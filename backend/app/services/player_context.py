from app.database import SessionLocal
from app.models.player_advanced_stats_db import PlayerAdvancedStatsDB
from app.models.player_db import PlayerDB
from app.models.player_transfer_db import PlayerTransferDB
from app.models.player_valuation_db import PlayerValuationDB
from app.utils.league_names import formatLeagueName


def serialize_advanced_stats(stats):
    if not stats:
        return None

    return {
        "season": stats.season,
        "source": stats.source,
        "matches": stats.matches,
        "starts": stats.starts,
        "minutes": stats.minutes,
        "goals": stats.goals,
        "assists": stats.assists,
        "xg": stats.xg,
        "xa": stats.xa,
        "npxg": stats.npxg,
        "shots": stats.shots,
        "shots_on_target": stats.shots_on_target,
        "key_passes": stats.key_passes,
        "progressive_passes": stats.progressive_passes,
        "passes_into_final_third": stats.passes_into_final_third,
        "passes_into_penalty_area": stats.passes_into_penalty_area,
        "progressive_carries": stats.progressive_carries,
        "shot_creating_actions": stats.shot_creating_actions,
        "goal_creating_actions": stats.goal_creating_actions,
        "tackles": stats.tackles,
        "interceptions": stats.interceptions,
        "blocks": stats.blocks,
        "aerials_won": stats.aerials_won,
        "aerials_lost": stats.aerials_lost,
        "yellow_cards": stats.yellow_cards,
        "red_cards": stats.red_cards,
        "clean_sheets": stats.clean_sheets,
        "saves": stats.saves,
        "save_percentage": stats.save_percentage,
        "goals_against": stats.goals_against,
        "pass_completion": stats.pass_completion,
    }


def build_player_context(player_id, db=None):
    owns_session = db is None
    db = db or SessionLocal()

    try:
        player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

        if not player:
            return None

        valuations = (
            db.query(PlayerValuationDB)
            .filter(PlayerValuationDB.player_id == player_id)
            .order_by(PlayerValuationDB.valuation_date.asc())
            .all()
        )
        transfers = (
            db.query(PlayerTransferDB)
            .filter(PlayerTransferDB.player_id == player_id)
            .order_by(
                PlayerTransferDB.transfer_date.desc().nullslast(),
                PlayerTransferDB.id.desc(),
            )
            .all()
        )
        advanced_stats = (
            db.query(PlayerAdvancedStatsDB)
            .filter(PlayerAdvancedStatsDB.player_id == player_id)
            .filter(PlayerAdvancedStatsDB.source == "fbref")
            .order_by(PlayerAdvancedStatsDB.season.desc())
            .first()
        )

        valuation_history = [
            {
                "date": item.valuation_date,
                "market_value": item.market_value,
                "current_club_id": item.current_club_id,
            }
            for item in valuations
        ]

        return {
            "profile": {
                "id": player.id,
                "transfermarkt_id": player.transfermarkt_id,
                "name": player.name,
                "age": player.age,
                "date_of_birth": player.date_of_birth,
                "nationality": player.nationality,
                "position": player.position,
                "club": player.club,
                "club_id": player.current_club_id,
                "league": formatLeagueName(player.league),
                "height_cm": player.height_cm,
                "preferred_foot": player.preferred_foot,
            },
            "contract": {
                "contract_expiration_date": player.contract_expiration_date,
                "contract_years_left": player.contract_years_left,
            },
            "market_value": {
                "market_value_m": player.market_value_m,
                "salary_m": player.salary_m,
            },
            "market_value_history": valuation_history,
            "transfer_history": [
                {
                    "transfer_date": item.transfer_date,
                    "season": item.transfer_season,
                    "from_club_id": item.from_club_id,
                    "to_club_id": item.to_club_id,
                    "from_club_name": item.from_club_name,
                    "to_club_name": item.to_club_name,
                    "transfer_type": item.transfer_type,
                    "transfer_fee": item.transfer_fee,
                    "transfer_fee_in_eur": item.transfer_fee_in_eur,
                    "market_value_in_eur": item.market_value_in_eur,
                }
                for item in transfers
            ],
            "advanced_stats": serialize_advanced_stats(advanced_stats),
            "performance_stats": {
                "matches": player.matches,
                "goals": player.goals,
                "assists": player.assists,
                "minutes_played": player.minutes_played,
                "goals_per_90": player.goals_per_90,
                "assists_per_90": player.assists_per_90,
                "goal_contributions": player.goal_contributions,
                "goal_contributions_per_90": player.goal_contributions_per_90,
                "minutes_per_goal": player.minutes_per_goal,
                "yellow_cards": player.yellow_cards,
                "red_cards": player.red_cards,
                "xg": player.xg,
                "xa": player.xa,
            },
        }
    finally:
        if owns_session:
            db.close()
