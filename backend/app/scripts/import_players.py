import csv

from app.database import SessionLocal
from app.models.player_db import PlayerDB
from app.models.player_advanced_stats_db import PlayerAdvancedStatsDB


db = SessionLocal()


def import_players(csv_file):

    with open(csv_file, newline="", encoding="utf-8") as file:

        reader = csv.DictReader(file)

        for row in reader:

            player = PlayerDB(

                # BASIC
                name=row["name"],
                age=int(row["age"]),
                position=row["position"],
                club=row["club"],

                # NEW
                nationality=row["nationality"],
                preferred_foot=row["preferred_foot"],

                height_cm=int(row["height_cm"]),
                weight_kg=int(row["weight_kg"]),

                league=row["league"],

                image_url=row["image_url"],

                # PERFORMANCE
                goals=int(row["goals"]),
                assists=int(row["assists"]),
                matches=int(row["matches"]),

                xg=float(row["xg"]),
                xa=float(row["xa"]),

                # FINANCIAL
                market_value_m=float(row["market_value_m"]),
                salary_m=float(row["salary_m"]),

                # RISK
                injury_days=int(row["injury_days"]),
                contract_years_left=float(
                    row["contract_years_left"]
                ),
            )

            db.add(player)

        db.commit()

        print("Players imported successfully.")


if __name__ == "__main__":

    import_players("players.csv")
