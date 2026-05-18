from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class PlayerDB(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, index=True)
    age = Column(Integer)
    position = Column(String)
    club = Column(String)

    goals = Column(Integer)
    assists = Column(Integer)
    matches = Column(Integer)

    xg = Column(Float)
    xa = Column(Float)

    market_value_m = Column(Float)
    salary_m = Column(Float)

    injury_days = Column(Integer)
    contract_years_left = Column(Float)