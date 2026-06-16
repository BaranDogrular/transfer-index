import os
import re
import unicodedata

import pandas as pd

from app.database import SessionLocal
from app.models.player_advanced_stats_db import PlayerAdvancedStatsDB
from app.models.player_db import PlayerDB
from app.models.player_transfer_db import PlayerTransferDB
from app.models.player_valuation_db import PlayerValuationDB


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "fbref_player_stats.csv")
SOURCE = "fbref"


FIELD_ALIASES = {
    "transfermarkt_id": [
        "transfermarkt_id",
        "transfermarkt_player_id",
        "tm_player_id",
        "tm_id",
    ],
    "player_name": ["player", "name", "player_name"],
    "club": ["club", "squad", "team", "current_club", "current_club_name"],
    "season": ["season", "year", "season_name"],
    "minutes": ["minutes", "min", "mins", "playing_time_min"],
    "goals": ["goals", "gls", "standard_gls"],
    "assists": ["assists", "ast", "standard_ast"],
    "xg": ["xg", "expected_xg"],
    "xa": ["xa", "xag", "expected_xa", "expected_xag"],
    "npxg": ["npxg", "np_xg", "expected_npxg"],
    "shots": ["shots", "sh", "shooting_sh"],
    "shots_on_target": ["shots_on_target", "sot", "shooting_sot"],
    "key_passes": ["key_passes", "kp", "passing_kp"],
    "progressive_passes": ["progressive_passes", "prgp", "prg_p", "prgpass"],
    "progressive_carries": ["progressive_carries", "prgc", "prg_c", "prgcarry"],
    "passes_into_final_third": [
        "passes_into_final_third",
        "passes_final_third",
        "passes_1_3",
        "1_3",
    ],
    "passes_into_penalty_area": [
        "passes_into_penalty_area",
        "passes_penalty_area",
        "ppa",
    ],
    "shot_creating_actions": ["shot_creating_actions", "sca"],
    "goal_creating_actions": ["goal_creating_actions", "gca"],
    "tackles": ["tackles", "tkl"],
    "interceptions": ["interceptions", "int"],
    "blocks": ["blocks", "blk"],
    "aerials_won": ["aerials_won", "aerial_duels_won", "won"],
    "aerials_lost": ["aerials_lost", "aerial_duels_lost", "lost"],
}

STAT_FIELDS = [
    "minutes",
    "goals",
    "assists",
    "xg",
    "xa",
    "npxg",
    "shots",
    "shots_on_target",
    "key_passes",
    "progressive_passes",
    "progressive_carries",
    "passes_into_final_third",
    "passes_into_penalty_area",
    "shot_creating_actions",
    "goal_creating_actions",
    "tackles",
    "interceptions",
    "blocks",
    "aerials_won",
    "aerials_lost",
]

INTEGER_FIELDS = {"minutes", "goals", "assists"}


def normalize_text(value):
    if value is None or pd.isna(value):
        return ""

    normalized = unicodedata.normalize("NFKD", str(value).strip().lower())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def normalize_column_name(value):
    normalized = normalize_text(value)
    normalized = normalized.replace("%", "pct")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def parse_int(value):
    if value is None or pd.isna(value):
        return None

    try:
        return int(float(str(value).replace(",", "")))
    except Exception:
        return None


def parse_float(value):
    if value is None or pd.isna(value):
        return None

    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def normalize_season(value):
    if value is None or pd.isna(value):
        return None

    raw_value = str(value).strip()

    if not raw_value:
        return None

    match = re.search(r"(20\d{2})\D?(20)?(\d{2})?", raw_value)

    if not match:
        return raw_value

    start_year = int(match.group(1))
    end_suffix = match.group(3)

    if not end_suffix:
        end_suffix = str(start_year + 1)[-2:]

    return f"{start_year}/{end_suffix}"


def get_column_value(row, column_lookup, field_name):
    for alias in FIELD_ALIASES[field_name]:
        normalized_alias = normalize_column_name(alias)
        column_name = column_lookup.get(normalized_alias)

        if column_name is not None:
            return row.get(column_name)

    return None


def build_player_maps(db):
    players = db.query(PlayerDB).all()

    players_by_transfermarkt_id = {
        player.transfermarkt_id: player
        for player in players
        if player.transfermarkt_id is not None
    }
    players_by_name_club = {
        (
            normalize_text(player.name),
            normalize_text(player.club),
        ): player
        for player in players
        if player.name and player.club
    }

    return players_by_transfermarkt_id, players_by_name_club


def resolve_player(row, column_lookup, players_by_transfermarkt_id, players_by_name_club):
    transfermarkt_id = parse_int(get_column_value(row, column_lookup, "transfermarkt_id"))

    if transfermarkt_id is not None:
        player = players_by_transfermarkt_id.get(transfermarkt_id)

        if player:
            return player, transfermarkt_id, "transfermarkt_id"

    player_name = get_column_value(row, column_lookup, "player_name")
    club_name = get_column_value(row, column_lookup, "club")

    player = players_by_name_club.get(
        (
            normalize_text(player_name),
            normalize_text(club_name),
        )
    )

    if player:
        return player, player.transfermarkt_id, "name_club"

    return None, transfermarkt_id, "unmatched"


def import_fbref_advanced_stats():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"FBref advanced stats CSV not found: {CSV_PATH}. "
            "Place the file at app/data/fbref_player_stats.csv."
        )

    db = SessionLocal()

    try:
        print("Reading fbref_player_stats.csv...")
        df = pd.read_csv(CSV_PATH)

        print("Inspecting CSV columns:")
        print(list(df.columns))

        column_lookup = {
            normalize_column_name(column_name): column_name
            for column_name in df.columns
        }
        mapped_columns = {}
        for field_name, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                column_name = column_lookup.get(normalize_column_name(alias))

                if column_name is not None:
                    mapped_columns[field_name] = column_name
                    break

        print("Mapped fields:")
        print(sorted(mapped_columns.keys()))

        players_by_transfermarkt_id, players_by_name_club = build_player_maps(db)

        updated = 0
        imported = 0
        skipped = 0
        matched_by_transfermarkt_id = 0
        matched_by_name_club = 0

        for _, row in df.iterrows():
            season = normalize_season(get_column_value(row, column_lookup, "season"))

            if not season:
                skipped += 1
                continue

            player, transfermarkt_id, match_type = resolve_player(
                row,
                column_lookup,
                players_by_transfermarkt_id,
                players_by_name_club,
            )

            if not player:
                skipped += 1
                continue

            if match_type == "transfermarkt_id":
                matched_by_transfermarkt_id += 1
            elif match_type == "name_club":
                matched_by_name_club += 1

            values = {}

            for field_name in STAT_FIELDS:
                raw_value = get_column_value(row, column_lookup, field_name)
                values[field_name] = (
                    parse_int(raw_value)
                    if field_name in INTEGER_FIELDS
                    else parse_float(raw_value)
                )

            existing_stats = (
                db.query(PlayerAdvancedStatsDB)
                .filter(PlayerAdvancedStatsDB.player_id == player.id)
                .filter(PlayerAdvancedStatsDB.season == season)
                .filter(PlayerAdvancedStatsDB.source == SOURCE)
                .first()
            )

            if existing_stats:
                existing_stats.transfermarkt_id = transfermarkt_id

                for field_name, value in values.items():
                    setattr(existing_stats, field_name, value)

                updated += 1
                continue

            advanced_stats = PlayerAdvancedStatsDB(
                player_id=player.id,
                transfermarkt_id=transfermarkt_id,
                season=season,
                source=SOURCE,
                **values,
            )

            db.add(advanced_stats)
            imported += 1

        db.commit()

        print("FBref advanced stats import completed.")
        print(f"Imported: {imported}")
        print(f"Updated: {updated}")
        print(f"Skipped: {skipped}")
        print(f"Matched by transfermarkt_id: {matched_by_transfermarkt_id}")
        print(f"Matched by name + club: {matched_by_name_club}")

    except Exception as error:
        db.rollback()
        print("FBref advanced stats import failed.")
        print(error)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import_fbref_advanced_stats()
