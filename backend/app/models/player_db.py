from sqlalchemy import Column, Integer, String, Float, Date
from sqlalchemy.orm import relationship

from app.database import Base


class PlayerDB(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)

    transfermarkt_id = Column(
        Integer,
        unique=True,
        index=True,
        nullable=True,
    )

    # BASIC INFO
    name = Column(String, index=True)
    age = Column(Integer)
    position = Column(String)
    club = Column(String)

    # PROFILE
    nationality = Column(String)
    preferred_foot = Column(String)

    height_cm = Column(Integer)
    weight_kg = Column(Integer)

    league = Column(String)
    image_url = Column(String)

    # PERFORMANCE
    goals = Column(Integer)
    assists = Column(Integer)
    matches = Column(Integer)

    xg = Column(Float)
    xa = Column(Float)

    # FINANCIAL
    market_value_m = Column(Float)
    salary_m = Column(Float)

    # RISK
    injury_days = Column(Integer)
    contract_years_left = Column(Float)
    contract_expiration_date = Column(Date, nullable=True)

    # VALUE HISTORY
    valuations = relationship(
        "PlayerValuationDB",
        back_populates="player",
        cascade="all, delete-orphan",
    )