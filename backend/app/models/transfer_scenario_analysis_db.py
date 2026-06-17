from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TransferScenarioAnalysisDB(Base):
    __tablename__ = "transfer_scenario_analyses"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_club = Column(String, nullable=False, index=True)
    context_hash = Column(String(64), nullable=False, unique=True, index=True)
    source = Column(String, nullable=False)

    fit_score = Column(Integer, nullable=True)
    grade = Column(String, nullable=True)
    strengths = Column(JSON, nullable=True)
    risks = Column(JSON, nullable=True)
    tactical_fit = Column(Text, nullable=True)
    financial_risk = Column(Text, nullable=True)
    contract_risk = Column(Text, nullable=True)
    market_value_projection = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    player = relationship("PlayerDB")
