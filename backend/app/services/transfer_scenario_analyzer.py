from app.models.player_transfer_db import PlayerTransferDB
from app.services.club_context import build_club_context, resolve_club
from app.services.club_intelligence import build_club_intelligence
from app.services.player_context import (
    build_player_context,
    get_league_transition_risk,
    normalize_label,
)


TOP_LEAGUES = {
    "Premier League",
    "LaLiga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
}

COUNTRY_REGIONS = {
    "england": "western_europe",
    "scotland": "western_europe",
    "spain": "western_europe",
    "france": "western_europe",
    "germany": "western_europe",
    "italy": "western_europe",
    "portugal": "western_europe",
    "netherlands": "western_europe",
    "belgium": "western_europe",
    "austria": "western_europe",
    "switzerland": "western_europe",
    "turkey": "southern_europe",
    "türkiye": "southern_europe",
    "greece": "southern_europe",
    "croatia": "southern_europe",
    "serbia": "southern_europe",
    "brazil": "south_america",
    "argentina": "south_america",
    "uruguay": "south_america",
    "colombia": "south_america",
    "chile": "south_america",
    "paraguay": "south_america",
    "ecuador": "south_america",
    "mexico": "north_america",
    "united states": "north_america",
    "usa": "north_america",
    "canada": "north_america",
    "morocco": "africa",
    "senegal": "africa",
    "nigeria": "africa",
    "ghana": "africa",
    "ivory coast": "africa",
    "egypt": "africa",
    "japan": "asia",
    "south korea": "asia",
    "korea": "asia",
    "australia": "oceania",
}

EXPECTED_AI_RESPONSE_SCHEMA = {
    "fit_score": 0,
    "grade": "",
    "sub_scores": {},
    "strengths": [],
    "risks": [],
    "tactical_fit": "",
    "financial_risk": "",
    "contract_risk": "",
    "market_value_projection": "",
    "summary": "",
    "recommendation": "",
}

SUB_SCORE_WEIGHTS = {
    "player_quality_score": 0.18,
    "performance_score": 0.15,
    "advanced_stats_score": 0.12,
    "squad_fit_score": 0.12,
    "financial_fit_score": 0.10,
    "age_profile_score": 0.10,
    "contract_score": 0.08,
    "culture_fit_score": 0.05,
    "pressure_readiness_score": 0.05,
    "transfer_risk_score": 0.05,
}


def clamp_score(value):
    return max(0, min(100, round(value)))


def to_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def market_value_to_millions(value):
    number_value = to_float(value)

    if number_value is None:
        return None

    if number_value > 100000:
        return number_value / 1000000

    return number_value


def normalize_position(position):
    value = str(position or "").lower().replace("-", " ")

    if "goalkeeper" in value:
        return "goalkeeper"
    if "centre back" in value or "center back" in value:
        return "centre_back"
    if "left back" in value or "right back" in value or "wing back" in value:
        return "full_back"
    if "defensive midfield" in value:
        return "defensive_midfielder"
    if "attacking midfield" in value:
        return "attacking_midfielder"
    if "winger" in value or "left wing" in value or "right wing" in value:
        return "winger"
    if "centre forward" in value or "center forward" in value or "striker" in value:
        return "striker"
    if "midfield" in value:
        return "central_midfielder"

    return value.strip() or "unknown"


def normalize_country(value):
    normalized = normalize_label(value)

    if normalized == "usa":
        return "united states"
    if normalized == "turkiye":
        return "turkey"

    return normalized


def country_region(value):
    return COUNTRY_REGIONS.get(normalize_country(value))


def league_level_from_name(league):
    if league in TOP_LEAGUES:
        return "top"
    if league:
        return "mid"

    return "unknown"


def level_rank(level):
    return {
        "elite": 4,
        "top": 3,
        "mid": 2,
        "developing": 1,
        "unknown": 0,
    }.get(level or "unknown", 0)


def get_source_club_level(player_context):
    current_league = (
        player_context.get("club", {}).get("league")
        or player_context.get("profile", {}).get("league")
    )

    if current_league in TOP_LEAGUES:
        return "top"
    if current_league:
        return "mid"

    return "unknown"


def get_transfer_items(player_context):
    transfer_summary = player_context.get("transfer_history_summary")

    if isinstance(transfer_summary, dict):
        return transfer_summary.get("transfers") or []

    transfers = player_context.get("transfer_history") or []
    return transfers if isinstance(transfers, list) else []


def get_clubs_played(player_context):
    transfer_summary = player_context.get("transfer_history_summary")

    if isinstance(transfer_summary, dict):
        return transfer_summary.get("clubs_played") or []

    clubs = []

    for transfer in get_transfer_items(player_context):
        for club_name in [transfer.get("from_club"), transfer.get("to_club")]:
            if club_name and club_name not in clubs:
                clubs.append(club_name)

    return clubs


def flatten_club_players(club_context):
    players = []
    seen_player_ids = set()

    for position_players in club_context.get("current_players_by_position", {}).values():
        for player in position_players:
            player_id = player.get("id")

            if player_id in seen_player_ids:
                continue

            seen_player_ids.add(player_id)
            players.append(player)

    return players


def count_position_group(club_context, player_position):
    target_group = normalize_position(player_position)
    count = 0

    for position, players in club_context.get("current_players_by_position", {}).items():
        if normalize_position(position) == target_group:
            count += len(players)

    return count


def score_position_need(player_context, club_context):
    position = player_context["profile"].get("position")

    if not position:
        return 55

    same_position_count = count_position_group(club_context, position)

    if same_position_count == 0:
        return 92
    if same_position_count == 1:
        return 82
    if same_position_count <= 3:
        return 68

    return 45


def score_market_fit(player_context, club_context):
    player_value_m = market_value_to_millions(
        player_context.get("market", {}).get("current_market_value")
        or player_context.get("market", {}).get("current_value")
    )
    club_total_value_m = market_value_to_millions(club_context.get("total_market_value"))

    if player_value_m is None or club_total_value_m is None or club_total_value_m <= 0:
        return 55

    ratio = player_value_m / club_total_value_m

    if ratio <= 0.08:
        return 92
    if ratio <= 0.15:
        return 80
    if ratio <= 0.25:
        return 64

    return 42


def score_age_fit(player_context, club_context):
    player_age = to_float(player_context["profile"].get("age"))
    average_age = to_float(club_context.get("average_age"))

    if player_age is None or average_age is None:
        return 55

    difference = abs(player_age - average_age)

    if difference <= 2:
        return 90
    if difference <= 4:
        return 76
    if difference <= 6:
        return 62

    return 45


def score_league_fit(player_context, club_context):
    player_league = player_context["profile"].get("league")
    target_league = club_context.get("league")

    if not player_league or not target_league:
        return 55

    if player_league == target_league:
        return 88

    if player_league in TOP_LEAGUES and target_league in TOP_LEAGUES:
        return 78

    if player_league in TOP_LEAGUES or target_league in TOP_LEAGUES:
        return 66

    return 58


def score_performance(player_context):
    performance = player_context.get("performance_24_25") or {}
    minutes = to_float(performance.get("minutes")) or 0
    matches = to_float(performance.get("matches")) or 0
    goals = to_float(performance.get("goals")) or 0
    assists = to_float(performance.get("assists")) or 0

    if minutes == 0 and matches == 0:
        return 55

    score = 45
    score += min(minutes / 3000, 1) * 22
    score += min(matches / 35, 1) * 16
    score += min((goals + assists) / 20, 1) * 17
    return clamp_score(score)


def score_contract(player_context):
    years_left = to_float(player_context.get("contract", {}).get("contract_years_left"))

    if years_left is None:
        return 55
    if years_left <= 1:
        return 86
    if years_left <= 2:
        return 72
    if years_left <= 4:
        return 58

    return 42


def score_transfer_history(player_context):
    transfers = get_transfer_items(player_context)

    if not transfers:
        return 70

    loan_count = sum(
        1
        for transfer in transfers
        if transfer.get("fee_label") in {"Kiral\u0131k", "Kiral\u0131ktan geri d\u00f6nd\u00fc"}
    )

    if len(transfers) <= 3 and loan_count <= 1:
        return 82
    if len(transfers) <= 6:
        return 68

    return 48


def get_previous_teammates_from_transfer_history(player_context, club_context, db):
    player_clubs = {
        normalize_label(club_name)
        for club_name in get_clubs_played(player_context)
        if normalize_label(club_name)
    }

    if not player_clubs:
        return {
            "count": 0,
            "method": "transfer-history club overlap only",
        }

    target_player_ids = [
        player.get("id")
        for player in flatten_club_players(club_context)
        if player.get("id")
    ]

    if not target_player_ids:
        return {
            "count": 0,
            "method": "transfer-history club overlap only",
        }

    target_transfers = (
        db.query(PlayerTransferDB)
        .filter(PlayerTransferDB.player_id.in_(target_player_ids))
        .all()
    )
    overlapping_player_ids = set()

    for transfer in target_transfers:
        transfer_clubs = {
            normalize_label(transfer.from_club_name),
            normalize_label(transfer.to_club_name),
        }

        if player_clubs.intersection(transfer_clubs):
            overlapping_player_ids.add(transfer.player_id)

    return {
        "count": len(overlapping_player_ids),
        "method": "transfer-history club overlap only",
    }


def get_squad_majority_nationality(club_context):
    target_players = flatten_club_players(club_context)

    if not target_players:
        return None

    nationality_counts = {}

    for player in target_players:
        nationality = normalize_country(player.get("nationality"))

        if not nationality:
            continue

        nationality_counts[nationality] = nationality_counts.get(nationality, 0) + 1

    if not nationality_counts:
        return None

    majority_nationality, majority_count = max(
        nationality_counts.items(),
        key=lambda item: item[1],
    )

    if majority_count < 2:
        return None

    return majority_nationality


def has_previous_country_experience(player_context, target_country, db):
    if not db or not target_country:
        return False

    target_country = normalize_country(target_country)

    for transfer in get_transfer_items(player_context):
        for club_name in [transfer.get("from_club"), transfer.get("to_club")]:
            if not club_name:
                continue

            club = resolve_club(db, club_name)

            if club and normalize_country(club.country) == target_country:
                return True

    return False


def build_culture_fit_signals(player_context, club_context, db=None):
    player_nationality = normalize_country(
        player_context.get("profile", {}).get("nationality")
    )
    source_country = normalize_country(player_context.get("club", {}).get("country"))
    target_country = normalize_country(club_context.get("country"))
    player_league = (
        player_context.get("club", {}).get("league")
        or player_context.get("profile", {}).get("league")
    )
    target_league = club_context.get("league")
    source_region = country_region(source_country or player_nationality)
    target_region = country_region(target_country)
    squad_majority_nationality = get_squad_majority_nationality(club_context)

    return {
        "same_country": bool(
            target_country
            and (
                source_country == target_country
                or player_nationality == target_country
            )
        ),
        "same_league": bool(player_league and target_league and player_league == target_league),
        "same_region": bool(
            source_region and target_region and source_region == target_region
        ),
        "same_nationality_as_squad_majority": bool(
            player_nationality
            and squad_majority_nationality
            and player_nationality == squad_majority_nationality
        ),
        "previous_same_country_experience": has_previous_country_experience(
            player_context,
            target_country,
            db,
        ),
        "squad_majority_nationality": squad_majority_nationality,
    }


def score_culture_signals(signals):
    if not signals:
        return 50

    score = 50

    if signals.get("same_country"):
        score += 15
    if signals.get("same_league"):
        score += 12
    if signals.get("same_region"):
        score += 8
    if signals.get("same_nationality_as_squad_majority"):
        score += 10
    if signals.get("previous_same_country_experience"):
        score += 10

    return clamp_score(score)


def calculate_culture_fit(player_context, club_context, db):
    signals = build_culture_fit_signals(player_context, club_context, db)
    score = score_culture_signals(signals)

    if score >= 70:
        culture_fit = "High"
    elif score >= 58:
        culture_fit = "Medium"
    else:
        culture_fit = "Low"

    return {
        "same_country": signals["same_country"],
        "same_league": signals["same_league"],
        "same_region": signals["same_region"],
        "same_nationality_as_squad_majority": signals[
            "same_nationality_as_squad_majority"
        ],
        "previous_same_country_experience": signals[
            "previous_same_country_experience"
        ],
        "squad_majority_nationality": signals["squad_majority_nationality"],
        "culture_fit": culture_fit,
        "culture_fit_score": score,
    }


def calculate_financial_fit(player_context, club_context):
    player_market_value = market_value_to_millions(
        player_context.get("market", {}).get("current_market_value")
        or player_context.get("market", {}).get("current_value")
    )
    club_total_market_value = market_value_to_millions(
        club_context.get("total_market_value")
    )
    club_average_market_value = market_value_to_millions(
        club_context.get("average_market_value")
    )

    if player_market_value is None:
        financial_fit = None
    elif not club_total_market_value or not club_average_market_value:
        financial_fit = None
    else:
        total_ratio = player_market_value / club_total_market_value
        average_ratio = player_market_value / club_average_market_value

        if total_ratio <= 0.05 and average_ratio <= 1.5:
            financial_fit = "Excellent"
        elif total_ratio <= 0.10 and average_ratio <= 2.5:
            financial_fit = "Good"
        elif total_ratio <= 0.20:
            financial_fit = "Difficult"
        else:
            financial_fit = "Unrealistic"

    return {
        "player_market_value": player_market_value,
        "club_total_market_value": club_total_market_value,
        "club_average_market_value": club_average_market_value,
        "financial_fit": financial_fit,
    }


def calculate_squad_fit(player_context, club_context):
    position = player_context.get("profile", {}).get("position")
    same_position_count = count_position_group(club_context, position)

    if same_position_count <= 1:
        depth = "Low"
        position_need = "High"
        squad_fit_score = 85
    elif same_position_count <= 3:
        depth = "Medium"
        position_need = "Medium"
        squad_fit_score = 65
    else:
        depth = "High"
        position_need = "Low"
        squad_fit_score = 40

    return {
        "position": position,
        "same_position_player_count": same_position_count,
        "depth": depth,
        "position_need": position_need,
        "squad_fit_score": squad_fit_score,
    }


def build_scout_fit_layers(player_context, club_context, db):
    player_league = player_context.get("club", {}).get("league") or player_context.get(
        "profile",
        {},
    ).get("league")
    target_league = club_context.get("league")

    return {
        "culture_fit": calculate_culture_fit(player_context, club_context, db),
        "financial_fit": calculate_financial_fit(player_context, club_context),
        "squad_fit": calculate_squad_fit(player_context, club_context),
        "pressure_readiness": (
            player_context.get("derived_scout_metrics", {}).get(
                "pressure_readiness"
            )
        ),
        "league_transition_risk": get_league_transition_risk(
            player_league,
            target_league,
        ),
    }


def first_available(*values):
    for value in values:
        if value is not None:
            return value

    return None


def has_number(value):
    return to_float(value) is not None


def get_advanced_stats(player_context):
    return player_context.get("advanced_stats_24_25") or {}


def get_advanced_stat(player_context, *keys):
    advanced_stats = get_advanced_stats(player_context)

    for key in keys:
        value = to_float(advanced_stats.get(key))

        if value is not None:
            return value

    return None


def get_position_group_from_context(player_context):
    return normalize_position(player_context.get("profile", {}).get("position"))


def is_attacker_group(position_group):
    return position_group in {"winger", "striker", "attacking_midfielder"}


def is_midfielder_group(position_group):
    return position_group in {
        "central_midfielder",
        "defensive_midfielder",
        "attacking_midfielder",
    }


def is_defender_group(position_group):
    return position_group in {
        "centre_back",
        "full_back",
        "left_back",
        "right_back",
    }


def metric_component(value, elite_value, weight):
    number_value = to_float(value)

    if number_value is None or elite_value <= 0:
        return 0

    return min(max(number_value, 0) / elite_value, 1) * weight


def normalize_percentage(value):
    number_value = to_float(value)

    if number_value is None:
        return None

    if number_value <= 1:
        return number_value * 100

    return number_value


def get_club_intelligence_context(club_context):
    return (
        club_context.get("club_intelligence")
        or build_club_intelligence(club_context)
        or {}
    )


def position_need_tokens(position):
    position_group = normalize_position(position)

    if position_group == "goalkeeper":
        return {"GK"}
    if position_group == "centre_back":
        return {"CB"}
    if position_group == "left_back":
        return {"LB"}
    if position_group == "right_back":
        return {"RB"}
    if position_group == "full_back":
        return {"LB", "RB"}
    if position_group == "defensive_midfielder":
        return {"DM", "CM"}
    if position_group in {"central_midfielder", "attacking_midfielder"}:
        return {"CM"}
    if position_group == "winger":
        return {"Winger", "RW", "LW"}
    if position_group == "striker":
        return {"ST", "CF"}

    return set()


def count_position_distribution_depth(position_distribution, position):
    target_group = normalize_position(position)
    count = 0

    for source_position, source_count in (position_distribution or {}).items():
        if normalize_position(source_position) == target_group:
            count += int(source_count or 0)

    return count


def get_player_market_value_m(player_context):
    return market_value_to_millions(
        player_context.get("market", {}).get("current_market_value")
        or player_context.get("market", {}).get("current_value")
    )


def score_market_value_signal(player_context):
    value_m = get_player_market_value_m(player_context)

    if value_m is None:
        return None
    if value_m >= 120:
        return 96
    if value_m >= 80:
        return 88
    if value_m >= 50:
        return 78
    if value_m >= 25:
        return 66
    if value_m >= 10:
        return 54

    return 42


def score_player_quality(player_context):
    profile = player_context.get("profile") or {}
    market_score = score_market_value_signal(player_context)
    age_score = score_age_profile(player_context)
    performance_score = score_performance_subscore(player_context)
    advanced_score = score_advanced_stats_subscore(player_context)
    score = (
        (market_score if market_score is not None else 50) * 0.35
        + (age_score if age_score is not None else 50) * 0.20
        + (performance_score if performance_score is not None else 50) * 0.25
        + (advanced_score if advanced_score is not None else 50) * 0.20
    )
    age = to_float(profile.get("age"))

    if age is not None and age <= 22:
        score += 3

    return clamp_score(score)


def score_squad_fit_subscore(player_context, club_context):
    position = player_context.get("profile", {}).get("position")
    club_intelligence = get_club_intelligence_context(club_context)
    position_depth = (
        club_intelligence.get("position_depth")
        or club_context.get("position_distribution")
        or {}
    )
    needs = set(club_intelligence.get("needs") or [])

    if not position or not position_depth:
        return 50

    same_position_count = count_position_group(club_context, position)

    if same_position_count == 0:
        same_position_count = count_position_distribution_depth(
            position_depth,
            position,
        )

    need_match = bool(position_need_tokens(position).intersection(needs))

    if need_match:
        return clamp_score(88 if same_position_count <= 2 else 82)
    if same_position_count <= 1:
        return 78
    if same_position_count <= 3:
        return 60
    if same_position_count <= 5:
        return 45

    return 38


def score_financial_fit_subscore(player_context, club_context):
    player_value_m = get_player_market_value_m(player_context)
    club_intelligence = get_club_intelligence_context(club_context)
    budget_tier = club_intelligence.get("budget_tier")
    club_level = club_intelligence.get("club_level")

    if player_value_m is None or not budget_tier or budget_tier == "unknown":
        return 50

    if player_value_m <= 5:
        return 86 if budget_tier in {"low", "medium"} else 74

    if budget_tier == "elite":
        if player_value_m >= 100:
            return 78
        if player_value_m >= 50:
            return 84
        return 90

    if budget_tier == "high":
        if player_value_m >= 100:
            return 58
        if player_value_m >= 50:
            return 70
        if player_value_m >= 15:
            return 84
        return 88

    if budget_tier == "medium":
        if player_value_m >= 50:
            return 35
        if player_value_m >= 25:
            return 55
        if player_value_m >= 10:
            return 78
        return 86

    if budget_tier == "low":
        if player_value_m >= 25:
            return 25
        if player_value_m >= 10:
            return 45
        return 82

    return 70 if club_level in {"elite", "top"} else 50


def score_age_profile(player_context):
    age = to_float(player_context.get("profile", {}).get("age"))

    if age is None:
        return 50
    if 18 <= age <= 22:
        return 86
    if 23 <= age <= 27:
        return 90
    if 28 <= age <= 31:
        return 72
    if age >= 32:
        return 48

    return 62


def score_age_profile_subscore(player_context, club_context):
    age = to_float(player_context.get("profile", {}).get("age"))
    player_value_m = get_player_market_value_m(player_context)
    club_intelligence = get_club_intelligence_context(club_context)
    transfer_policy = club_intelligence.get("transfer_policy")
    average_age = to_float(club_intelligence.get("average_age"))

    if age is None:
        return 50

    if age >= 33:
        score = 35
    elif transfer_policy == "young_talent":
        if age <= 23:
            score = 88
        elif age <= 26:
            score = 66
        else:
            score = 48
    elif transfer_policy == "prime_players":
        if 24 <= age <= 29:
            score = 88
        elif age <= 23:
            score = 68
        elif age <= 32:
            score = 62
        else:
            score = 38
    elif transfer_policy == "value_opportunity":
        if age <= 24 and (player_value_m is None or player_value_m <= 25):
            score = 82
        elif age <= 28 and (player_value_m is None or player_value_m <= 15):
            score = 78
        elif age <= 30:
            score = 64
        else:
            score = 45
    else:
        if 24 <= age <= 29:
            score = 82
        elif age <= 23:
            score = 76
        elif age <= 32:
            score = 60
        else:
            score = 40

    if average_age is not None:
        age_difference = abs(age - average_age)

        if age_difference <= 2:
            score += 5
        elif age_difference >= 7:
            score -= 8

    return clamp_score(score)


def score_contract_subscore(player_context):
    years_left = to_float(player_context.get("contract", {}).get("contract_years_left"))

    if years_left is None:
        return 50
    if years_left <= 1:
        return 85
    if years_left <= 2:
        return 70
    if years_left <= 3:
        return 55

    return 40


def score_performance_subscore(player_context):
    performance = player_context.get("performance_24_25") or {}
    position_group = get_position_group_from_context(player_context)
    minutes = to_float(performance.get("minutes"))
    goals = to_float(performance.get("goals"))
    assists = to_float(performance.get("assists"))
    goals_per_90 = to_float(performance.get("goals_per_90"))
    assists_per_90 = to_float(performance.get("assists_per_90"))
    key_passes = get_advanced_stat(player_context, "key_passes")
    progressive_passes = get_advanced_stat(player_context, "progressive_passes")
    tackles = get_advanced_stat(player_context, "tackles")
    interceptions = get_advanced_stat(player_context, "interceptions")
    blocks = get_advanced_stat(player_context, "blocks")
    clean_sheets = get_advanced_stat(player_context, "clean_sheets")
    save_percentage = normalize_percentage(
        get_advanced_stat(player_context, "save_percentage")
    )

    if position_group == "goalkeeper":
        if not any(has_number(value) for value in [minutes, clean_sheets, save_percentage]):
            return 50

        score = 40
        score += metric_component(minutes, 3000, 25)
        score += metric_component(clean_sheets, 16, 18)
        score += metric_component(
            max((save_percentage or 0) - 55, 0),
            20,
            17,
        )
        return clamp_score(score)

    if is_attacker_group(position_group):
        if not any(
            has_number(value)
            for value in [minutes, goals, assists, goals_per_90, assists_per_90]
        ):
            return 50

        score = 35
        score += metric_component(minutes, 3000, 20)
        score += metric_component(goals, 22, 20)
        score += metric_component(assists, 14, 12)
        score += metric_component(goals_per_90, 0.65, 8)
        score += metric_component(assists_per_90, 0.38, 5)
        return clamp_score(score)

    if is_midfielder_group(position_group):
        if not any(
            has_number(value)
            for value in [minutes, assists, key_passes, progressive_passes]
        ):
            return 50

        score = 40
        score += metric_component(minutes, 3000, 20)
        score += metric_component(assists, 12, 14)
        score += metric_component(key_passes, 60, 13)
        score += metric_component(progressive_passes, 180, 13)
        return clamp_score(score)

    if is_defender_group(position_group):
        if not any(
            has_number(value)
            for value in [minutes, tackles, interceptions, blocks]
        ):
            return 50

        score = 40
        score += metric_component(minutes, 3000, 22)
        score += metric_component(tackles, 80, 13)
        score += metric_component(interceptions, 60, 13)
        score += metric_component(blocks, 60, 12)
        return clamp_score(score)

    if not any(has_number(value) for value in [minutes, goals, assists]):
        return 50

    goal_contribution_total = (goals or 0) + (assists or 0)
    score = 40
    score += metric_component(minutes, 3000, 25)
    score += metric_component(goal_contribution_total, 20, 20)
    return clamp_score(score)


def score_advanced_stats_subscore(player_context):
    advanced_stats = get_advanced_stats(player_context)

    if not advanced_stats:
        return 50

    position_group = get_position_group_from_context(player_context)
    xg = get_advanced_stat(player_context, "xg")
    xa = get_advanced_stat(player_context, "xa")
    npxg = get_advanced_stat(player_context, "npxg")
    sca = get_advanced_stat(player_context, "shot_creating_actions", "sca")
    gca = get_advanced_stat(player_context, "goal_creating_actions", "gca")
    progressive_carries = get_advanced_stat(player_context, "progressive_carries")
    progressive_passes = get_advanced_stat(player_context, "progressive_passes")
    key_passes = get_advanced_stat(player_context, "key_passes")
    tackles = get_advanced_stat(player_context, "tackles")
    interceptions = get_advanced_stat(player_context, "interceptions")
    blocks = get_advanced_stat(player_context, "blocks")
    aerials_won = get_advanced_stat(player_context, "aerials_won")
    psxg = get_advanced_stat(player_context, "psxg", "post_shot_xg")
    save_percentage = normalize_percentage(
        get_advanced_stat(player_context, "save_percentage")
    )
    clean_sheets = get_advanced_stat(player_context, "clean_sheets")

    if position_group == "goalkeeper":
        if not any(has_number(value) for value in [psxg, save_percentage, clean_sheets]):
            return 50

        score = 42
        score += metric_component(max((save_percentage or 0) - 55, 0), 20, 30)
        score += metric_component(clean_sheets, 16, 18)
        score += metric_component(psxg, 12, 10)
        return clamp_score(score)

    if is_attacker_group(position_group):
        if not any(
            has_number(value)
            for value in [xg, xa, npxg, sca, gca, progressive_carries]
        ):
            return 50

        score = 38
        score += metric_component(xg, 18, 16)
        score += metric_component(xa, 8, 10)
        score += metric_component(npxg, 16, 12)
        score += metric_component(sca, 100, 12)
        score += metric_component(gca, 15, 7)
        score += metric_component(progressive_carries, 120, 5)
        return clamp_score(score)

    if is_midfielder_group(position_group):
        if not any(
            has_number(value)
            for value in [xa, progressive_passes, progressive_carries, key_passes, sca]
        ):
            return 50

        score = 40
        score += metric_component(xa, 8, 14)
        score += metric_component(progressive_passes, 220, 16)
        score += metric_component(progressive_carries, 90, 10)
        score += metric_component(key_passes, 70, 12)
        score += metric_component(sca, 100, 8)
        return clamp_score(score)

    if is_defender_group(position_group):
        if not any(
            has_number(value)
            for value in [tackles, interceptions, blocks, aerials_won]
        ):
            return 50

        score = 42
        score += metric_component(tackles, 90, 17)
        score += metric_component(interceptions, 70, 15)
        score += metric_component(blocks, 70, 14)
        score += metric_component(aerials_won, 90, 12)
        return clamp_score(score)

    if not any(has_number(value) for value in advanced_stats.values()):
        return 50

    return clamp_score(50)


def score_culture_fit_subscore(player_context, club_context, db=None):
    return score_culture_signals(
        build_culture_fit_signals(player_context, club_context, db)
    )


def score_pressure_readiness_subscore(player_context, club_context):
    club_intelligence = get_club_intelligence_context(club_context)
    target_level = club_intelligence.get("club_level") or "unknown"
    source_level = get_source_club_level(player_context)
    target_rank = level_rank(target_level)
    source_rank = level_rank(source_level)
    current_league = (
        player_context.get("club", {}).get("league")
        or player_context.get("profile", {}).get("league")
    )
    minutes = to_float(player_context.get("performance_24_25", {}).get("minutes"))
    caps = to_float(player_context.get("national_team", {}).get("international_caps"))

    if target_rank == 0 and source_rank == 0 and minutes is None and caps is None:
        return 50

    score = 50

    if target_rank >= 3:
        if source_rank >= 3:
            score += 12
        elif source_rank == 2:
            score -= 8
        else:
            score -= 14

    if caps is not None:
        if caps >= 25:
            score += 16
        elif caps >= 5:
            score += 9
        elif caps > 0:
            score += 4

    if current_league in TOP_LEAGUES and minutes is not None:
        if minutes >= 1800:
            score += 16
        elif minutes >= 900:
            score += 8
    elif target_rank >= 3 and minutes is not None and minutes < 900:
        score -= 5

    return clamp_score(score)


def score_transfer_risk_subscore(
    player_context,
    financial_fit_score,
    squad_fit_score,
):
    age = to_float(player_context.get("profile", {}).get("age"))
    player_value_m = get_player_market_value_m(player_context)
    years_left = to_float(player_context.get("contract", {}).get("contract_years_left"))
    injury_days = to_float(player_context.get("risk_snapshot", {}).get("injury_days"))
    score = 50

    if player_value_m is not None:
        if player_value_m >= 100:
            score += 18
        elif player_value_m >= 50:
            score += 12
        elif player_value_m <= 10:
            score -= 6

    if financial_fit_score is not None and financial_fit_score < 55:
        score += 18
    elif financial_fit_score is not None and financial_fit_score >= 75:
        score -= 8

    if age is not None:
        if age >= 33:
            score += 16
        elif age >= 30:
            score += 9
        elif age <= 23:
            score -= 4

    if years_left is not None:
        if years_left > 3:
            score += 14
        elif years_left <= 1:
            score -= 8

    if squad_fit_score is not None and squad_fit_score < 55:
        score += 12
    elif squad_fit_score is not None and squad_fit_score >= 75:
        score -= 6

    if injury_days is not None:
        if injury_days >= 90:
            score += 12
        elif injury_days >= 30:
            score += 6

    return clamp_score(score)


def build_sub_scores(player_context, club_context, db=None):
    squad_fit_score = clamp_score(score_squad_fit_subscore(player_context, club_context))
    financial_fit_score = clamp_score(
        score_financial_fit_subscore(
            player_context,
            club_context,
        )
    )

    return {
        "player_quality_score": clamp_score(score_player_quality(player_context)),
        "squad_fit_score": squad_fit_score,
        "financial_fit_score": financial_fit_score,
        "age_profile_score": clamp_score(
            score_age_profile_subscore(player_context, club_context)
        ),
        "contract_score": clamp_score(score_contract_subscore(player_context)),
        "performance_score": clamp_score(score_performance_subscore(player_context)),
        "advanced_stats_score": clamp_score(score_advanced_stats_subscore(player_context)),
        "culture_fit_score": clamp_score(
            score_culture_fit_subscore(player_context, club_context, db)
        ),
        "pressure_readiness_score": clamp_score(
            score_pressure_readiness_subscore(player_context, club_context)
        ),
        "transfer_risk_score": clamp_score(
            score_transfer_risk_subscore(
                player_context,
                financial_fit_score,
                squad_fit_score,
            )
        ),
    }


def calculate_weighted_fit_score(sub_scores):
    weighted_total = 0
    available_weight = 0
    missing_scores = []

    for key, weight in SUB_SCORE_WEIGHTS.items():
        value = sub_scores.get(key)

        if value is None:
            missing_scores.append(key)
            continue

        weighted_value = 100 - value if key == "transfer_risk_score" else value
        weighted_total += weighted_value * weight
        available_weight += weight

    if not available_weight:
        return None, missing_scores

    return clamp_score(weighted_total / available_weight), missing_scores


def grade_from_score(score):
    if score is None:
        return "Poor Fit"
    if score >= 90:
        return "Elite Fit"
    if score >= 80:
        return "Strong Fit"
    if score >= 70:
        return "Good Fit"
    if score >= 60:
        return "Moderate Fit"
    if score >= 50:
        return "Risky Fit"

    return "Poor Fit"


def readable_score_name(score_key):
    return score_key.replace("_score", "").replace("_", " ").title()


def build_strengths(sub_scores, player_context, club_context):
    strengths = []

    if (sub_scores.get("squad_fit_score") or 0) >= 75:
        strengths.append("High squad need at position.")
    if (sub_scores.get("player_quality_score") or 0) >= 75:
        strengths.append("Strong overall player quality profile.")
    if (sub_scores.get("performance_score") or 0) >= 70:
        strengths.append("Strong performance profile.")
    if (sub_scores.get("advanced_stats_score") or 0) >= 70:
        strengths.append("Advanced stats support the player profile.")
    if (sub_scores.get("financial_fit_score") or 0) >= 70:
        strengths.append("Financial profile looks manageable for the target club.")
    if (sub_scores.get("contract_score") or 0) >= 70:
        strengths.append("Contract situation improves transfer feasibility.")
    if (sub_scores.get("culture_fit_score") or 0) >= 70:
        strengths.append("Objective culture-fit signals are positive.")
    if (sub_scores.get("pressure_readiness_score") or 0) >= 70:
        strengths.append("Pressure readiness indicators are strong.")
    if sub_scores.get("transfer_risk_score") is not None and sub_scores["transfer_risk_score"] <= 40:
        strengths.append("Transfer risk profile is relatively low.")
    if not strengths:
        strengths.append("Scenario has enough available data for a baseline fit estimate.")

    return strengths


def build_risks(sub_scores, missing_scores, player_context, club_context):
    risks = []
    general_missing_scores = [
        score_key
        for score_key in missing_scores
        if score_key != "advanced_stats_score"
    ]

    if general_missing_scores:
        missing_labels = ", ".join(
            readable_score_name(score_key)
            for score_key in general_missing_scores[:3]
        )
        risks.append(f"Missing verified data limits scoring for: {missing_labels}.")
    if not player_context.get("advanced_stats_24_25"):
        risks.append("Limited verified advanced stats.")
    if sub_scores.get("financial_fit_score") is not None and sub_scores["financial_fit_score"] < 55:
        risks.append("Financially difficult move.")
    if sub_scores.get("squad_fit_score") is not None and sub_scores["squad_fit_score"] < 55:
        risks.append("Target club already has notable depth in this position group.")
    if sub_scores.get("contract_score") is not None and sub_scores["contract_score"] < 55:
        risks.append("Long contract may reduce transfer feasibility.")
    if sub_scores.get("transfer_risk_score") is not None and sub_scores["transfer_risk_score"] >= 65:
        risks.append("Transfer risk is elevated by fee, contract, age, injury or squad-fit factors.")
    if sub_scores.get("performance_score") is not None and sub_scores["performance_score"] < 60:
        risks.append("Recent performance data is limited or below elite transfer confidence.")
    if sub_scores.get("culture_fit_score") is not None and sub_scores["culture_fit_score"] < 55:
        risks.append("Objective culture-fit signals are limited.")
    if not risks:
        risks.append("No major deterministic risk was detected from the available data.")

    return risks


def build_deterministic_summary(player_name, club_name, grade, fit_score, sub_scores):
    positive_labels = {
        "player_quality_score": "strong player quality",
        "performance_score": "strong performance",
        "advanced_stats_score": "advanced stats support",
        "squad_fit_score": "squad need",
        "financial_fit_score": "financial fit",
        "age_profile_score": "positive age profile",
        "contract_score": "contract feasibility",
        "culture_fit_score": "verified culture-fit signals",
        "pressure_readiness_score": "pressure readiness",
    }
    concern_labels = {
        "player_quality_score": "player quality",
        "performance_score": "performance",
        "advanced_stats_score": "advanced stats",
        "squad_fit_score": "squad depth",
        "financial_fit_score": "financial fit",
        "age_profile_score": "age profile",
        "contract_score": "contract feasibility",
        "culture_fit_score": "culture-fit signals",
        "pressure_readiness_score": "pressure readiness",
    }
    positives = [
        label
        for key, label in positive_labels.items()
        if sub_scores.get(key) is not None and sub_scores[key] >= 70
    ]
    concerns = [
        label
        for key, label in concern_labels.items()
        if sub_scores.get(key) is not None and sub_scores[key] < 55
    ]

    if sub_scores.get("transfer_risk_score") is not None:
        if sub_scores["transfer_risk_score"] >= 65:
            concerns.append("transfer risk")
        elif sub_scores["transfer_risk_score"] <= 40:
            positives.append("low transfer risk")

    positive_text = ", ".join(positives[:3]) if positives else "balanced baseline data"
    concern_text = ", ".join(concerns[:3]) if concerns else "no major deterministic concern"

    return (
        f"{player_name} to {club_name} grades as {grade} with a "
        f"{fit_score}/100 deterministic Transfer Index. The score is driven by "
        f"{positive_text}, but reduced by {concern_text}."
    )


def calculate_transfer_fit_score(player_context, club_context, db=None):
    sub_scores = build_sub_scores(player_context, club_context, db)
    fit_score, missing_scores = calculate_weighted_fit_score(sub_scores)
    fit_score = fit_score if fit_score is not None else 0
    grade = grade_from_score(fit_score)
    player_name = player_context["profile"].get("name") or "This player"
    club_name = club_context.get("club_name") or "the target club"

    return {
        "fit_score": fit_score,
        "grade": grade,
        "recommendation": grade,
        "sub_scores": sub_scores,
        "strengths": build_strengths(sub_scores, player_context, club_context),
        "risks": build_risks(
            sub_scores,
            missing_scores,
            player_context,
            club_context,
        ),
        "summary": build_deterministic_summary(
            player_name,
            club_name,
            grade,
            fit_score,
            sub_scores,
        ),
    }


def build_transfer_scenario_context(player_id, target_club, db):
    player_context = build_player_context(player_id, db)

    if not player_context:
        return None

    club_context = build_club_context(target_club, db)

    if not club_context:
        return {
            "error": "Target club not found",
            "player_context": player_context,
            "target_club_context": None,
            "scenario": {
                "player_name": player_context.get("profile", {}).get("name"),
                "target_club": target_club,
                "source_club": player_context.get("profile", {}).get("club"),
                "position": player_context.get("profile", {}).get("position"),
                "market_value": player_context.get("market", {}).get(
                    "current_market_value"
                )
                or player_context.get("market", {}).get("current_value"),
                "contract_years_left": player_context.get("contract", {}).get(
                    "contract_years_left"
                ),
            },
            "deterministic_analysis": None,
            "scout_fit_layers": None,
            "club_intelligence": None,
        }

    club_intelligence = build_club_intelligence(club_context)
    scenario = {
        "player_name": player_context.get("profile", {}).get("name"),
        "target_club": club_context.get("club_name"),
        "source_club": player_context.get("profile", {}).get("club"),
        "position": player_context.get("profile", {}).get("position"),
        "market_value": player_context.get("market", {}).get("current_market_value")
        or player_context.get("market", {}).get("current_value"),
        "contract_years_left": player_context.get("contract", {}).get(
            "contract_years_left"
        ),
    }
    scout_fit_layers = build_scout_fit_layers(player_context, club_context, db)

    return {
        "player_context": player_context,
        "target_club_context": club_context,
        "scenario": scenario,
        "deterministic_analysis": calculate_transfer_fit_score(
            player_context,
            club_context,
            db,
        ),
        "scout_fit_layers": scout_fit_layers,
        "club_intelligence": club_intelligence,
    }


def analyze_transfer_scenario(player_id, target_club, db):
    return build_transfer_scenario_context(player_id, target_club, db)


def build_ai_prompt_preview(scenario_context):
    scenario = scenario_context.get("scenario") or {}
    deterministic_analysis = scenario_context.get("deterministic_analysis") or {}
    player_context = scenario_context.get("player_context") or {}
    club_context = scenario_context.get("target_club_context") or {}
    profile = player_context.get("profile") or {}

    return (
        "Analyze this transfer scenario using the provided structured context. "
        f"Player: {scenario.get('player_name')}. "
        f"Target club: {scenario.get('target_club')}. "
        f"Source club: {scenario.get('source_club')}. "
        f"Position: {scenario.get('position')}. "
        f"Player age: {profile.get('age')}. "
        f"Target league: {club_context.get('league')}. "
        f"Deterministic baseline: {deterministic_analysis.get('fit_score')}/100 "
        f"({deterministic_analysis.get('grade')}). "
        "Return only JSON matching the expected AI response schema."
    )


def get_expected_ai_response_schema():
    return EXPECTED_AI_RESPONSE_SCHEMA.copy()
