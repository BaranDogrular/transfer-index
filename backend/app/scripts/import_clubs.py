import os

import pandas as pd

from app.database import SessionLocal
from app.models.club_db import ClubDB
from app.models.player_db import PlayerDB
from app.models.player_advanced_stats_db import PlayerAdvancedStatsDB
from app.models.player_transfer_db import PlayerTransferDB
from app.models.player_valuation_db import PlayerValuationDB


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLUBS_CSV_PATH = os.path.join(BASE_DIR, "data", "transfermarkt", "clubs.csv")
COMPETITIONS_CSV_PATH = os.path.join(BASE_DIR, "data", "transfermarkt", "competitions.csv")


def parse_int(value):
    if pd.isna(value):
        return None

    try:
        return int(value)
    except Exception:
        return None


def parse_float(value):
    if pd.isna(value):
        return None

    try:
        return float(value)
    except Exception:
        return None


def parse_string(value):
    if pd.isna(value):
        return None

    value = str(value).strip()
    return value or None


def import_clubs():
    db = SessionLocal()

    try:
        print("Reading clubs.csv...")
        clubs_df = pd.read_csv(CLUBS_CSV_PATH)

        print("Reading competitions.csv...")
        competitions_df = pd.read_csv(COMPETITIONS_CSV_PATH)

        required_club_columns = {
            "club_id",
            "club_code",
            "name",
            "domestic_competition_id",
            "total_market_value",
            "squad_size",
            "average_age",
            "stadium_name",
            "coach_name",
            "url",
        }
        required_competition_columns = {"competition_id", "name", "country_name"}

        missing_club_columns = required_club_columns - set(clubs_df.columns)
        missing_competition_columns = required_competition_columns - set(
            competitions_df.columns
        )

        if missing_club_columns:
            raise ValueError(f"Missing columns in clubs.csv: {missing_club_columns}")

        if missing_competition_columns:
            raise ValueError(
                f"Missing columns in competitions.csv: {missing_competition_columns}"
            )

        competitions_df = competitions_df.rename(
            columns={
                "name": "league",
                "country_name": "country",
            }
        )

        clubs_df = clubs_df.merge(
            competitions_df[["competition_id", "league", "country"]],
            left_on="domestic_competition_id",
            right_on="competition_id",
            how="left",
        )

        logo_columns = [
            column
            for column in ["logo_url", "image_url", "club_logo"]
            if column in clubs_df.columns
        ]

        imported = 0
        updated = 0

        for _, row in clubs_df.iterrows():
            club_id = parse_int(row.get("club_id"))

            if club_id is None:
                continue

            club = db.query(ClubDB).filter(ClubDB.club_id == club_id).first()

            if not club:
                club = ClubDB(club_id=club_id)
                db.add(club)
                imported += 1
            else:
                updated += 1

            club.club_code = parse_string(row.get("club_code"))
            club.name = parse_string(row.get("name")) or f"Club {club_id}"
            club.domestic_competition_id = parse_string(
                row.get("domestic_competition_id")
            )
            club.league = parse_string(row.get("league"))
            club.country = parse_string(row.get("country"))
            club.logo_url = (
                parse_string(row.get(logo_columns[0])) if logo_columns else None
            )
            club.squad_size = parse_int(row.get("squad_size"))
            club.average_age = parse_float(row.get("average_age"))
            club.total_market_value = parse_float(row.get("total_market_value"))
            club.stadium_name = parse_string(row.get("stadium_name"))
            club.coach_name = parse_string(row.get("coach_name"))
            club.url = parse_string(row.get("url"))

        db.commit()

        print("Club import completed.")
        print(f"Imported clubs: {imported}")
        print(f"Updated clubs: {updated}")

    except Exception as error:
        db.rollback()
        print("Club import failed.")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_clubs()
