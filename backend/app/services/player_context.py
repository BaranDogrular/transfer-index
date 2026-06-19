import re
import unicodedata

from app.database import SessionLocal
from app.models.club_db import ClubDB
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
    "passes_into_final_third": "passes_into_final_third",
    "passes_into_penalty_area": "passes_into_penalty_area",
    "sca": "shot_creating_actions",
    "shot_creating_actions": "shot_creating_actions",
    "gca": "goal_creating_actions",
    "goal_creating_actions": "goal_creating_actions",
    "tackles": "tackles",
    "interceptions": "interceptions",
    "blocks": "blocks",
    "aerials_won": "aerials_won",
    "aerials_lost": "aerials_lost",
    "yellow_cards": "yellow_cards",
    "red_cards": "red_cards",
}

LOAN_LABEL = "Kiral\u0131k"
LOAN_RETURN_LABEL = "Kiral\u0131ktan geri d\u00f6nd\u00fc"
FREE_LABEL = "Bedelsiz"

TOP_LEAGUES = {
    "Premier League",
    "LaLiga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
}
STRONG_LEAGUES = {
    "Eredivisie",
    "Liga Portugal",
    "Belgian Pro League",
    "S\u00fcper Lig",
    "Major League Soccer",
    "EFL Championship",
}

NATIONALITY_LANGUAGE_GROUPS = {
    "argentina": {"spanish"},
    "argentinian": {"spanish"},
    "austria": {"german"},
    "austrian": {"german"},
    "belgium": {"dutch", "french"},
    "belgian": {"dutch", "french"},
    "brazil": {"portuguese"},
    "brazilian": {"portuguese"},
    "croatia": {"croatian"},
    "croatian": {"croatian"},
    "denmark": {"danish"},
    "danish": {"danish"},
    "england": {"english"},
    "english": {"english"},
    "france": {"french"},
    "french": {"french"},
    "germany": {"german"},
    "german": {"german"},
    "italy": {"italian"},
    "italian": {"italian"},
    "netherlands": {"dutch"},
    "dutch": {"dutch"},
    "norway": {"norwegian"},
    "norwegian": {"norwegian"},
    "portugal": {"portuguese"},
    "portuguese": {"portuguese"},
    "spain": {"spanish"},
    "spanish": {"spanish"},
    "turkey": {"turkish"},
    "turkish": {"turkish"},
    "t\u00fcrkiye": {"turkish"},
    "uruguay": {"spanish"},
    "uruguayan": {"spanish"},
}

AI_SAFETY_INSUFFICIENT_DATA = "Insufficient verified data."


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


def normalize_label(value):
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(value).strip().lower())
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def to_float(value):
    value = clean_value(value)

    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def clamp_score(value):
    return max(0, min(100, round(value)))


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


def market_value_to_millions(value):
    number_value = to_float(value)

    if number_value is None:
        return None

    if number_value > 100000:
        return number_value / 1000000

    return number_value


def get_current_club(db, player):
    club = None

    if player.current_club_id is not None:
        club = (
            db.query(ClubDB)
            .filter(ClubDB.club_id == player.current_club_id)
            .first()
        )

    if not club and player.club:
        club = db.query(ClubDB).filter(ClubDB.name.ilike(player.club)).first()

    return club


def get_age_profile(age):
    age = to_float(age)

    if age is None:
        return None
    if 18 <= age <= 22:
        return "Elite Young Talent"
    if 23 <= age <= 27:
        return "Prime Age"
    if 28 <= age <= 31:
        return "Experienced"
    if age >= 32:
        return "Veteran"

    return "Youth"


def get_playing_time_score(minutes):
    minutes = to_float(minutes)

    if minutes is None:
        return None

    return clamp_score(min(minutes / 3000, 1) * 100)


def get_market_trend(valuations):
    if len(valuations) < 2:
        return None

    first_value = valuations[0].market_value
    current_value = valuations[-1].market_value

    if not first_value or first_value <= 0 or current_value is None:
        return None

    change_percent = ((current_value - first_value) / first_value) * 100

    if change_percent >= 10:
        return "Rising"
    if change_percent <= -10:
        return "Declining"

    return "Stable"


def get_experience_score(matches, starts, minutes):
    if matches is None and starts is None and minutes is None:
        return None

    matches = to_float(matches) or 0
    starts = to_float(starts) or 0
    minutes = to_float(minutes) or 0
    score = 0
    score += min(matches / 38, 1) * 30
    score += min(starts / 38, 1) * 25
    score += min(minutes / 3420, 1) * 45
    return clamp_score(score)


def get_transfer_stability(transfer_count):
    if transfer_count <= 2:
        return "Stable"
    if transfer_count <= 5:
        return "Moderate"

    return "Journeyman Risk"


def get_contract_risk(years_left):
    years_left = to_float(years_left)

    if years_left is None:
        return None
    if years_left <= 1:
        return "High"
    if years_left <= 3:
        return "Medium"

    return "Low"


def get_league_tier(league):
    league = formatLeagueName(league)

    if league in TOP_LEAGUES:
        return "top"
    if league in STRONG_LEAGUES:
        return "strong"
    if league:
        return "other"

    return None


def get_league_transition_risk(current_league, target_league=None):
    if not target_league:
        return None

    current_league = formatLeagueName(current_league)
    target_league = formatLeagueName(target_league)

    if not current_league or not target_league:
        return None
    if current_league == target_league:
        return "Low"
    if get_league_tier(current_league) == get_league_tier(target_league):
        return "Medium"

    return "High"


def language_groups_for_nationality(nationality):
    normalized = normalize_label(nationality)

    if not normalized:
        return set()

    groups = set()

    for part in re.split(r"\s*/\s*|\s*,\s*|\s+and\s+", normalized):
        mapped_groups = NATIONALITY_LANGUAGE_GROUPS.get(part.strip())

        if mapped_groups:
            groups.update(mapped_groups)

    return groups


def get_pressure_readiness(age, league, transfer_count, international_caps):
    if age is None and not league and international_caps is None:
        return None

    score = 0
    age = to_float(age)
    caps = to_float(international_caps) or 0

    if age is not None:
        if 23 <= age <= 29:
            score += 25
        elif 18 <= age <= 22:
            score += 20
        elif 30 <= age <= 32:
            score += 16
        else:
            score += 10

    if get_league_tier(league) == "top":
        score += 25
    elif get_league_tier(league) == "strong":
        score += 16
    elif league:
        score += 10

    if transfer_count <= 2:
        score += 20
    elif transfer_count <= 5:
        score += 12
    else:
        score += 5

    if caps >= 25:
        score += 20
    elif caps > 0:
        score += 10

    score = clamp_score(score)

    if score >= 70:
        readiness = "High"
    elif score >= 45:
        readiness = "Medium"
    else:
        readiness = "Low"

    return {
        "score": score,
        "readiness": readiness,
        "european_experience": None,
        "top_league_experience": get_league_tier(league) == "top",
        "national_team_experience": caps > 0,
    }


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


def serialize_transfer_item(item):
    return {
        "season": item.transfer_season,
        "date": item.transfer_date,
        "from_club": item.from_club_name,
        "to_club": item.to_club_name,
        "fee_label": get_transfer_fee_label(item),
        "market_value": item.market_value_in_eur,
        "transfer_fee": first_non_null(item.transfer_fee_in_eur, item.transfer_fee),
        "transfer_type": item.transfer_type,
    }


def build_transfer_summary(transfer_items):
    clubs_played = []
    seen_clubs = set()

    for item in transfer_items:
        for club_name in [item.get("from_club"), item.get("to_club")]:
            club_name = clean_value(club_name)

            if not club_name:
                continue

            normalized_club = normalize_label(club_name)

            if normalized_club in seen_clubs:
                continue

            seen_clubs.add(normalized_club)
            clubs_played.append(club_name)

    fees = [
        item.get("transfer_fee")
        for item in transfer_items
        if to_float(item.get("transfer_fee")) is not None
        and to_float(item.get("transfer_fee")) > 0
    ]
    fee_labels = [item.get("fee_label") for item in transfer_items]

    return {
        "transfers": transfer_items,
        "clubs_played": clubs_played,
        "highest_fee": max(fees) if fees else None,
        "free_transfers": sum(1 for label in fee_labels if label == FREE_LABEL),
        "loans": sum(
            1
            for label in fee_labels
            if label in {LOAN_LABEL, LOAN_RETURN_LABEL}
        ),
    }


def serialize_advanced_stats(stats):
    if not stats:
        return None

    return {
        context_key: getattr(stats, model_key)
        for context_key, model_key in ADVANCED_STATS_KEYS.items()
    }


def build_derived_scout_metrics(
    player,
    advanced_stats,
    valuations,
    transfer_summary,
    current_league,
):
    matches = first_non_null(
        player.matches,
        advanced_stats.matches if advanced_stats else None,
    )
    starts = advanced_stats.starts if advanced_stats else None
    minutes = first_non_null(
        player.minutes_played,
        advanced_stats.minutes if advanced_stats else None,
    )
    transfer_count = len(transfer_summary["transfers"])

    return {
        "age_profile": get_age_profile(player.age),
        "playing_time_score": get_playing_time_score(minutes),
        "market_trend": get_market_trend(valuations),
        "experience_score": get_experience_score(matches, starts, minutes),
        "transfer_stability": get_transfer_stability(transfer_count),
        "contract_risk": get_contract_risk(player.contract_years_left),
        "league_transition_risk": None,
        "pressure_readiness": get_pressure_readiness(
            player.age,
            current_league,
            transfer_count,
            player.international_caps,
        ),
    }


def build_objective_culture_signals(player):
    language_groups = sorted(language_groups_for_nationality(player.nationality))

    return {
        "nationality": player.nationality,
        "nationality_language_groups": language_groups,
        "same_nationality_teammates_count": None,
        "same_language_approximation": (
            "Using nationality mapping only." if language_groups else None
        ),
        "previous_teammates": None,
        "culture_fit": None,
    }


def build_ai_safety_block():
    return {
        "private_life": AI_SAFETY_INSUFFICIENT_DATA,
        "family": AI_SAFETY_INSUFFICIENT_DATA,
        "nightlife": AI_SAFETY_INSUFFICIENT_DATA,
        "alcohol": AI_SAFETY_INSUFFICIENT_DATA,
        "discipline_rumors": AI_SAFETY_INSUFFICIENT_DATA,
        "dressing_room_rumors": AI_SAFETY_INSUFFICIENT_DATA,
        "personality_speculation": AI_SAFETY_INSUFFICIENT_DATA,
        "mental_health": AI_SAFETY_INSUFFICIENT_DATA,
        "off_field_behaviour": AI_SAFETY_INSUFFICIENT_DATA,
    }


def build_player_context(player_id, db=None):
    owns_session = db is None
    db = db or SessionLocal()

    try:
        player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

        if not player:
            return None

        current_club = get_current_club(db, player)
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
        current_league = formatLeagueName(player.league)
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

        transfer_items = [serialize_transfer_item(item) for item in transfers]
        transfer_summary = build_transfer_summary(transfer_items)
        advanced_stats_context = serialize_advanced_stats(advanced_stats)
        performance_stats = {
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
        }
        derived_scout_metrics = build_derived_scout_metrics(
            player,
            advanced_stats,
            valuations,
            transfer_summary,
            current_league,
        )

        context = {
            "profile": {
                "name": player.name,
                "age": player.age,
                "nationality": player.nationality,
                "position": player.position,
                "club": player.club,
                "league": current_league,
                "height": player.height_cm,
                "preferred_foot": player.preferred_foot,
            },
            "club": {
                "current_club": player.club,
                "club_id": player.current_club_id,
                "league": current_league,
                "country": current_club.country if current_club else None,
            },
            "contract": {
                "contract_until": player.contract_expiration_date,
                "contract_years_left": player.contract_years_left,
            },
            "market": {
                "current_value": current_value,
                "current_market_value": current_value,
                "peak_value": peak_value,
                "peak_market_value": peak_value,
                "value_history": valuation_history,
                "market_value_history": valuation_history,
                "value_growth_percent": value_growth_percent,
                "market_value_growth": value_growth_percent,
                "market_trend": get_market_trend(valuations),
            },
            "performance": performance_stats,
            "performance_24_25": performance_stats,
            "advanced_stats": advanced_stats_context,
            "advanced_stats_24_25": advanced_stats_context,
            "transfer_history": transfer_items,
            "transfer_history_summary": transfer_summary,
            "derived_scout_metrics": derived_scout_metrics,
            "objective_culture_signals": build_objective_culture_signals(player),
            "ai_safety": build_ai_safety_block(),
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
                "pressure_readiness": derived_scout_metrics.get(
                    "pressure_readiness"
                ),
            },
        }

        return normalize_context(context)
    finally:
        if owns_session:
            db.close()
