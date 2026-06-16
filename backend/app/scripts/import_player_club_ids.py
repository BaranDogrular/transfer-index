import os

import pandas as pd

from app.database import SessionLocal
from app.models.player_db import PlayerDB
from app.models.player_valuation_db import PlayerValuationDB
from app.models.player_transfer_db import PlayerTransferDB
from app.models.club_db import ClubDB


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYERS_CSV_PATH = os.path.join(BASE_DIR, "data", "transfermarkt", "players.csv")


def parse_int(value):
    if pd.isna(value):
        return None

    try:
        return int(value)
    except Exception:
        return None


def import_player_club_ids():
    db = SessionLocal()

    try:
        print("Reading players.csv...")
        df = pd.read_csv(PLAYERS_CSV_PATH)

        required_columns = {"player_id", "current_club_id"}
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(f"Missing columns in players.csv: {missing_columns}")

        players_by_transfermarkt_id = {
            player.transfermarkt_id: player
            for player in db.query(PlayerDB).all()
            if player.transfermarkt_id is not None
        }

        updated = 0
        skipped = 0

        for _, row in df.iterrows():
            transfermarkt_id = parse_int(row.get("player_id"))
            current_club_id = parse_int(row.get("current_club_id"))

            if transfermarkt_id is None:
                skipped += 1
                continue

            player = players_by_transfermarkt_id.get(transfermarkt_id)

            if not player:
                skipped += 1
                continue

            player.current_club_id = current_club_id
            updated += 1

        db.commit()

        print("Player club ids import completed.")
        print(f"Updated players: {updated}")
        print(f"Skipped rows: {skipped}")

    except Exception as error:
        db.rollback()
        print("Player club ids import failed.")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_player_club_ids()
