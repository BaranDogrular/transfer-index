from pydantic import BaseModel


class PlayerData(BaseModel):
    name: str
    age: int
    position: str
    club: str
    goals: int
    assists: int
    matches: int
    xg: float
    xa: float
    market_value_m: float
    salary_m: float
    injury_days: int
    contract_years_left: float


class TeamNeed(BaseModel):
    team_name: str
    needed_position: str
    max_market_value_m: float
    max_salary_m: float
    preferred_age_min: int
    preferred_age_max: int


class TransferRequest(BaseModel):
    player: PlayerData
    team: TeamNeed