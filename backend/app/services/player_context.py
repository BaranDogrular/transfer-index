from app.database import SessionLocal
from app.models.player_advanced_stats_db import PlayerAdvancedStatsDB
from app.models.player_db import PlayerDB
from app.models.player_transfer_db import PlayerTransferDB
from app.models.player_valuation_db import PlayerValuationDB
from app.utils.league_names import formatLeagueName


ADVANCED_STATS_KEYS = {
    "xg": "xg",
    "xa": "xa",
    "npxg": "npxg",
    "shots": "shots",
    "shots_on_target": "shots_on_target",
    "key_passes": "key_passes",
    "progressive_passes": "progressive_passes",
    "progressive_carries": "progressive_carries",
    "sca": "shot_creating_actions",
    "gca": "goal_creating_actions",
    "tackles": "tackles",
    "interceptions": "interceptions",
    "blocks": "blocks",
    "aerials_won": "aerials_won",
    "aerials_lost": "aerials_lost",
}

LOAN_LABEL = "Kiral\u0131k"
LOAN_RETURN_LABEL = "Kiral\u0131ktan geri d\u00f6nd\u00fc"
FREE_LABEL = "Bedelsiz"


def clean_value(value):
    if isinstance(value, str):
        value = value.strip()

        if value in {"", "-"}:
            return None

    return value


def normalize_context(value):
    if isinstance(value, dict):
        return {key: normalize_context(item) for key, item in value.items()}

    if isinstance(value, list):
        return [normalize_context(item) for item in value]

    return clean_value(value)


def first_non_null(*values):
    for value in values:
        value = clean_value(value)

        if value is not None:
            return value

    return None


def market_value_m_to_eur(value):
    value = clean_value(value)

    if value is None:
        return None

    try:
        number_value = float(value)
    except Exception:
        return None

    if number_value > 100000:
        return int(round(number_value))

    return int(round(number_value * 1000000))


def format_transfer_fee(value):
    value = clean_value(value)

    if value is None:
        return None

    try:
        number_value = float(value)
    except Exception:
        return None

    if number_value <= 0:
        return None

    if number_value >= 1000000:
        return f"\u20ac{number_value / 1000000:.1f}M"

    if number_value >= 1000:
        return f"\u20ac{number_value / 1000:.0f}K"

    return f"\u20ac{number_value:.0f}"


def get_transfer_fee_label(transfer):
    transfer_type = (transfer.transfer_type or "").strip()
    fee_text = (transfer.transfer_fee_text or "").strip()
    normalized_text = f"{transfer_type} {fee_text}".lower()

    if "loan return" in normalized_text or "end of loan" in normalized_text:
        return LOAN_RETURN_LABEL

    if "loan" in normalized_text or "loaned" in normalized_text:
        return LOAN_LABEL

    if (
        "free transfer" in normalized_text
        or "free" in normalized_text
        or "abl\u00f6se yok" in normalized_text
    ):
        return FREE_LABEL

    fee = first_non_null(transfer.transfer_fee_in_eur, transfer.transfer_fee)
    formatted_fee = format_transfer_fee(fee)

    if formatted_fee:
        return formatted_fee

    if fee is not None:
        try:
            if float(fee) == 0:
                return FREE_LABEL
        except Exception:
            pass

    if fee_text and fee_text not in {"-", "?", "0", "\u20ac0"}:
        return fee_text

    return None


def serialize_advanced_stats(stats):
    if not stats:
        return None

    return {
        context_key: getattr(stats, model_key)
        for context_key, model_key in ADVANCED_STATS_KEYS.items()
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

        recent_valuations = valuations[-10:]
        valuation_history = [
            {
                "date": item.valuation_date,
                "market_value": item.market_value,
            }
            for item in recent_valuations
        ]
        current_value = (
            valuations[-1].market_value
            if valuations
            else market_value_m_to_eur(player.market_value_m)
        )
        peak_value = max((item.market_value for item in valuations), default=None)
        value_growth_percent = None

        if valuations:
            first_value = valuations[0].market_value

            if first_value and first_value > 0:
                value_growth_percent = round(
                    ((valuations[-1].market_value - first_value) / first_value) * 100,
                    2,
                )

        context = {
            "profile": {
                "name": player.name,
                "age": player.age,
                "nationality": player.nationality,
                "position": player.position,
                "club": player.club,
                "league": formatLeagueName(player.league),
                "height": player.height_cm,
                "preferred_foot": player.preferred_foot,
            },
            "contract": {
                "contract_until": player.contract_expiration_date,
                "contract_years_left": player.contract_years_left,
            },
            "market": {
                "current_value": current_value,
                "peak_value": peak_value,
                "value_history": valuation_history,
                "value_growth_percent": value_growth_percent,
            },
            "performance_24_25": {
                "matches": first_non_null(
                    player.matches,
                    advanced_stats.matches if advanced_stats else None,
                ),
                "starts": advanced_stats.starts if advanced_stats else None,
                "minutes": first_non_null(
                    player.minutes_played,
                    advanced_stats.minutes if advanced_stats else None,
                ),
                "goals": first_non_null(
                    player.goals,
                    advanced_stats.goals if advanced_stats else None,
                ),
                "assists": first_non_null(
                    player.assists,
                    advanced_stats.assists if advanced_stats else None,
                ),
                "goals_per_90": player.goals_per_90,
                "assists_per_90": player.assists_per_90,
                "yellow_cards": first_non_null(
                    player.yellow_cards,
                    advanced_stats.yellow_cards if advanced_stats else None,
                ),
                "red_cards": first_non_null(
                    player.red_cards,
                    advanced_stats.red_cards if advanced_stats else None,
                ),
            },
            "advanced_stats_24_25": serialize_advanced_stats(advanced_stats),
            "transfer_history": [
                {
                    "season": item.transfer_season,
                    "date": item.transfer_date,
                    "from_club": item.from_club_name,
                    "to_club": item.to_club_name,
                    "fee_label": get_transfer_fee_label(item),
                    "market_value": item.market_value_in_eur,
                }
                for item in transfers
            ],
            "national_team": {
                "nationality": player.nationality,
                "country_flag_url": player.country_flag_url,
                "national_team_name": player.national_team_name,
                "national_team_flag_url": player.national_team_flag_url,
                "international_caps": player.international_caps,
                "international_goals": player.international_goals,
            },
            "risk_snapshot": {
                "age": player.age,
                "injury_days": player.injury_days,
                "contract_years_left": player.contract_years_left,
                "matches": player.matches,
                "minutes": player.minutes_played,
                "red_cards": player.red_cards,
            },
        }

        return normalize_context(context)
    finally:
        if owns_session:
            db.close()
