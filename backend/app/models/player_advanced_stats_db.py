from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class PlayerAdvancedStatsDB(Base):
    __tablename__ = "player_advanced_stats"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "source",
            name="uq_player_advanced_stats_player_season_source",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    player_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transfermarkt_id = Column(Integer, nullable=True, index=True)

    season = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, default="fbref", index=True)

    matches = Column(Integer, nullable=True)
    starts = Column(Integer, nullable=True)
    minutes = Column(Integer, nullable=True)
    goals = Column(Integer, nullable=True)
    assists = Column(Integer, nullable=True)
    xg = Column(Float, nullable=True)
    xa = Column(Float, nullable=True)
    npxg = Column(Float, nullable=True)
    shots = Column(Float, nullable=True)
    shots_on_target = Column(Float, nullable=True)
    key_passes = Column(Float, nullable=True)
    progressive_passes = Column(Float, nullable=True)
    progressive_carries = Column(Float, nullable=True)
    passes_into_final_third = Column(Float, nullable=True)
    passes_into_penalty_area = Column(Float, nullable=True)
    shot_creating_actions = Column(Float, nullable=True)
    goal_creating_actions = Column(Float, nullable=True)
    tackles = Column(Float, nullable=True)
    interceptions = Column(Float, nullable=True)
    blocks = Column(Float, nullable=True)
    aerials_won = Column(Float, nullable=True)
    aerials_lost = Column(Float, nullable=True)
    yellow_cards = Column(Integer, nullable=True)
    red_cards = Column(Integer, nullable=True)
    clean_sheets = Column(Integer, nullable=True)
    saves = Column(Integer, nullable=True)
    save_percentage = Column(Float, nullable=True)
    goals_against = Column(Integer, nullable=True)
    pass_completion = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    player = relationship(
        "PlayerDB",
        back_populates="advanced_stats",
    )
