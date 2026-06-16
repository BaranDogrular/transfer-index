import pandas as pd
from datetime import date

from app.database import SessionLocal
from app.models.player_db import PlayerDB
from app.models.player_valuation_db import PlayerValuationDB

print("IMPORT SCRIPT STARTED")

DATA_PATH = "app/data/transfermarkt/players.csv"


def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def safe_str(value, default="Unknown"):
    try:
        if pd.isna(value):
            return default

        value = str(value).strip()

        if not value or value.lower() == "nan":
            return default

        return value

    except Exception:
        return default


def calculate_age(date_of_birth):
    if pd.isna(date_of_birth):
        return 0

    try:
        birth_date = pd.to_datetime(date_of_birth).date()
        today = date.today()

        return (
            today.year
            - birth_date.year
            - ((today.month, today.day) < (birth_date.month, birth_date.day))
        )
    except Exception:
        return 0


def parse_contract_date(value):
    if pd.isna(value):
        return None

    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def calculate_contract_years_left(contract_expiration_date):
    if not contract_expiration_date:
        return 0

    try:
        today = date.today()
        days_left = (contract_expiration_date - today).days

        if days_left <= 0:
            return 0

        return round(days_left / 365, 2)

    except Exception:
        return 0


def import_players():
    db = SessionLocal()

    try:
        df = pd.read_csv(DATA_PATH)

        imported = 0
        updated = 0
        skipped = 0

        for _, row in df.iterrows():
            last_season = safe_int(row.get("last_season", 0))

            if last_season < 2025:
                skipped += 1
                continue

            transfermarkt_id = safe_int(row.get("player_id", 0))

            if transfermarkt_id == 0:
                skipped += 1
                continue

            name = safe_str(row.get("name", ""), "")

            if not name:
                skipped += 1
                continue

            date_of_birth = parse_contract_date(row.get("date_of_birth"))
            age = calculate_age(row.get("date_of_birth"))

            contract_expiration_date = parse_contract_date(
                row.get("contract_expiration_date")
            )

            contract_years_left = calculate_contract_years_left(
                contract_expiration_date
            )

            position = safe_str(
                row.get("sub_position", row.get("position", "Unknown"))
            )
            club = safe_str(row.get("current_club_name", "Unknown"))
            current_club_id = safe_int(row.get("current_club_id", 0)) or None
            nationality = safe_str(row.get("country_of_citizenship", "Unknown"))
            preferred_foot = safe_str(row.get("foot", "Unknown"))
            height_cm = safe_int(row.get("height_in_cm", 0))
            league = safe_str(
                row.get("current_club_domestic_competition_id", "Unknown")
            )
            image_url = safe_str(row.get("image_url", ""), "")
            market_value_m = safe_float(row.get("market_value_in_eur", 0)) / 1_000_000

            existing_player = (
                db.query(PlayerDB)
                .filter(PlayerDB.transfermarkt_id == transfermarkt_id)
                .first()
            )

            if existing_player:
                existing_player.name = name
                existing_player.age = age
                existing_player.position = position
                existing_player.club = club
                existing_player.current_club_id = current_club_id

                existing_player.date_of_birth = date_of_birth
                existing_player.nationality = nationality
                existing_player.preferred_foot = preferred_foot
                existing_player.height_cm = height_cm
                existing_player.weight_kg = 0
                existing_player.league = league
                existing_player.image_url = image_url

                existing_player.goals = 0
                existing_player.assists = 0
                existing_player.matches = 0
                existing_player.xg = 0
                existing_player.xa = 0

                existing_player.market_value_m = market_value_m
                existing_player.salary_m = 0

                existing_player.injury_days = 0
                existing_player.contract_years_left = contract_years_left
                existing_player.contract_expiration_date = contract_expiration_date

                updated += 1
                continue

            player = PlayerDB(
                transfermarkt_id=transfermarkt_id,

                # BASIC
                name=name,
                age=age,
                position=position,
                club=club,
                current_club_id=current_club_id,

                # PROFILE
                date_of_birth=date_of_birth,
                nationality=nationality,
                preferred_foot=preferred_foot,
                height_cm=height_cm,
                weight_kg=0,
                league=league,
                image_url=image_url,

                # PERFORMANCE
                goals=0,
                assists=0,
                matches=0,
                xg=0,
                xa=0,

                # FINANCIAL
                market_value_m=market_value_m,
                salary_m=0,

                # RISK
                injury_days=0,
                contract_years_left=contract_years_left,
                contract_expiration_date=contract_expiration_date,
            )

            db.add(player)
            imported += 1

        db.commit()

        print("Transfermarkt import completed.")
        print(f"Imported: {imported}")
        print(f"Updated: {updated}")
        print(f"Skipped: {skipped}")

    except Exception as error:
        db.rollback()
        print("Transfermarkt import failed.")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_players()
