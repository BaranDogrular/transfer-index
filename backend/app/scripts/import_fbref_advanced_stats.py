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
UNMATCHED_CSV_PATH = os.path.join(BASE_DIR, "data", "skipped_fbref_players.csv")
SOURCE = "fbref"
DEFAULT_SEASON = "2024/25"
SAMPLE_COLUMNS = [
    "player",
    "squad",
    "comp",
    "season",
    "matches",
    "starts",
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
    "yellow_cards",
    "red_cards",
    "clean_sheets",
    "saves",
    "save_percentage",
    "goals_against",
    "pass_completion",
]


FIELD_ALIASES = {
    "transfermarkt_id": [
        "transfermarkt_id",
        "transfermarkt_player_id",
        "tm_player_id",
        "tm_id",
    ],
    "player_name": ["player", "name", "player_name"],
    "club": ["club", "squad", "team", "current_club", "current_club_name"],
    "league": ["comp", "competition", "league"],
    "season": ["season", "year", "season_name"],
    "matches": ["matches", "mp", "playing_time_mp", "mp_stats_playing_time"],
    "starts": ["starts", "playing_time_starts", "starts_stats_playing_time"],
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
    "blocks": ["blocks_stats_defense", "blocks", "block", "blk"],
    "aerials_won": ["aerials_won", "aerial_duels_won", "won_stats_misc", "won"],
    "aerials_lost": [
        "aerials_lost",
        "aerial_duels_lost",
        "lost_stats_misc",
        "lost",
    ],
    "yellow_cards": ["yellow_cards", "crdy", "cards_yellow", "crdy_stats_misc"],
    "red_cards": ["red_cards", "crdr", "cards_red", "crdr_stats_misc"],
    "clean_sheets": ["clean_sheets", "cs", "cs_stats_keeper"],
    "saves": ["saves"],
    "save_percentage": ["save_percentage", "save_pct", "savepct"],
    "goals_against": ["goals_against", "ga", "ga_stats_keeper"],
    "pass_completion": [
        "pass_completion",
        "cmp_pct_stats_keeper_adv",
        "cmppct_stats_keeper_adv",
    ],
}

STAT_FIELDS = [
    "matches",
    "starts",
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
    "yellow_cards",
    "red_cards",
    "clean_sheets",
    "saves",
    "save_percentage",
    "goals_against",
    "pass_completion",
]

INTEGER_FIELDS = {
    "matches",
    "starts",
    "minutes",
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "clean_sheets",
    "saves",
    "goals_against",
}
NON_ADDITIVE_FIELDS = {"save_percentage", "pass_completion"}


def print_sample_schema():
    print("Expected fbref_player_stats.csv schema:")
    print(",".join(SAMPLE_COLUMNS))
    print("Alternative FBref columns are also supported:")
    print("Player -> player, Squad -> squad, Comp -> league, Min -> minutes")
    print("Gls -> goals, Ast -> assists, xAG -> xa, Sh -> shots, SoT -> shots_on_target")
    print("KP -> key_passes, PrgP -> progressive_passes, PrgC -> progressive_carries")
    print("SCA -> shot_creating_actions, GCA -> goal_creating_actions")
    print("Tkl -> tackles, Int -> interceptions, Blocks -> blocks")
    print("MP -> matches, Starts -> starts, CrdY -> yellow_cards, CrdR -> red_cards")
    print("CS -> clean_sheets, Saves -> saves, Save% -> save_percentage, GA -> goals_against")


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


def get_raw_value(row, column_lookup, field_name):
    value = get_column_value(row, column_lookup, field_name)

    if value is None or pd.isna(value):
        return ""

    return value


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
    players_by_name = {}

    for player in players:
        normalized_name = normalize_text(player.name)

        if not normalized_name:
            continue

        players_by_name.setdefault(normalized_name, []).append(player)

    return players_by_transfermarkt_id, players_by_name_club, players_by_name


def resolve_player(
    row,
    column_lookup,
    season,
    players_by_transfermarkt_id,
    players_by_name_club,
    players_by_name,
):
    transfermarkt_id = parse_int(get_column_value(row, column_lookup, "transfermarkt_id"))

    if transfermarkt_id is not None:
        player = players_by_transfermarkt_id.get(transfermarkt_id)

        if player:
            return player, transfermarkt_id, "transfermarkt_id"

    player_name = get_column_value(row, column_lookup, "player_name")
    club_name = get_column_value(row, column_lookup, "club")
    normalized_player_name = normalize_text(player_name)
    normalized_club_name = normalize_text(club_name)

    player = players_by_name_club.get(
        (
            normalized_player_name,
            normalized_club_name,
        )
    )

    if player:
        return player, player.transfermarkt_id, "name_club"

    if season and normalized_player_name and normalized_club_name:
        for candidate in players_by_name.get(normalized_player_name, []):
            normalized_candidate_club = normalize_text(candidate.club)

            if (
                normalized_club_name in normalized_candidate_club
                or normalized_candidate_club in normalized_club_name
            ):
                return candidate, candidate.transfermarkt_id, "name_squad_season"

    if season and normalized_player_name:
        candidates = players_by_name.get(normalized_player_name, [])

        if len(candidates) == 1:
            player = candidates[0]
            return player, player.transfermarkt_id, "name_season"

    return None, transfermarkt_id, "unmatched"


def assign_values(stats, values):
    for field_name, value in values.items():
        setattr(stats, field_name, value)


def merge_values(stats, values):
    for field_name, value in values.items():
        if value is None:
            continue

        current_value = getattr(stats, field_name)

        if field_name in NON_ADDITIVE_FIELDS:
            if current_value is None:
                setattr(stats, field_name, value)
            continue

        setattr(stats, field_name, (current_value or 0) + value)


def import_fbref_advanced_stats():
    if not os.path.exists(CSV_PATH):
        print(f"FBref advanced stats CSV not found: {CSV_PATH}")
        print("Place the file at app/data/fbref_player_stats.csv.")
        print_sample_schema()
        return

    db = SessionLocal()

    try:
        print("Reading fbref_player_stats.csv...")
        df = pd.read_csv(CSV_PATH)

        print("Inspecting CSV columns:")
        print(list(df.columns))

        column_lookup = {}
        for column_name in df.columns:
            column_lookup.setdefault(normalize_column_name(column_name), column_name)
        mapped_columns = {}
        for field_name, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                column_name = column_lookup.get(normalize_column_name(alias))

                if column_name is not None:
                    mapped_columns[field_name] = column_name
                    break

        print("Mapped fields:")
        print(sorted(mapped_columns.keys()))

        if "season" not in mapped_columns:
            print(f"Season column not found. Using default season: {DEFAULT_SEASON}")

        (
            players_by_transfermarkt_id,
            players_by_name_club,
            players_by_name,
        ) = build_player_maps(db)

        updated = 0
        imported = 0
        skipped = 0
        matched_by_transfermarkt_id = 0
        matched_by_name_club = 0
        matched_by_name_squad_season = 0
        matched_by_name_season = 0
        unmatched_rows = []
        stats_by_key = {}

        for _, row in df.iterrows():
            season = normalize_season(get_column_value(row, column_lookup, "season"))

            if not season and "season" not in mapped_columns:
                season = DEFAULT_SEASON

            if not season:
                skipped += 1
                unmatched_rows.append(
                    {
                        "player": get_raw_value(row, column_lookup, "player_name"),
                        "squad": get_raw_value(row, column_lookup, "club"),
                        "league": get_raw_value(row, column_lookup, "league"),
                        "season": "",
                        "transfermarkt_id": get_raw_value(
                            row,
                            column_lookup,
                            "transfermarkt_id",
                        ),
                        "reason": "missing season",
                    }
                )
                continue

            player, transfermarkt_id, match_type = resolve_player(
                row,
                column_lookup,
                season,
                players_by_transfermarkt_id,
                players_by_name_club,
                players_by_name,
            )

            if not player:
                skipped += 1
                unmatched_rows.append(
                    {
                        "player": get_raw_value(row, column_lookup, "player_name"),
                        "squad": get_raw_value(row, column_lookup, "club"),
                        "league": get_raw_value(row, column_lookup, "league"),
                        "season": season,
                        "transfermarkt_id": transfermarkt_id or "",
                        "reason": "no matching player",
                    }
                )
                continue

            if match_type == "transfermarkt_id":
                matched_by_transfermarkt_id += 1
            elif match_type == "name_club":
                matched_by_name_club += 1
            elif match_type == "name_squad_season":
                matched_by_name_squad_season += 1
            elif match_type == "name_season":
                matched_by_name_season += 1

            values = {}

            for field_name in STAT_FIELDS:
                raw_value = get_column_value(row, column_lookup, field_name)
                values[field_name] = (
                    parse_int(raw_value)
                    if field_name in INTEGER_FIELDS
                    else parse_float(raw_value)
                )

            existing_stats = (
                stats_by_key.get((player.id, season, SOURCE))
                or db.query(PlayerAdvancedStatsDB)
                .filter(PlayerAdvancedStatsDB.player_id == player.id)
                .filter(PlayerAdvancedStatsDB.season == season)
                .filter(PlayerAdvancedStatsDB.source == SOURCE)
                .first()
            )

            if existing_stats:
                existing_stats.transfermarkt_id = transfermarkt_id

                if (player.id, season, SOURCE) in stats_by_key:
                    merge_values(existing_stats, values)
                else:
                    assign_values(existing_stats, values)
                    stats_by_key[(player.id, season, SOURCE)] = existing_stats

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
            stats_by_key[(player.id, season, SOURCE)] = advanced_stats
            imported += 1

        db.commit()

        if unmatched_rows:
            pd.DataFrame(unmatched_rows).to_csv(UNMATCHED_CSV_PATH, index=False)
        elif os.path.exists(UNMATCHED_CSV_PATH):
            os.remove(UNMATCHED_CSV_PATH)

        print("FBref advanced stats import completed.")
        print(f"Total rows: {len(df)}")
        print(f"Imported: {imported}")
        print(f"Updated: {updated}")
        print(f"Skipped: {skipped}")
        print(f"Unmatched players CSV path: {UNMATCHED_CSV_PATH}")
        print(f"Matched by transfermarkt_id: {matched_by_transfermarkt_id}")
        print(f"Matched by name + club: {matched_by_name_club}")
        print(f"Matched by player + squad + season: {matched_by_name_squad_season}")
        print(f"Matched by player + season: {matched_by_name_season}")

    except Exception as error:
        db.rollback()
        print("FBref advanced stats import failed.")
        print(error)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import_fbref_advanced_stats()
