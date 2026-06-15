from pydantic import BaseModel


# PLAYER
class PlayerData(BaseModel):
    # BASIC
    name: str
    age: int
    position: str
    club: str

    # NEW FIELDS
    nationality: str
    preferred_foot: str

    height_cm: int
    weight_kg: int

    league: str

    image_url: str

    # PERFORMANCE
    goals: int
    assists: int
    matches: int

    xg: float
    xa: float

    # FINANCIAL
    market_value_m: float
    salary_m: float

    # RISK
    injury_days: int
    contract_years_left: float


# TEAM NEED
class TeamNeed(BaseModel):
    team_name: str
    needed_position: str

    max_market_value_m: float
    max_salary_m: float

    preferred_age_min: int
    preferred_age_max: int


# TRANSFER REQUEST
class TransferRequest(BaseModel):
    player: PlayerData
    team: TeamNeed