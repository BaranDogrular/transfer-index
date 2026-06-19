from app.models.player_transfer_db import PlayerTransferDB
from app.services.club_context import build_club_context
from app.services.player_context import (
    build_player_context,
    get_league_transition_risk,
    language_groups_for_nationality,
    normalize_label,
)


TOP_LEAGUES = {
    "Premier League",
    "LaLiga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
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
    "player_quality_score": 0.20,
    "squad_fit_score": 0.15,
    "financial_fit_score": 0.15,
    "performance_score": 0.15,
    "advanced_stats_score": 0.10,
    "age_profile_score": 0.08,
    "contract_score": 0.07,
    "culture_fit_score": 0.05,
    "pressure_readiness_score": 0.03,
    "transfer_risk_score": 0.02,
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


def calculate_culture_fit(player_context, club_context, db):
    player_nationality = player_context.get("profile", {}).get("nationality")
    player_language_groups = language_groups_for_nationality(player_nationality)
    target_players = flatten_club_players(club_context)
    same_nationality_count = sum(
        1
        for player in target_players
        if normalize_label(player.get("nationality"))
        and normalize_label(player.get("nationality"))
        == normalize_label(player_nationality)
    )
    same_language_count = None

    if player_language_groups:
        same_language_count = sum(
            1
            for player in target_players
            if player_language_groups.intersection(
                language_groups_for_nationality(player.get("nationality"))
            )
        )

    previous_teammates = get_previous_teammates_from_transfer_history(
        player_context,
        club_context,
        db,
    )
    previous_teammate_count = previous_teammates.get("count", 0)

    if (
        same_nationality_count >= 2
        or (same_language_count is not None and same_language_count >= 4)
        or previous_teammate_count >= 1
    ):
        culture_fit = "High"
    elif same_nationality_count >= 1 or (
        same_language_count is not None and same_language_count >= 2
    ):
        culture_fit = "Medium"
    else:
        culture_fit = "Low"

    return {
        "same_nationality_teammates_count": same_nationality_count,
        "same_language_approximation_count": same_language_count,
        "same_language_method": "nationality mapping only",
        "previous_teammates": previous_teammates,
        "culture_fit": culture_fit,
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
    derived = player_context.get("derived_scout_metrics") or {}
    component_values = [
        score_market_value_signal(player_context),
        score_age_profile(player_context),
        score_performance_subscore(player_context),
        derived.get("experience_score"),
    ]
    available_values = [
        value
        for value in component_values
        if value is not None
    ]

    if not available_values:
        return None

    score = sum(available_values) / len(available_values)

    age = to_float(profile.get("age"))

    if age is not None and age <= 22:
        score += 3

    return clamp_score(score)


def score_squad_fit_subscore(player_context, club_context):
    position = player_context.get("profile", {}).get("position")
    players_by_position = club_context.get("current_players_by_position") or {}

    if not position or not players_by_position:
        return None

    return calculate_squad_fit(player_context, club_context)["squad_fit_score"]


def score_financial_fit_subscore(player_context, club_context):
    financial_fit = calculate_financial_fit(player_context, club_context)
    fit_label = financial_fit.get("financial_fit")

    return {
        "Excellent": 92,
        "Good": 76,
        "Difficult": 48,
        "Unrealistic": 25,
    }.get(fit_label)


def score_age_profile(player_context):
    age = to_float(player_context.get("profile", {}).get("age"))

    if age is None:
        return None
    if 18 <= age <= 22:
        return 86
    if 23 <= age <= 27:
        return 90
    if 28 <= age <= 31:
        return 72
    if age >= 32:
        return 48

    return 62


def score_contract_subscore(player_context):
    years_left = to_float(player_context.get("contract", {}).get("contract_years_left"))

    if years_left is None:
        return None
    if years_left <= 1:
        return 40
    if years_left <= 3:
        return 65

    return 82


def score_performance_subscore(player_context):
    performance = player_context.get("performance_24_25") or {}
    values = [
        performance.get("matches"),
        performance.get("starts"),
        performance.get("minutes"),
        performance.get("goals"),
        performance.get("assists"),
    ]

    if all(value is None for value in values):
        return None

    minutes = to_float(performance.get("minutes")) or 0
    matches = to_float(performance.get("matches")) or 0
    starts = to_float(performance.get("starts")) or 0
    goals = to_float(performance.get("goals")) or 0
    assists = to_float(performance.get("assists")) or 0

    score = 35
    score += min(minutes / 3000, 1) * 28
    score += min(matches / 38, 1) * 14
    score += min(starts / 32, 1) * 10
    score += min((goals + assists) / 25, 1) * 13
    return clamp_score(score)


def score_advanced_stats_subscore(player_context):
    advanced_stats = player_context.get("advanced_stats_24_25")

    if not advanced_stats:
        return None

    values = [
        advanced_stats.get("xg"),
        advanced_stats.get("xa"),
        advanced_stats.get("npxg"),
        advanced_stats.get("shots"),
        advanced_stats.get("shots_on_target"),
        advanced_stats.get("key_passes"),
        advanced_stats.get("progressive_passes"),
        advanced_stats.get("progressive_carries"),
        advanced_stats.get("shot_creating_actions"),
        advanced_stats.get("sca"),
        advanced_stats.get("goal_creating_actions"),
        advanced_stats.get("gca"),
        advanced_stats.get("tackles"),
        advanced_stats.get("interceptions"),
        advanced_stats.get("blocks"),
        advanced_stats.get("aerials_won"),
    ]

    if all(value is None for value in values):
        return None

    attacking = (
        (to_float(advanced_stats.get("xg")) or 0)
        + (to_float(advanced_stats.get("xa")) or 0)
        + (to_float(advanced_stats.get("npxg")) or 0) * 0.5
    )
    creation = (
        (to_float(advanced_stats.get("key_passes")) or 0) * 0.12
        + (to_float(advanced_stats.get("progressive_passes")) or 0) * 0.06
        + (to_float(advanced_stats.get("progressive_carries")) or 0) * 0.06
        + (
            to_float(
                first_available(
                    advanced_stats.get("shot_creating_actions"),
                    advanced_stats.get("sca"),
                )
            )
            or 0
        )
        * 0.05
        + (
            to_float(
                first_available(
                    advanced_stats.get("goal_creating_actions"),
                    advanced_stats.get("gca"),
                )
            )
            or 0
        )
        * 0.25
    )
    defending = (
        (to_float(advanced_stats.get("tackles")) or 0) * 0.08
        + (to_float(advanced_stats.get("interceptions")) or 0) * 0.10
        + (to_float(advanced_stats.get("blocks")) or 0) * 0.08
        + (to_float(advanced_stats.get("aerials_won")) or 0) * 0.05
    )

    return clamp_score(
        42
        + min(attacking * 1.6, 22)
        + min(creation, 22)
        + min(defending, 14)
    )


def score_culture_fit_subscore(player_context, club_context):
    player_nationality = player_context.get("profile", {}).get("nationality")
    target_players = flatten_club_players(club_context)

    if not player_nationality or not target_players:
        return None

    player_language_groups = language_groups_for_nationality(player_nationality)
    same_nationality_count = sum(
        1
        for player in target_players
        if normalize_label(player.get("nationality"))
        and normalize_label(player.get("nationality"))
        == normalize_label(player_nationality)
    )
    same_language_count = 0

    if player_language_groups:
        same_language_count = sum(
            1
            for player in target_players
            if player_language_groups.intersection(
                language_groups_for_nationality(player.get("nationality"))
            )
        )

    if same_nationality_count >= 2 or same_language_count >= 4:
        return 85
    if same_nationality_count >= 1 or same_language_count >= 2:
        return 65

    return 45


def score_pressure_readiness_subscore(player_context):
    pressure_readiness = (
        player_context.get("derived_scout_metrics", {}).get("pressure_readiness")
        or {}
    )
    score = pressure_readiness.get("score")

    if score is None:
        return None

    return clamp_score(score)


def score_transfer_risk_subscore(player_context):
    transfer_summary = player_context.get("transfer_history_summary")
    transfers = get_transfer_items(player_context)

    if transfer_summary is None and transfers is None:
        return None

    transfer_count = len(transfers)
    loans = 0

    if isinstance(transfer_summary, dict):
        loans = to_float(transfer_summary.get("loans")) or 0

    if transfer_count <= 2:
        score = 84
    elif transfer_count <= 5:
        score = 66
    else:
        score = 45

    if loans >= 3:
        score -= 8

    return clamp_score(score)


def build_sub_scores(player_context, club_context):
    return {
        "player_quality_score": score_player_quality(player_context),
        "squad_fit_score": score_squad_fit_subscore(player_context, club_context),
        "financial_fit_score": score_financial_fit_subscore(
            player_context,
            club_context,
        ),
        "age_profile_score": score_age_profile(player_context),
        "contract_score": score_contract_subscore(player_context),
        "performance_score": score_performance_subscore(player_context),
        "advanced_stats_score": score_advanced_stats_subscore(player_context),
        "culture_fit_score": score_culture_fit_subscore(player_context, club_context),
        "pressure_readiness_score": score_pressure_readiness_subscore(player_context),
        "transfer_risk_score": score_transfer_risk_subscore(player_context),
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

        weighted_total += value * weight
        available_weight += weight

    if not available_weight:
        return None, missing_scores

    return clamp_score(weighted_total / available_weight), missing_scores


def grade_from_score(score):
    if score is None:
        return "Poor Fit"
    if score >= 85:
        return "Elite Fit"
    if score >= 70:
        return "Strong Fit"
    if score >= 55:
        return "Moderate Fit"
    if score >= 40:
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
        strengths.append("Contract risk is low.")
    if (sub_scores.get("culture_fit_score") or 0) >= 70:
        strengths.append("Objective culture-fit signals are positive.")
    if (sub_scores.get("pressure_readiness_score") or 0) >= 70:
        strengths.append("Pressure readiness indicators are strong.")
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
    if sub_scores.get("advanced_stats_score") is None:
        risks.append("Limited verified advanced stats.")
    if sub_scores.get("financial_fit_score") is not None and sub_scores["financial_fit_score"] < 55:
        risks.append("Financially difficult move.")
    if sub_scores.get("squad_fit_score") is not None and sub_scores["squad_fit_score"] < 55:
        risks.append("Target club already has notable depth in this position group.")
    if sub_scores.get("contract_score") is not None and sub_scores["contract_score"] < 55:
        risks.append("Contract risk is high.")
    if sub_scores.get("transfer_risk_score") is not None and sub_scores["transfer_risk_score"] < 55:
        risks.append("Transfer history suggests additional adaptation or stability risk.")
    if sub_scores.get("performance_score") is not None and sub_scores["performance_score"] < 60:
        risks.append("Recent performance data is limited or below elite transfer confidence.")
    if sub_scores.get("culture_fit_score") is not None and sub_scores["culture_fit_score"] < 55:
        risks.append("Objective culture-fit signals are limited.")
    if not risks:
        risks.append("No major deterministic risk was detected from the available data.")

    return risks


def calculate_transfer_fit_score(player_context, club_context):
    sub_scores = build_sub_scores(player_context, club_context)
    fit_score, missing_scores = calculate_weighted_fit_score(sub_scores)
    fit_score = fit_score if fit_score is not None else 0
    grade = grade_from_score(fit_score)
    player_name = player_context["profile"].get("name") or "This player"
    club_name = club_context.get("club_name") or "the target club"
    available_score_count = len(
        [
            value
            for value in sub_scores.values()
            if value is not None
        ]
    )

    return {
        "fit_score": fit_score,
        "grade": grade,
        "sub_scores": sub_scores,
        "strengths": build_strengths(sub_scores, player_context, club_context),
        "risks": build_risks(
            sub_scores,
            missing_scores,
            player_context,
            club_context,
        ),
        "summary": (
            f"{player_name} to {club_name} grades as {grade} with a "
            f"{fit_score}/100 deterministic fit score. The score is normalized "
            f"across {available_score_count}/10 available sub-scores and weighs "
            "player quality, squad fit, financial fit, performance, advanced stats, "
            "age profile, contract, culture fit, pressure readiness and transfer risk."
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
        }

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
        ),
        "scout_fit_layers": scout_fit_layers,
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
