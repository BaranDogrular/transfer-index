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
from app.models.player_transfer_db import PlayerTransferDB
from app.models.club_db import ClubDB
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


@router.get("/clubs/{club_id_or_name}")
def get_club(club_id_or_name: str, db: Session = Depends(get_db)):
    club = None

    if club_id_or_name.isdigit():
        club = (
            db.query(ClubDB)
            .filter(ClubDB.club_id == int(club_id_or_name))
            .first()
        )

    if not club:
        normalized_name = club_id_or_name.replace("-", " ").strip()
        club = (
            db.query(ClubDB)
            .filter(ClubDB.name.ilike(normalized_name))
            .first()
        )

    club_name = club.name if club else club_id_or_name.replace("-", " ").strip()

    players = (
        db.query(PlayerDB)
        .filter(PlayerDB.club.ilike(club_name))
        .order_by(PlayerDB.market_value_m.desc().nullslast(), PlayerDB.name.asc())
        .all()
    )

    if not club and not players:
        raise HTTPException(status_code=404, detail="Club not found")

    player_items = [
        {
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "market_value_m": player.market_value_m,
            "image_url": player.image_url,
        }
        for player in players
    ]

    market_values = [
        player.market_value_m
        for player in players
        if player.market_value_m is not None
    ]
    ages = [player.age for player in players if player.age is not None and player.age > 0]
    total_market_value = sum(market_values) if market_values else None
    average_age = round(sum(ages) / len(ages), 1) if ages else None

    return {
        "club_id": club.club_id if club else None,
        "club_name": club_name,
        "country": club.country if club else None,
        "league": club.league if club else None,
        "squad_count": len(players) if players else club.squad_size if club else 0,
        "average_age": average_age if average_age is not None else club.average_age if club else None,
        "total_market_value": total_market_value,
        "top_players_by_value": player_items[:5],
        "players": player_items,
    }


@router.get("/players/compare")
def compare_players(
    player1_id: int,
    player2_id: int,
    db: Session = Depends(get_db),
):
    player1 = db.query(PlayerDB).filter(PlayerDB.id == player1_id).first()
    player2 = db.query(PlayerDB).filter(PlayerDB.id == player2_id).first()

    if not player1 or not player2:
        raise HTTPException(status_code=404, detail="Player not found")

    def serialize_player(player):
        return {
            "id": player.id,
            "name": player.name,
            "image_url": player.image_url,
            "club": player.club,
            "league": player.league,
            "position": player.position,
            "age": player.age,
            "height": player.height_cm,
            "preferred_foot": player.preferred_foot,
            "market_value_m": player.market_value_m,
            "contract_expiration_date": player.contract_expiration_date,
            "matches": player.matches,
            "goals": player.goals,
            "assists": player.assists,
            "minutes_played": player.minutes_played,
            "goals_per_90": player.goals_per_90,
            "assists_per_90": player.assists_per_90,
            "goal_contributions": player.goal_contributions,
            "goal_contributions_per_90": player.goal_contributions_per_90,
            "yellow_cards": player.yellow_cards,
            "red_cards": player.red_cards,
        }

    return {
        "player1": serialize_player(player1),
        "player2": serialize_player(player2),
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


@router.get("/players/{player_id}/transfers")
def get_player_transfers(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    transfers = (
        db.query(PlayerTransferDB)
        .filter(PlayerTransferDB.player_id == player_id)
        .order_by(
            PlayerTransferDB.transfer_date.desc().nullslast(),
            PlayerTransferDB.id.desc(),
        )
        .all()
    )

    def format_transfer_fee(value):
        if value is None or value <= 0:
            return None

        if value >= 1000000:
            return f"€{value / 1000000:.1f}M"

        if value >= 1000:
            return f"€{value / 1000:.0f}K"

        return f"€{value}"

    def get_transfer_label(transfer):
        transfer_type = (transfer.transfer_type or "").strip().lower()

        if transfer_type in {"loan", "loaned"}:
            return "Kiralık"

        if transfer_type in {"loan return", "end of loan"}:
            return "Kiralıktan geri döndü"

        if transfer_type in {"free transfer", "free", "ablöse yok"}:
            return "Bedelsiz"

        fee = transfer.transfer_fee_in_eur
        if fee is None:
            fee = transfer.transfer_fee

        formatted_fee = format_transfer_fee(fee)
        if formatted_fee:
            return formatted_fee

        return "-"

    transfer_items = [
        {
            "id": item.id,
            "player_id": item.player_id,
            "transfer_date": item.transfer_date,
            "transfer_season": item.transfer_season,
            "from_club_id": item.from_club_id,
            "to_club_id": item.to_club_id,
            "from_club_name": item.from_club_name,
            "to_club_name": item.to_club_name,
            "from_club_country": item.from_club_country,
            "to_club_country": item.to_club_country,
            "transfer_type": item.transfer_type,
            "transfer_fee_text": item.transfer_fee_text,
            "transfer_fee": item.transfer_fee,
            "transfer_fee_in_eur": item.transfer_fee_in_eur,
            "formatted_transfer_fee": format_transfer_fee(item.transfer_fee_in_eur),
            "transfer_label": get_transfer_label(item),
            "market_value_in_eur": item.market_value_in_eur,
            "player_name": item.player_name,
        }
        for item in transfers
    ]

    return {
        "player_id": player_id,
        "count": len(transfer_items),
        "transfers": transfer_items,
    }
