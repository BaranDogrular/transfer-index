from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.transfer import (
    TransferRequest,
    PlayerData,
    TeamNeed,
)
from app.models.player_db import PlayerDB
from app.services.scoring_engine import TransferIndexEngine
from app.services.ai_scout import AIScoutService
from app.models.player_valuation_db import PlayerValuationDB
from app.schemas.player_valuation import PlayerValuationResponse, PlayerValuationItem


router = APIRouter()

engine = TransferIndexEngine()
ai_scout = AIScoutService()



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def root():
    return {"message": "Transfer Index API running"}


@router.post("/transfer-score")
def calculate_transfer_score(request: TransferRequest):
    return engine.calculate(request.player, request.team)


@router.post("/players")
def create_player(
    player: PlayerData,
    db: Session = Depends(get_db),
):
    new_player = PlayerDB(**player.model_dump())

    db.add(new_player)
    db.commit()
    db.refresh(new_player)

    return {
        "success": True,
        "player": new_player,
    }


@router.get("/players/search")
def search_players(
    q: str | None = None,
    position: str | None = None,
    league: str | None = None,
    nationality: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    max_value: float | None = None,
    max_salary: float | None = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(PlayerDB)

    if q:
        query = query.filter(PlayerDB.name.ilike(f"%{q}%"))

    if position:
        query = query.filter(PlayerDB.position.ilike(position))

    if league:
        query = query.filter(PlayerDB.league.ilike(f"%{league}%"))

    if nationality:
        query = query.filter(PlayerDB.nationality.ilike(f"%{nationality}%"))

    if min_age is not None:
        query = query.filter(PlayerDB.age >= min_age)

    if max_age is not None:
        query = query.filter(PlayerDB.age <= max_age)

    if max_value is not None:
        query = query.filter(PlayerDB.market_value_m <= max_value)

    if max_salary is not None:
        query = query.filter(PlayerDB.salary_m <= max_salary)

    total = query.count()

    page = max(page, 1)
    limit = min(max(limit, 1), 100)

    players = (
        query
        .order_by(PlayerDB.market_value_m.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "count": len(players),
        "total": total,
        "page": page,
        "limit": limit,
        "players": players,
    }


@router.get("/players")
def get_players(db: Session = Depends(get_db)):
    players = db.query(PlayerDB).all()

    return {
        "count": len(players),
        "players": players,
    }


@router.get("/players/{player_id}")
def get_player(
    player_id: int,
    db: Session = Depends(get_db),
):
    player = (
        db.query(PlayerDB)
        .filter(PlayerDB.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    return player


@router.post("/players/{player_id}/transfer-score")
def calculate_player_transfer_score(
    player_id: int,
    team: TeamNeed,
    db: Session = Depends(get_db),
):
    player = (
        db.query(PlayerDB)
        .filter(PlayerDB.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    result = engine.calculate(player, team)

    return {
        "success": True,
        "player": player.name,
        "transfer_index": result,
    }


@router.delete("/players/{player_id}")
def delete_player(
    player_id: int,
    db: Session = Depends(get_db),
):
    player = (
        db.query(PlayerDB)
        .filter(PlayerDB.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    db.delete(player)
    db.commit()

    return {
        "success": True,
        "message": f"Player {player_id} deleted",
    }


@router.post("/players/{player_id}/ai-report")
def generate_ai_report(
    player_id: int,
    db: Session = Depends(get_db),
):
    player = (
        db.query(PlayerDB)
        .filter(PlayerDB.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    team = {
        "team_name": "Fenerbahçe",
        "needed_position": player.position,
        "max_market_value_m": 20,
        "max_salary_m": 4,
        "preferred_age_min": 22,
        "preferred_age_max": 29,
    }

    class TeamObject:
        def __init__(self, data):
            self.__dict__.update(data)

    team_object = TeamObject(team)

    score_data = engine.calculate(player, team_object)

    ai_result = ai_scout.generate_report(player, score_data)

    return {
        "success": ai_result["success"],
        "player": player.name,
        "report": ai_result["report"],
        "score": score_data,
        "error": ai_result.get("error"),
    }

@router.get("/players/{player_id}/valuations", response_model=PlayerValuationResponse)
def get_player_valuations(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    valuations = (
        db.query(PlayerValuationDB)
        .filter(PlayerValuationDB.player_id == player_id)
        .order_by(PlayerValuationDB.valuation_date.asc())
        .all()
    )

    history = [
        PlayerValuationItem(
            date=item.valuation_date,
            market_value=item.market_value,
        )
        for item in valuations
    ]

    if not valuations:
        return PlayerValuationResponse(
            player_id=player_id,
            current_value=None,
            peak_value=None,
            lowest_value=None,
            growth_percent=None,
            history=[],
        )

    first_value = valuations[0].market_value
    current_value = valuations[-1].market_value
    peak_value = max(item.market_value for item in valuations)
    lowest_value = min(item.market_value for item in valuations)

    growth_percent = None
    if first_value and first_value > 0:
        growth_percent = round(((current_value - first_value) / first_value) * 100, 2)

    return PlayerValuationResponse(
        player_id=player_id,
        current_value=current_value,
        peak_value=peak_value,
        lowest_value=lowest_value,
        growth_percent=growth_percent,
        history=history,
    )
