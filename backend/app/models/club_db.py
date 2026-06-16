from sqlalchemy import Column, Float, Integer, String

from app.database import Base


class ClubDB(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, unique=True, index=True, nullable=False)
    club_code = Column(String, nullable=True, index=True)
    name = Column(String, nullable=False, index=True)
    domestic_competition_id = Column(String, nullable=True, index=True)
    league = Column(String, nullable=True)
    country = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    squad_size = Column(Integer, nullable=True)
    average_age = Column(Float, nullable=True)
    total_market_value = Column(Float, nullable=True)
    stadium_name = Column(String, nullable=True)
    coach_name = Column(String, nullable=True)
    url = Column(String, nullable=True)
