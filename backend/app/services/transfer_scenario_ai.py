import json
import logging
from datetime import datetime, timedelta
from hashlib import sha256


from app.models.transfer_scenario_analysis_db import TransferScenarioAnalysisDB
from app.services.transfer_scenario_analyzer import (
    EXPECTED_AI_RESPONSE_SCHEMA,
    build_transfer_scenario_context,
)


CACHE_TTL_DAYS = 7
logger = logging.getLogger(__name__)


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


def normalize_ai_response(value):
    normalized = get_empty_ai_fields()
    normalized.update(
        {
            "fit_score": clamp_fit_score(value.get("fit_score")),
            "grade": normalize_string(value.get("grade")),
            "sub_scores": (
                value.get("sub_scores")
                if isinstance(value.get("sub_scores"), dict)
                else {}
            ),
            "strengths": normalize_list(value.get("strengths")),
            "risks": normalize_list(value.get("risks")),
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
    )


def build_context_hash(scenario_context):
    return sha256(stable_json(scenario_context).encode("utf-8")).hexdigest()


def is_cache_fresh(cached_analysis):
    if not cached_analysis or not cached_analysis.updated_at:
        return False

    return cached_analysis.updated_at >= datetime.utcnow() - timedelta(
        days=CACHE_TTL_DAYS
    )


def serialize_cached_analysis(cached_analysis):
    cached_response = get_empty_ai_fields()
    cached_response.update(
        {
            "source": "cache",
            "fit_score": cached_analysis.fit_score,
            "grade": cached_analysis.grade or "",
            "sub_scores": cached_analysis.sub_scores or {},
            "strengths": cached_analysis.strengths or [],
            "risks": cached_analysis.risks or [],
            "recommendation": cached_analysis.recommendation or "",
            "summary": cached_analysis.summary or "",
            "tactical_fit": cached_analysis.tactical_fit or "",
            "financial_risk": cached_analysis.financial_risk or "",
            "contract_risk": cached_analysis.contract_risk or "",
            "squad_fit": cached_analysis.squad_fit or "",
            "culture_fit": cached_analysis.culture_fit or "",
            "missing_data_notes": cached_analysis.missing_data_notes or [],
            "market_value_projection": cached_analysis.market_value_projection or "",
        }
    )
    return cached_response


def get_cached_transfer_analysis(db, context_hash):
    cached_analysis = (
        db.query(TransferScenarioAnalysisDB)
        .filter(TransferScenarioAnalysisDB.context_hash == context_hash)
        .first()
    )

    if not is_cache_fresh(cached_analysis):
        return None

    return serialize_cached_analysis(cached_analysis)


def save_transfer_analysis_cache(
    db,
    player_id,
    target_club,
    scenario_context,
    context_hash,
    ai_response,
):
    try:
        cached_analysis = (
            db.query(TransferScenarioAnalysisDB)
            .filter(TransferScenarioAnalysisDB.context_hash == context_hash)
            .first()
        )

        if not cached_analysis:
            cached_analysis = TransferScenarioAnalysisDB(
                player_id=player_id,
                target_club=scenario_context.get("scenario", {}).get("target_club")
                or target_club,
                context_hash=context_hash,
                created_at=datetime.utcnow(),
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
        cached_analysis.updated_at = datetime.utcnow()

        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Transfer scenario AI cache write failed.")


def fallback_from_context(scenario_context, reason):
    deterministic = scenario_context.get("deterministic_analysis") or {}
    scout_fit_layers = scenario_context.get("scout_fit_layers") or {}
    missing_data_notes = [
        item
        for item in deterministic.get("risks", [])
        if "missing verified data" in str(item).lower()
    ]
    fallback = get_empty_ai_fields()
    fallback.update(
        {
            "source": "fallback",
            "fit_score": deterministic.get("fit_score", 0),
            "grade": deterministic.get("grade", ""),
            "sub_scores": deterministic.get("sub_scores", {}),
            "strengths": deterministic.get("strengths", []),
            "risks": deterministic.get("risks", []),
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
            "missing_data_notes": missing_data_notes,
            "market_value_projection": "Not available in deterministic fallback.",
            "summary": reason,
            "recommendation": "Use deterministic analysis until AI analysis is available.",
        }
    )
    return fallback


def analyze_transfer_scenario_with_ai(player_id, target_club, db):
    scenario_context = build_transfer_scenario_context(player_id, target_club, db)

    if not scenario_context:
        return None

    if scenario_context.get("error") == "Target club not found":
        return {"error": "Target club not found"}

    context_hash = build_context_hash(scenario_context)
    cached_analysis = get_cached_transfer_analysis(db, context_hash)

    if cached_analysis:
        return cached_analysis

    return fallback_from_context(
        scenario_context,
        "OpenAI integration is not enabled yet. Returned deterministic analysis.",
    )
