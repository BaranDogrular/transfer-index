import json
import logging
import re
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from app.database import SessionLocal
from app.models.transfer_scenario_analysis_db import TransferScenarioAnalysisDB
from app.services.transfer_scenario_analyzer import (
    EXPECTED_AI_RESPONSE_SCHEMA,
    build_transfer_scenario_context,
    count_position_distribution_depth,
    market_value_to_millions,
    normalize_position,
)

CACHE_TTL_DAYS = 7
logger = logging.getLogger(__name__)

AI_INTERPRETATION_SCHEMA = {
    "recommendation": "",
    "summary": "",
    "tactical_fit": "",
    "financial_risk": "",
    "contract_risk": "",
    "squad_fit": "",
    "culture_fit": "",
    "main_strengths": [],
    "main_risks": [],
    "missing_data_notes": [],
}


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None)


def get_empty_ai_fields():
    return EXPECTED_AI_RESPONSE_SCHEMA.copy()


def clamp_fit_score(value):
    try:
        return max(0, min(100, round(float(value))))
    except Exception:
        return 0


def normalize_string(value):
    if value is None:
        return ""

    return str(value).strip()


def normalize_list(value):
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def strip_json_code_fence(value):
    text = str(value or "").strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return text


def normalize_ai_response(value, deterministic):
    normalized = get_empty_ai_fields()
    main_strengths = normalize_list(
        value.get("main_strengths", value.get("strengths"))
    )
    main_risks = normalize_list(value.get("main_risks", value.get("risks")))

    normalized.update(
        {
            "fit_score": deterministic.get("fit_score"),
            "grade": deterministic.get("grade", ""),
            "sub_scores": deterministic.get("sub_scores", {}),
            "strengths": main_strengths,
            "risks": main_risks,
            "main_strengths": main_strengths,
            "main_risks": main_risks,
            "tactical_fit": normalize_string(value.get("tactical_fit")),
            "financial_risk": normalize_string(value.get("financial_risk")),
            "contract_risk": normalize_string(value.get("contract_risk")),
            "squad_fit": normalize_string(value.get("squad_fit")),
            "culture_fit": normalize_string(value.get("culture_fit")),
            "missing_data_notes": normalize_list(value.get("missing_data_notes")),
            "market_value_projection": normalize_string(
                value.get("market_value_projection")
            ),
            "summary": normalize_string(value.get("summary")),
            "recommendation": normalize_string(value.get("recommendation")),
        }
    )
    return normalized


def stable_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
        allow_nan=False,
    )


def build_context_hash(ai_transfer_context):
    return sha256(stable_json(ai_transfer_context).encode("utf-8")).hexdigest()


def is_cache_fresh(cached_analysis):
    if not cached_analysis or not cached_analysis.updated_at:
        return False

    return cached_analysis.updated_at >= utc_now() - timedelta(
        days=CACHE_TTL_DAYS
    )


def serialize_cached_analysis(cached_analysis):
    sub_scores = cached_analysis.sub_scores or {}
    cached_response = get_empty_ai_fields()
    cached_response.update(
        {
            "source": "cache",
            "context_hash": cached_analysis.context_hash,
            "fit_score": cached_analysis.fit_score,
            "grade": cached_analysis.grade or "",
            "sub_scores": sub_scores,
            "strengths": cached_analysis.strengths or [],
            "risks": cached_analysis.risks or [],
            "main_strengths": cached_analysis.strengths or [],
            "main_risks": cached_analysis.risks or [],
            "recommendation": cached_analysis.recommendation or "",
            "summary": cached_analysis.summary or "",
            "tactical_fit": cached_analysis.tactical_fit or "",
            "financial_risk": cached_analysis.financial_risk or "",
            "contract_risk": cached_analysis.contract_risk or "",
            "squad_fit": cached_analysis.squad_fit or "",
            "culture_fit": cached_analysis.culture_fit or "",
            "missing_data_notes": cached_analysis.missing_data_notes or [],
            "missing_data": [
                key for key, value in sub_scores.items() if value is None
            ],
            "market_value_projection": cached_analysis.market_value_projection or "",
        }
    )
    return cached_response


def get_cached_transfer_analysis(context_hash, db=None):
    owns_session = db is None
    db = db or SessionLocal()

    try:
        cached_analysis = (
            db.query(TransferScenarioAnalysisDB)
            .filter(TransferScenarioAnalysisDB.context_hash == context_hash)
            .first()
        )

        if not is_cache_fresh(cached_analysis):
            return None

        return serialize_cached_analysis(cached_analysis)
    finally:
        if owns_session:
            db.close()


def save_transfer_analysis_cache(
    player_id,
    target_club,
    context_hash,
    ai_response,
    db=None,
):
    if (ai_response or {}).get("source") == "fallback":
        return None

    owns_session = db is None
    db = db or SessionLocal()

    try:
        cached_analysis = (
            db.query(TransferScenarioAnalysisDB)
            .filter(TransferScenarioAnalysisDB.context_hash == context_hash)
            .first()
        )

        if not cached_analysis:
            cached_analysis = TransferScenarioAnalysisDB(
                player_id=player_id,
                target_club=target_club,
                context_hash=context_hash,
                created_at=utc_now(),
            )
            db.add(cached_analysis)

        cached_analysis.source = ai_response.get("source") or "openai"
        cached_analysis.fit_score = ai_response.get("fit_score")
        cached_analysis.grade = ai_response.get("grade")
        cached_analysis.sub_scores = ai_response.get("sub_scores") or {}
        cached_analysis.strengths = ai_response.get("strengths") or []
        cached_analysis.risks = ai_response.get("risks") or []
        cached_analysis.recommendation = ai_response.get("recommendation")
        cached_analysis.summary = ai_response.get("summary")
        cached_analysis.tactical_fit = ai_response.get("tactical_fit")
        cached_analysis.financial_risk = ai_response.get("financial_risk")
        cached_analysis.contract_risk = ai_response.get("contract_risk")
        cached_analysis.squad_fit = ai_response.get("squad_fit")
        cached_analysis.culture_fit = ai_response.get("culture_fit")
        cached_analysis.missing_data_notes = (
            ai_response.get("missing_data_notes") or []
        )
        cached_analysis.market_value_projection = ai_response.get(
            "market_value_projection"
        )
        cached_analysis.updated_at = utc_now()

        db.commit()
        return serialize_cached_analysis(cached_analysis)
    except Exception:
        db.rollback()
        logger.warning("Transfer scenario AI cache write failed.")
        return None
    finally:
        if owns_session:
            db.close()


def fallback_from_context(scenario_context, reason, context_hash=None):
    deterministic = scenario_context.get("deterministic_analysis") or {}
    scout_fit_layers = scenario_context.get("scout_fit_layers") or {}
    missing_data = deterministic.get("missing_data") or []
    missing_data_notes = deterministic.get("missing_data_notes") or [
        f"No verified data was available for {item}." for item in missing_data
    ]
    fallback = get_empty_ai_fields()
    fallback.update(
        {
            "source": "fallback",
            "context_hash": context_hash,
            "fit_score": deterministic.get("fit_score"),
            "grade": deterministic.get("grade"),
            "sub_scores": deterministic.get("sub_scores", {}),
            "strengths": deterministic.get("strengths", []),
            "risks": deterministic.get("risks", []),
            "main_strengths": deterministic.get("strengths", []),
            "main_risks": deterministic.get("risks", []),
            "tactical_fit": "Not available in deterministic fallback.",
            "financial_risk": "See deterministic risks.",
            "contract_risk": "See deterministic risks.",
            "squad_fit": (
                scout_fit_layers.get("squad_fit", {}).get("position_need")
                if isinstance(scout_fit_layers.get("squad_fit"), dict)
                else ""
            ),
            "culture_fit": (
                scout_fit_layers.get("culture_fit", {}).get("culture_fit")
                if isinstance(scout_fit_layers.get("culture_fit"), dict)
                else ""
            ),
            "missing_data": missing_data,
            "missing_data_notes": missing_data_notes,
            "market_value_projection": "Not available in deterministic fallback.",
            "summary": deterministic.get("summary") or reason,
            "recommendation": deterministic.get("grade")
            or "Insufficient deterministic data.",
            "fallback_reason": reason,
        }
    )
    return fallback


def get_nested(value, *keys):
    current = value

    for key in keys:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


POSITION_PERFORMANCE_KEYS = {
    "striker": (
        "goals",
        "xg",
        "npxg",
        "shots",
        "shots_on_target",
    ),
    "winger": (
        "goals",
        "assists",
        "xa",
        "progressive_carries",
        "key_passes",
        "shot_creating_actions",
        "goal_creating_actions",
    ),
    "central_midfielder": (
        "progressive_passes",
        "xa",
        "key_passes",
        "shot_creating_actions",
        "goal_creating_actions",
        "passes_into_final_third",
    ),
    "attacking_midfielder": (
        "progressive_passes",
        "xa",
        "key_passes",
        "shot_creating_actions",
        "goal_creating_actions",
        "passes_into_final_third",
    ),
    "defensive_midfielder": (
        "tackles",
        "interceptions",
        "progressive_passes",
        "blocks",
    ),
    "centre_back": (
        "interceptions",
        "tackles",
        "blocks",
        "aerials_won",
        "progressive_passes",
    ),
    "full_back": (
        "tackles",
        "interceptions",
        "progressive_carries",
        "progressive_passes",
        "xa",
        "key_passes",
    ),
    "goalkeeper": (
        "clean_sheets",
        "saves",
        "save_percentage",
        "goals_against",
        "pass_completion",
    ),
}


def first_not_none(*values):
    for value in values:
        if value is not None:
            return value

    return None


def build_position_relevant_performance(player_context):
    profile = player_context.get("profile") or {}
    performance = player_context.get("performance_24_25") or {}
    advanced_stats = player_context.get("advanced_stats_24_25") or {}
    position_group = normalize_position(profile.get("position"))
    available_values = {
        "matches": first_not_none(
            performance.get("matches"),
            advanced_stats.get("matches"),
        ),
        "starts": first_not_none(
            performance.get("starts"),
            advanced_stats.get("starts"),
        ),
        "minutes": first_not_none(
            performance.get("minutes"),
            advanced_stats.get("minutes"),
        ),
        "goals": first_not_none(
            performance.get("goals"),
            advanced_stats.get("goals"),
        ),
        "assists": first_not_none(
            performance.get("assists"),
            advanced_stats.get("assists"),
        ),
        **advanced_stats,
    }
    relevant_keys = POSITION_PERFORMANCE_KEYS.get(
        position_group,
        ("goals", "assists"),
    )
    output = {
        "matches": available_values.get("matches"),
        "starts": available_values.get("starts"),
        "minutes": available_values.get("minutes"),
    }
    output.update({key: available_values.get(key) for key in relevant_keys})
    return output


def top_distribution_items(distribution, limit=5):
    sorted_items = sorted(
        (distribution or {}).items(),
        key=lambda item: (-int(item[1] or 0), str(item[0])),
    )
    return {key: value for key, value in sorted_items[:limit]}


def build_compact_ai_context(scenario_context):
    player_context = scenario_context.get("player_context") or {}
    club_context = scenario_context.get("target_club_context") or {}
    scenario = scenario_context.get("scenario") or {}
    deterministic = scenario_context.get("deterministic_analysis") or {}
    profile = player_context.get("profile") or {}
    market = player_context.get("market") or {}
    contract = player_context.get("contract") or {}
    squad_profile = club_context.get("squad_profile") or {}
    financial_profile = club_context.get("financial_profile") or {}
    position_depth = (
        club_context.get("position_depth")
        or squad_profile.get("position_distribution")
        or club_context.get("position_distribution")
        or {}
    )
    position_group = normalize_position(profile.get("position"))

    return {
        "player": {
            "name": profile.get("name"),
            "age": profile.get("age"),
            "position": profile.get("position"),
            "current_club": (
                get_nested(player_context, "club", "current_club")
                or profile.get("club")
                or scenario.get("source_club")
            ),
            "market_value": (
                market_value_to_millions(
                    first_not_none(
                        market.get("current_market_value"),
                        market.get("current_value"),
                        scenario.get("market_value"),
                    )
                )
            ),
            "contract_years_left": (
                first_not_none(
                    contract.get("contract_years_left"),
                    scenario.get("contract_years_left"),
                )
            ),
        },
        "performance": build_position_relevant_performance(player_context),
        "target_club": {
            "name": get_nested(club_context, "club", "name")
            or club_context.get("club_name")
            or scenario.get("target_club"),
            "league": get_nested(club_context, "club", "league")
            or club_context.get("league"),
            "squad_profile_summary": {
                "squad_count": get_nested(club_context, "club", "squad_count")
                or club_context.get("squad_count"),
                "average_age": first_not_none(
                    get_nested(club_context, "club", "average_age"),
                    club_context.get("average_age"),
                ),
                "age_distribution": squad_profile.get("age_distribution")
                or club_context.get("age_distribution")
                or {},
                "foot_distribution": squad_profile.get("foot_distribution")
                or club_context.get("foot_distribution")
                or {},
                "top_nationalities": top_distribution_items(
                    squad_profile.get("nationality_distribution")
                    or club_context.get("nationality_distribution")
                    or {}
                ),
            },
            "position_depth": {
                "position_group": position_group,
                "same_position_player_count": count_position_distribution_depth(
                    position_depth,
                    profile.get("position"),
                ),
                "distribution": position_depth,
            },
            "financial_profile_summary": {
                "total_market_value": market_value_to_millions(
                    club_context.get("total_market_value")
                ),
                "average_market_value": market_value_to_millions(
                    club_context.get("average_market_value")
                ),
                "median_player_value": market_value_to_millions(
                    financial_profile.get("median_player_value")
                ),
                "top_player_value": market_value_to_millions(
                    financial_profile.get("top_player_value")
                ),
                "value_concentration": financial_profile.get(
                    "value_concentration"
                ),
                "market_value_unit": "EUR millions",
            },
        },
        "analysis": {
            "fit_score": deterministic.get("fit_score"),
            "grade": deterministic.get("grade"),
            "sub_scores": deterministic.get("sub_scores"),
            "strengths": deterministic.get("strengths"),
            "risks": deterministic.get("risks"),
            "missing_data": deterministic.get("missing_data") or [],
        },
    }


def build_ai_transfer_context(player_id, target_club, db=None):
    owns_session = db is None
    db = db or SessionLocal()

    try:
        scenario_context = build_transfer_scenario_context(player_id, target_club, db)

        if not scenario_context or scenario_context.get("error"):
            return None

        return build_compact_ai_context(scenario_context)
    finally:
        if owns_session:
            db.close()


def build_prompt_payload(scenario_context):
    return build_compact_ai_context(scenario_context)


def build_ai_messages(scenario_context):
    prompt_payload = build_prompt_payload(scenario_context)

    return [
        {
            "role": "system",
            "content": (
                "You are a professional football scout. Use only the provided "
                "structured data. Do not recalculate fit_score or sub_scores. "
                "Do not invent facts. If data is missing, mention it in "
                "missing_data_notes. Return only valid JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                "Write a concise transfer scenario interpretation for this "
                "player and target club.\n\n"
                "Required JSON schema:\n"
                f"{stable_json(AI_INTERPRETATION_SCHEMA)}\n\n"
                "Context:\n"
                f"{stable_json(prompt_payload)}"
            ),
        },
    ]


def analyze_transfer_scenario_with_ai(player_id, target_club, db):
    scenario_context = build_transfer_scenario_context(player_id, target_club, db)

    if not scenario_context:
        return None

    if scenario_context.get("error") == "Target club not found":
        return {"error": "Target club not found"}

    ai_transfer_context = build_compact_ai_context(scenario_context)
    context_hash = build_context_hash(ai_transfer_context)
    cached_analysis = get_cached_transfer_analysis(context_hash, db)

    if cached_analysis:
        return cached_analysis

    logger.info(
        "OpenAI provider is not enabled. Using deterministic transfer scenario fallback."
    )
    return fallback_from_context(
        scenario_context,
        "OpenAI provider is not enabled. Returned deterministic analysis.",
        context_hash,
    )
