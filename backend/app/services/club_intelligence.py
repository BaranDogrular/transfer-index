TOP_LEAGUES = {
    "Premier League",
    "LaLiga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
}

ELITE_CLUB_KEYWORDS = {
    "barcelona",
    "real madrid",
    "manchester city",
    "manchester united",
    "liverpool",
    "arsenal",
    "chelsea",
    "bayern",
    "paris saint germain",
    "psg",
    "juventus",
    "inter",
    "milan",
}


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


def normalize_text(value):
    return str(value or "").strip().lower()


def normalize_position(position):
    value = normalize_text(position).replace("-", " ")

    if "goalkeeper" in value:
        return "goalkeeper"
    if "centre back" in value or "center back" in value:
        return "centre_back"
    if "left back" in value:
        return "left_back"
    if "right back" in value:
        return "right_back"
    if "full back" in value or "wing back" in value:
        return "full_back"
    if "winger" in value or "left wing" in value or "right wing" in value:
        return "winger"
    if "centre forward" in value or "center forward" in value or "striker" in value:
        return "striker"
    if "midfield" in value:
        return "central_midfielder"

    return value or "unknown"


def count_position_depth(position_distribution):
    grouped_depth = {
        "goalkeeper": 0,
        "centre_back": 0,
        "left_back": 0,
        "right_back": 0,
        "full_back": 0,
        "central_midfielder": 0,
        "winger": 0,
        "striker": 0,
    }

    for position, count in (position_distribution or {}).items():
        group = normalize_position(position)

        if group in grouped_depth:
            grouped_depth[group] += int(count or 0)

    if grouped_depth["full_back"]:
        grouped_depth["left_back"] += grouped_depth["full_back"]
        grouped_depth["right_back"] += grouped_depth["full_back"]

    return grouped_depth


def get_budget_tier(club_context):
    total_value_m = market_value_to_millions(club_context.get("total_market_value"))
    average_value_m = market_value_to_millions(club_context.get("average_market_value"))
    league = club_context.get("league")
    club_name = normalize_text(club_context.get("club_name"))

    if total_value_m is not None or average_value_m is not None:
        if (total_value_m or 0) >= 700 or (average_value_m or 0) >= 25:
            return "elite"
        if (total_value_m or 0) >= 250 or (average_value_m or 0) >= 10:
            return "high"
        if (total_value_m or 0) >= 75 or (average_value_m or 0) >= 3:
            return "medium"
        return "low"

    if any(keyword in club_name for keyword in ELITE_CLUB_KEYWORDS):
        return "elite"
    if league in TOP_LEAGUES:
        return "high"
    if league:
        return "medium"

    return "unknown"


def get_club_level(club_context, budget_tier):
    total_value_m = market_value_to_millions(club_context.get("total_market_value"))
    average_age = to_float(club_context.get("average_age"))
    league = club_context.get("league")

    if total_value_m is not None:
        if total_value_m >= 700:
            return "elite"
        if total_value_m >= 250 or (league in TOP_LEAGUES and total_value_m >= 150):
            return "top"
        if total_value_m >= 75:
            return "mid"
        if average_age is not None and average_age <= 24:
            return "developing"
        return "mid"

    if budget_tier == "elite":
        return "elite"
    if budget_tier == "high":
        return "top"
    if average_age is not None and average_age <= 24:
        return "developing"
    if budget_tier in {"medium", "low"}:
        return "mid" if budget_tier == "medium" else "developing"

    return "unknown"


def get_needs(position_distribution):
    if not position_distribution:
        return []

    grouped_depth = count_position_depth(position_distribution)
    needs = []

    if grouped_depth["goalkeeper"] < 2:
        needs.append("GK")
    if grouped_depth["centre_back"] < 4:
        needs.append("CB")
    if grouped_depth["left_back"] < 2:
        needs.append("LB")
    if grouped_depth["right_back"] < 2:
        needs.append("RB")
    if grouped_depth["central_midfielder"] < 3:
        needs.append("CM")
    if grouped_depth["winger"] < 3:
        needs.append("Winger")
    if grouped_depth["striker"] < 2:
        needs.append("ST")

    return needs


def get_transfer_policy(average_age, budget_tier):
    if average_age is None and budget_tier == "unknown":
        return "unknown"

    if average_age is not None and average_age <= 24:
        return "young_talent"
    if budget_tier in {"elite", "high"}:
        return "prime_players" if average_age and average_age >= 26 else "balanced"
    if budget_tier in {"medium", "low"}:
        return "value_opportunity"

    return "balanced"


def build_club_intelligence(club_context):
    if not club_context:
        return None

    position_distribution = club_context.get("position_distribution") or {}
    budget_tier = get_budget_tier(club_context)
    average_age = to_float(club_context.get("average_age"))
    squad_size = club_context.get("squad_count")

    return {
        "club_name": club_context.get("club_name"),
        "league": club_context.get("league"),
        "country": club_context.get("country"),
        "budget_tier": budget_tier,
        "club_level": get_club_level(club_context, budget_tier),
        "average_age": round(average_age, 1) if average_age is not None else None,
        "squad_size": squad_size if squad_size is not None else None,
        "position_depth": position_distribution,
        "needs": get_needs(position_distribution),
        "transfer_policy": get_transfer_policy(average_age, budget_tier),
    }
