import os

import pandas as pd

from app.database import SessionLocal
from app.models.player_db import PlayerDB
from app.models.player_valuation_db import PlayerValuationDB
from app.models.player_transfer_db import PlayerTransferDB


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "transfermarkt", "transfers.csv")
CLUBS_CSV_PATH = os.path.join(BASE_DIR, "data", "transfermarkt", "clubs.csv")
COMPETITIONS_CSV_PATH = os.path.join(BASE_DIR, "data", "transfermarkt", "competitions.csv")
BATCH_SIZE = 5000


def parse_date(value):
    if pd.isna(value):
        return None

    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def parse_int(value):
    if pd.isna(value):
        return None

    try:
        return int(value)
    except Exception:
        return None


def parse_money(value):
    if pd.isna(value):
        return None

    try:
        return int(float(value))
    except Exception:
        return None


def parse_transfer_type(value):
    if pd.isna(value):
        return None

    normalized = str(value).strip().lower()

    if normalized in {"loan", "loan return", "free transfer", "end of loan", "released"}:
        return normalized

    return None


def infer_transfer_types(df):
    inferred_types = {}
    type_columns = [
        column
        for column in df.columns
        if any(keyword in column.lower() for keyword in ["type", "loan", "fee_text"])
    ]

    for index, row in df.iterrows():
        for column in type_columns:
            transfer_type = parse_transfer_type(row.get(column))
            if transfer_type:
                inferred_types[index] = transfer_type
                break

    sortable_df = df.copy()
    sortable_df["_transfer_date"] = pd.to_datetime(
        sortable_df["transfer_date"],
        errors="coerce",
    )
    sortable_df["_transfer_fee"] = pd.to_numeric(
        sortable_df["transfer_fee"],
        errors="coerce",
    )

    grouped_df = sortable_df.sort_values(
        ["player_id", "_transfer_date"]
    ).groupby("player_id")

    for _, player_transfers in grouped_df:
        zero_fee_transfers = player_transfers[
            player_transfers["_transfer_fee"].fillna(-1) == 0
        ]
        used_return_indexes = set()

        for index, row in zero_fee_transfers.iterrows():
            from_club_id = parse_int(row.get("from_club_id"))
            to_club_id = parse_int(row.get("to_club_id"))
            transfer_date = row.get("_transfer_date")

            if from_club_id is None or to_club_id is None or pd.isna(transfer_date):
                continue

            possible_returns = zero_fee_transfers[
                (zero_fee_transfers.index != index)
                & (zero_fee_transfers.index.map(lambda value: value not in used_return_indexes))
                & (zero_fee_transfers["from_club_id"] == to_club_id)
                & (zero_fee_transfers["to_club_id"] == from_club_id)
                & (zero_fee_transfers["_transfer_date"] > transfer_date)
            ]

            if possible_returns.empty:
                continue

            return_index = possible_returns.index[0]
            inferred_types.setdefault(index, "loan")
            inferred_types.setdefault(return_index, "loan return")
            used_return_indexes.add(return_index)

    for index, row in sortable_df.iterrows():
        if index in inferred_types:
            continue

        if parse_money(row.get("transfer_fee")) == 0:
            inferred_types[index] = "free transfer"

    return inferred_types


def parse_string(value):
    if pd.isna(value):
        return None

    value = str(value).strip()
    return value or None


def import_transfers():
    db = SessionLocal()

    try:
        print("Reading transfers.csv...")
        df = pd.read_csv(CSV_PATH)

        print("Reading clubs.csv...")
        clubs_df = pd.read_csv(CLUBS_CSV_PATH)

        print("Reading competitions.csv...")
        competitions_df = pd.read_csv(COMPETITIONS_CSV_PATH)

        required_columns = {
            "player_id",
            "transfer_date",
            "transfer_season",
            "from_club_id",
            "to_club_id",
            "from_club_name",
            "to_club_name",
            "transfer_fee",
            "market_value_in_eur",
            "player_name",
        }
        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(f"Missing columns in transfers.csv: {missing_columns}")

        required_club_columns = {"club_id", "domestic_competition_id"}
        required_competition_columns = {"competition_id", "country_name"}
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

        inferred_transfer_types = infer_transfer_types(df)

        clubs_with_country = clubs_df.merge(
            competitions_df[["competition_id", "country_name"]],
            left_on="domestic_competition_id",
            right_on="competition_id",
            how="left",
        )

        club_countries_by_id = {
            int(row["club_id"]): parse_string(row.get("country_name"))
            for _, row in clubs_with_country.iterrows()
            if not pd.isna(row.get("club_id"))
        }

        players_by_transfermarkt_id = {
            player.transfermarkt_id: player.id
            for player in db.query(PlayerDB).all()
            if player.transfermarkt_id is not None
        }

        print(f"Players with transfermarkt_id: {len(players_by_transfermarkt_id)}")
        print("Deleting old transfer history...")
        db.query(PlayerTransferDB).delete()
        db.commit()

        records = []
        imported_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            transfermarkt_player_id = parse_int(row.get("player_id"))

            if transfermarkt_player_id is None:
                skipped_count += 1
                continue

            player_db_id = players_by_transfermarkt_id.get(transfermarkt_player_id)

            if not player_db_id:
                skipped_count += 1
                continue

            from_club_id = parse_int(row.get("from_club_id"))
            to_club_id = parse_int(row.get("to_club_id"))
            transfer_fee = parse_money(row.get("transfer_fee"))
            transfer_type = inferred_transfer_types.get(
                row.name,
                parse_transfer_type(row.get("transfer_fee")),
            )

            records.append(
                PlayerTransferDB(
                    player_id=player_db_id,
                    transfer_date=parse_date(row.get("transfer_date")),
                    transfer_season=parse_string(row.get("transfer_season")),
                    from_club_id=from_club_id,
                    to_club_id=to_club_id,
                    from_club_name=parse_string(row.get("from_club_name")),
                    to_club_name=parse_string(row.get("to_club_name")),
                    from_club_country=club_countries_by_id.get(from_club_id),
                    to_club_country=club_countries_by_id.get(to_club_id),
                    transfer_type=transfer_type,
                    transfer_fee_text=parse_string(row.get("transfer_fee")),
                    transfer_fee=transfer_fee,
                    transfer_fee_in_eur=transfer_fee,
                    market_value_in_eur=parse_money(row.get("market_value_in_eur")),
                    player_name=parse_string(row.get("player_name")),
                )
            )

            if len(records) >= BATCH_SIZE:
                db.bulk_save_objects(records)
                db.commit()
                imported_count += len(records)
                print(f"Imported {imported_count} transfers...")
                records = []

        if records:
            db.bulk_save_objects(records)
            db.commit()
            imported_count += len(records)

        print("Transfer import completed.")
        print(f"Imported transfers: {imported_count}")
        print(f"Skipped rows: {skipped_count}")

    except Exception as error:
        db.rollback()
        print("Transfer import failed.")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_transfers()
