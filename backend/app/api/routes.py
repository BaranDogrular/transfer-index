from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.transfer import TransferRequest, PlayerData, TeamNeed
from app.models.player_db import PlayerDB
from app.services.scoring_engine import TransferIndexEngine

router = APIRouter()
engine = TransferIndexEngine()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/transfer-score")
def calculate_transfer_score(request: TransferRequest):
    return engine.calculate(request.player, request.team)


@router.post("/players")
def create_player(player: PlayerData, db: Session = Depends(get_db)):
    new_player = PlayerDB(**player.model_dump())
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player


@router.get("/players")
def get_players(db: Session = Depends(get_db)):
    return db.query(PlayerDB).all()


@router.get("/players/{player_id}")
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        return {"error": "Player not found"}

    return player


@router.post("/players/{player_id}/transfer-score")
def calculate_player_transfer_score(
    player_id: int,
    team: TeamNeed,
    db: Session = Depends(get_db)
):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        return {"error": "Player not found"}

    return engine.calculate(player, team)

@router.delete("/players/{player_id}")
def delete_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        return {"error": "Player not found"}

    db.delete(player)
    db.commit()

    return {"message": f"Player {player_id} deleted"}