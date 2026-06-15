from datetime import date
from pydantic import BaseModel


class PlayerValuationItem(BaseModel):
    date: date
    market_value: int


class PlayerValuationResponse(BaseModel):
    player_id: int

    current_value: int | None = None
    peak_value: int | None = None
    lowest_value: int | None = None

    growth_percent: float | None = None

    history: list[PlayerValuationItem]