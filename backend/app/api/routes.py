from fastapi import APIRouter
from app.models.transfer import TransferRequest
from app.services.scoring_engine import TransferIndexEngine

router = APIRouter()
engine = TransferIndexEngine()


@router.post("/transfer-score")
def calculate_transfer_score(request: TransferRequest):
    return engine.calculate(request.player, request.team)