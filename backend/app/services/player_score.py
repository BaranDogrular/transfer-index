from app.models.player_db import PlayerDB
from app.services.player_context import build_player_context


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


def score_potential(age):
    age = to_float(age)

    if age is None:
        return 55
    if age <= 20:
        return 92
    if age <= 23:
        return 86
    if age <= 26:
        return 76
    if age <= 29:
        return 66
    if age <= 32:
        return 52

    return 40


def score_performance(performance):
    minutes = to_float(performance.get("minutes")) or 0
    matches = to_float(performance.get("matches")) or 0
    goals = to_float(performance.get("goals")) or 0
    assists = to_float(performance.get("assists")) or 0

    if minutes == 0 and matches == 0:
        return 55

    score = 40
    score += min(minutes / 3200, 1) * 24
    score += min(matches / 38, 1) * 16
    score += min((goals + assists) / 25, 1) * 20
    return clamp_score(score)


def score_advanced_stats(advanced_stats):
    if not advanced_stats:
        return 55

    attacking = (
        (to_float(advanced_stats.get("xg")) or 0)
        + (to_float(advanced_stats.get("xa")) or 0)
        + (to_float(advanced_stats.get("npxg")) or 0) * 0.5
    )
    creation = (
        (to_float(advanced_stats.get("key_passes")) or 0) * 0.12
        + (to_float(advanced_stats.get("progressive_passes")) or 0) * 0.06
        + (to_float(advanced_stats.get("progressive_carries")) or 0) * 0.06
        + (to_float(advanced_stats.get("sca")) or 0) * 0.05
        + (to_float(advanced_stats.get("gca")) or 0) * 0.25
    )
    defending = (
        (to_float(advanced_stats.get("tackles")) or 0) * 0.08
        + (to_float(advanced_stats.get("interceptions")) or 0) * 0.1
        + (to_float(advanced_stats.get("blocks")) or 0) * 0.08
        + (to_float(advanced_stats.get("aerials_won")) or 0) * 0.05
    )

    return clamp_score(42 + min(attacking * 1.6, 22) + min(creation, 22) + min(defending, 14))


def score_market(market):
    value_m = market_value_to_millions(market.get("current_value"))

    if value_m is None:
        return 55
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


def score_risk(context):
    risk = context.get("risk_snapshot") or {}
    injury_days = to_float(risk.get("injury_days")) or 0
    red_cards = to_float(risk.get("red_cards")) or 0

    score = 82

    if injury_days > 180:
        score -= 32
    elif injury_days > 90:
        score -= 22
    elif injury_days > 30:
        score -= 12

    if red_cards >= 2:
        score -= 12
    elif red_cards == 1:
        score -= 6

    return clamp_score(score)


def grade_from_score(score):
    if score >= 86:
        return "Elite Player"
    if score >= 76:
        return "High Quality"
    if score >= 66:
        return "Strong Prospect"
    if score >= 52:
        return "Developing Player"

    return "Needs Monitoring"


def build_strengths(component_scores, context):
    strengths = []

    if component_scores["potential"] >= 80:
        strengths.append("Age profile gives the player strong long-term upside.")
    if component_scores["performance"] >= 72:
        strengths.append("Current-season production and minutes are strong.")
    if component_scores["advanced_stats"] >= 72:
        strengths.append("Advanced performance indicators support the profile.")
    if component_scores["market"] >= 75:
        strengths.append("Market valuation signals high external confidence.")
    if component_scores["risk"] >= 75:
        strengths.append("Risk snapshot does not flag a major availability concern.")
    if not strengths:
        strengths.append("Player has enough available data for a baseline quality score.")

    return strengths


def build_risks(component_scores, context):
    risks = []

    if component_scores["performance"] < 60:
        risks.append("Recent match output or minutes are limited.")
    if component_scores["advanced_stats"] < 60:
        risks.append("Advanced stats do not strongly separate the player yet.")
    if component_scores["risk"] < 65:
        risks.append("Availability or discipline data adds some risk.")
    if component_scores["market"] < 55:
        risks.append("Market signal is still modest compared with elite profiles.")
    if not risks:
        risks.append("No major club-independent risk was detected from the available data.")

    return risks


def analyze_player_score(player_id, db):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        return None

    context = build_player_context(player_id, db)
    component_scores = {
        "potential": score_potential(context["profile"].get("age")),
        "performance": score_performance(context.get("performance_24_25") or {}),
        "advanced_stats": score_advanced_stats(context.get("advanced_stats_24_25")),
        "market": score_market(context.get("market") or {}),
        "risk": score_risk(context),
    }
    weights = {
        "potential": 0.24,
        "performance": 0.28,
        "advanced_stats": 0.20,
        "market": 0.20,
        "risk": 0.08,
    }
    player_score = clamp_score(
        sum(component_scores[key] * weight for key, weight in weights.items())
    )
    grade = grade_from_score(player_score)

    return {
        "player": {
            "id": player.id,
            "name": player.name,
            "image_url": player.image_url,
            "club": player.club,
            "league": context["profile"].get("league"),
            "position": player.position,
            "age": player.age,
            "market_value_m": player.market_value_m,
        },
        "player_score": player_score,
        "grade": grade,
        "strengths": build_strengths(component_scores, context),
        "risks": build_risks(component_scores, context),
        "summary": (
            f"{player.name} grades as {grade} with a {player_score}/100 "
            "club-independent player score. This separates overall quality and "
            "potential from target-club transfer fit."
        ),
    }
