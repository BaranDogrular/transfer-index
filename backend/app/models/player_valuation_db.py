from sqlalchemy import Column, Integer, BigInteger, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class PlayerValuationDB(Base):
    __tablename__ = "player_valuations"

    id = Column(Integer, primary_key=True, index=True)

    player_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    market_value = Column(BigInteger, nullable=False)
    valuation_date = Column(Date, nullable=False, index=True)

    current_club_id = Column(Integer, nullable=True)

    player = relationship(
        "PlayerDB",
        back_populates="valuations",
    )