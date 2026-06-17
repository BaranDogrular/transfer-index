from app.services.club_context import build_club_context
from app.services.player_context import build_player_context


TOP_LEAGUES = {
    "Premier League",
    "LaLiga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
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
        player_context.get("market", {}).get("current_value")
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
    transfers = player_context.get("transfer_history") or []

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


def grade_from_score(score):
    if score >= 82:
        return "Strong Fit"
    if score >= 68:
        return "Good Fit"
    if score >= 52:
        return "Moderate Fit"

    return "Risky Fit"


def build_strengths(component_scores, player_context, club_context):
    strengths = []

    if component_scores["position_need"] >= 75:
        strengths.append("Target club has a clear need in the player's position group.")
    if component_scores["age_fit"] >= 75:
        strengths.append("Player age fits the target club squad profile.")
    if component_scores["league_fit"] >= 75:
        strengths.append("League level transition looks manageable.")
    if component_scores["performance"] >= 70:
        strengths.append("Recent 24/25 performance gives the transfer a strong base.")
    if component_scores["contract"] >= 70:
        strengths.append("Contract situation may be workable.")
    if not strengths:
        strengths.append("Scenario has enough available data for a baseline fit estimate.")

    return strengths


def build_risks(component_scores, player_context, club_context):
    risks = []

    if component_scores["market_fit"] < 60:
        risks.append("Player valuation is heavy relative to the target club squad value.")
    if component_scores["position_need"] < 60:
        risks.append("Target club already has notable depth in this position group.")
    if component_scores["contract"] < 60:
        risks.append("Long contract length can increase transfer difficulty.")
    if component_scores["transfer_history"] < 60:
        risks.append("Transfer history suggests additional adaptation or stability risk.")
    if component_scores["performance"] < 60:
        risks.append("Recent performance data is limited or below elite transfer confidence.")
    if not risks:
        risks.append("No major deterministic risk was detected from the available data.")

    return risks


def calculate_transfer_fit_score(player_context, club_context):
    component_scores = {
        "position_need": score_position_need(player_context, club_context),
        "market_fit": score_market_fit(player_context, club_context),
        "age_fit": score_age_fit(player_context, club_context),
        "league_fit": score_league_fit(player_context, club_context),
        "performance": score_performance(player_context),
        "contract": score_contract(player_context),
        "transfer_history": score_transfer_history(player_context),
    }
    weights = {
        "position_need": 0.22,
        "market_fit": 0.16,
        "age_fit": 0.12,
        "league_fit": 0.14,
        "performance": 0.18,
        "contract": 0.10,
        "transfer_history": 0.08,
    }
    fit_score = clamp_score(
        sum(component_scores[key] * weight for key, weight in weights.items())
    )
    grade = grade_from_score(fit_score)
    player_name = player_context["profile"].get("name") or "This player"
    club_name = club_context.get("club_name") or "the target club"

    return {
        "fit_score": fit_score,
        "grade": grade,
        "strengths": build_strengths(component_scores, player_context, club_context),
        "risks": build_risks(component_scores, player_context, club_context),
        "summary": (
            f"{player_name} to {club_name} grades as {grade} with a "
            f"{fit_score}/100 deterministic fit score. The score weighs position need, "
            "market fit, age profile, league compatibility, performance, contract and "
            "transfer-history risk."
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
                "market_value": player_context.get("market", {}).get("current_value"),
                "contract_years_left": player_context.get("contract", {}).get(
                    "contract_years_left"
                ),
            },
            "deterministic_analysis": None,
        }

    scenario = {
        "player_name": player_context.get("profile", {}).get("name"),
        "target_club": club_context.get("club_name"),
        "source_club": player_context.get("profile", {}).get("club"),
        "position": player_context.get("profile", {}).get("position"),
        "market_value": player_context.get("market", {}).get("current_value"),
        "contract_years_left": player_context.get("contract", {}).get(
            "contract_years_left"
        ),
    }

    return {
        "player_context": player_context,
        "target_club_context": club_context,
        "scenario": scenario,
        "deterministic_analysis": calculate_transfer_fit_score(
            player_context,
            club_context,
        ),
    }


def analyze_transfer_scenario(player_id, target_club, db):
    return build_transfer_scenario_context(player_id, target_club, db)
