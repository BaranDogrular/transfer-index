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
    current_club_id = Column(Integer, nullable=True, index=True)

    # PROFILE
    date_of_birth = Column(Date, nullable=True)
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
    minutes_played = Column(Integer)
    yellow_cards = Column(Integer)
    red_cards = Column(Integer)
    goals_per_90 = Column(Float)
    assists_per_90 = Column(Float)
    goal_contributions = Column(Integer)
    goal_contributions_per_90 = Column(Float)
    minutes_per_goal = Column(Float)

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

    transfers = relationship(
        "PlayerTransferDB",
        back_populates="player",
        cascade="all, delete-orphan",
    )
