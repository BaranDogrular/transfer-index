import pandas as pd

from app.database import SessionLocal
from app.models.player_db import PlayerDB
from app.models.player_valuation_db import PlayerValuationDB

print("PLAYER SEASON STATS IMPORT STARTED")

APPEARANCES_PATH = "app/data/transfermarkt/appearances.csv"
GAMES_PATH = "app/data/transfermarkt/games.csv"

TARGET_SEASON = 2024


def safe_int(value, default=0):
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def import_player_stats():
    db = SessionLocal()

    try:
        print("Reading appearances.csv...")
        appearances_df = pd.read_csv(APPEARANCES_PATH)

        print("Reading games.csv...")
        games_df = pd.read_csv(GAMES_PATH)

        required_appearance_columns = {
            "game_id",
            "player_id",
            "goals",
            "assists",
            "minutes_played",
            "appearance_id",
        }

        required_game_columns = {
            "game_id",
            "season",
        }

        missing_appearance_columns = required_appearance_columns - set(
            appearances_df.columns
        )
        missing_game_columns = required_game_columns - set(games_df.columns)

        if missing_appearance_columns:
            raise ValueError(
                f"Missing columns in appearances.csv: {missing_appearance_columns}"
            )

        if missing_game_columns:
            raise ValueError(
                f"Missing columns in games.csv: {missing_game_columns}"
            )

        print(f"Filtering season: {TARGET_SEASON}/{str(TARGET_SEASON + 1)[-2:]}")

        games_df = games_df[["game_id", "season"]]

        merged_df = appearances_df.merge(
            games_df,
            on="game_id",
            how="left",
        )

        season_df = merged_df[merged_df["season"] == TARGET_SEASON]

        print(f"Season appearance rows: {len(season_df)}")

        print("Aggregating player season stats...")

        stats_df = (
            season_df.groupby("player_id")
            .agg(
                matches=("appearance_id", "count"),
                goals=("goals", "sum"),
                assists=("assists", "sum"),
                minutes_played=("minutes_played", "sum"),
            )
            .reset_index()
        )

        print(f"Aggregated players: {len(stats_df)}")

        players_by_transfermarkt_id = {
            player.transfermarkt_id: player
            for player in db.query(PlayerDB).all()
            if player.transfermarkt_id is not None
        }

        print(f"Players in database: {len(players_by_transfermarkt_id)}")

        updated = 0
        skipped = 0

        for _, row in stats_df.iterrows():
            transfermarkt_id = safe_int(row.get("player_id"))

            player = players_by_transfermarkt_id.get(transfermarkt_id)

            if not player:
                skipped += 1
                continue

            player.matches = safe_int(row.get("matches"))
            player.goals = safe_int(row.get("goals"))
            player.assists = safe_int(row.get("assists"))

            updated += 1

        db.commit()

        print("Player season stats import completed.")
        print(f"Updated players: {updated}")
        print(f"Skipped players: {skipped}")

    except Exception as error:
        db.rollback()
        print("Player season stats import failed.")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    import_player_stats()