import os
import pandas as pd

from app.database import SessionLocal
from app.models.player_db import PlayerDB
from app.models.player_advanced_stats_db import PlayerAdvancedStatsDB
from app.models.player_valuation_db import PlayerValuationDB


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "transfermarkt", "player_valuations.csv")

BATCH_SIZE = 5000


def parse_date(value):
    if pd.isna(value):
        return None

    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def parse_market_value(value):
    if pd.isna(value):
        return None

    try:
        return int(value)
    except Exception:
        return None


def import_player_valuations():
    db = SessionLocal()

    try:
        print("Reading player_valuations.csv...")
        df = pd.read_csv(CSV_PATH)

        required_columns = {"player_id", "market_value_in_eur", "date"}
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(f"Missing columns in player_valuations.csv: {missing_columns}")

        print("Loading existing players by transfermarkt_id...")

        players_by_transfermarkt_id = {
            player.transfermarkt_id: player.id
            for player in db.query(PlayerDB).all()
            if player.transfermarkt_id is not None
        }

        print(f"Players with transfermarkt_id: {len(players_by_transfermarkt_id)}")

        print("Deleting old valuation data...")
        db.query(PlayerValuationDB).delete()
        db.commit()

        records = []
        imported_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            transfermarkt_player_id = row.get("player_id")

            if pd.isna(transfermarkt_player_id):
                skipped_count += 1
                continue

            transfermarkt_player_id = int(transfermarkt_player_id)

            player_db_id = players_by_transfermarkt_id.get(transfermarkt_player_id)

            if not player_db_id:
                skipped_count += 1
                continue

            market_value = parse_market_value(row.get("market_value_in_eur"))
            valuation_date = parse_date(row.get("date"))

            if market_value is None or valuation_date is None:
                skipped_count += 1
                continue

            current_club_id = row.get("current_club_id")
            if pd.isna(current_club_id):
                current_club_id = None
            else:
                current_club_id = int(current_club_id)

            records.append(
                PlayerValuationDB(
                    player_id=player_db_id,
                    market_value=market_value,
                    valuation_date=valuation_date,
                    current_club_id=current_club_id,
                )
            )

            if len(records) >= BATCH_SIZE:
                db.bulk_save_objects(records)
                db.commit()
                imported_count += len(records)
                print(f"Imported {imported_count} valuations...")
                records = []

        if records:
            db.bulk_save_objects(records)
            db.commit()
            imported_count += len(records)

        print("Import completed.")
        print(f"Imported valuations: {imported_count}")
        print(f"Skipped rows: {skipped_count}")

    except Exception as error:
        db.rollback()
        print("Import failed.")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_player_valuations()
