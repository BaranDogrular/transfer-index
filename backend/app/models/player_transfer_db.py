from sqlalchemy import BigInteger, Column, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class PlayerTransferDB(Base):
    __tablename__ = "player_transfers"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "transfer_date",
            "transfer_season",
            "from_club_id",
            "to_club_id",
            "transfer_fee",
            name="uq_player_transfer_history",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    player_id = Column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    transfer_date = Column(Date, nullable=True, index=True)
    transfer_season = Column(String, nullable=True)

    from_club_id = Column(Integer, nullable=True)
    to_club_id = Column(Integer, nullable=True)
    from_club_name = Column(String, nullable=True)
    to_club_name = Column(String, nullable=True)
    from_club_country = Column(String, nullable=True)
    to_club_country = Column(String, nullable=True)

    transfer_type = Column(String, nullable=True)
    transfer_fee_text = Column(String, nullable=True)
    transfer_fee = Column(BigInteger, nullable=True)
    transfer_fee_in_eur = Column(BigInteger, nullable=True)
    market_value_in_eur = Column(BigInteger, nullable=True)
    player_name = Column(String, nullable=True)

    player = relationship(
        "PlayerDB",
        back_populates="transfers",
    )
