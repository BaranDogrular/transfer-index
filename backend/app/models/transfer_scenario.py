from pydantic import BaseModel


class TransferScenarioRequest(BaseModel):
    player_id: int
    target_club: str
