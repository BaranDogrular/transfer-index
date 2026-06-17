import json
import logging
import os
import re
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from app.models.transfer_scenario_analysis_db import TransferScenarioAnalysisDB
from app.services.transfer_scenario_analyzer import (
    EXPECTED_AI_RESPONSE_SCHEMA,
    build_transfer_scenario_context,
)


load_dotenv(Path(__file__).resolve().parents[2] / ".env")

DEFAULT_MODEL = "gpt-4o-mini"
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


def strip_json_code_fence(value):
    text = str(value or "").strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return text


def normalize_ai_response(value):
    normalized = get_empty_ai_fields()
    normalized.update(
        {
            "fit_score": clamp_fit_score(value.get("fit_score")),
            "grade": normalize_string(value.get("grade")),
            "strengths": normalize_list(value.get("strengths")),
            "risks": normalize_list(value.get("risks")),
            "tactical_fit": normalize_string(value.get("tactical_fit")),
            "financial_risk": normalize_string(value.get("financial_risk")),
            "contract_risk": normalize_string(value.get("contract_risk")),
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
    context_payload = {
        "player_context": scenario_context.get("player_context"),
        "target_club_context": scenario_context.get("target_club_context"),
    }
    return sha256(stable_json(context_payload).encode("utf-8")).hexdigest()


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
            "strengths": cached_analysis.strengths or [],
            "risks": cached_analysis.risks or [],
            "tactical_fit": cached_analysis.tactical_fit or "",
            "financial_risk": cached_analysis.financial_risk or "",
            "contract_risk": cached_analysis.contract_risk or "",
            "market_value_projection": cached_analysis.market_value_projection or "",
            "summary": cached_analysis.summary or "",
            "recommendation": cached_analysis.recommendation or "",
        }
    )
    return cached_response


def upsert_cached_analysis(
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

        cached_analysis.source = "openai"
        cached_analysis.fit_score = ai_response.get("fit_score")
        cached_analysis.grade = ai_response.get("grade")
        cached_analysis.strengths = ai_response.get("strengths") or []
        cached_analysis.risks = ai_response.get("risks") or []
        cached_analysis.tactical_fit = ai_response.get("tactical_fit")
        cached_analysis.financial_risk = ai_response.get("financial_risk")
        cached_analysis.contract_risk = ai_response.get("contract_risk")
        cached_analysis.market_value_projection = ai_response.get(
            "market_value_projection"
        )
        cached_analysis.summary = ai_response.get("summary")
        cached_analysis.recommendation = ai_response.get("recommendation")
        cached_analysis.updated_at = datetime.utcnow()

        db.commit()
    except Exception:
        db.rollback()
        logger.warning("Transfer scenario AI cache write failed.")


def fallback_from_context(scenario_context, reason):
    deterministic = scenario_context.get("deterministic_analysis") or {}
    fallback = get_empty_ai_fields()
    fallback.update(
        {
            "source": "fallback",
            "fit_score": deterministic.get("fit_score", 0),
            "grade": deterministic.get("grade", ""),
            "strengths": deterministic.get("strengths", []),
            "risks": deterministic.get("risks", []),
            "tactical_fit": "Not available in deterministic fallback.",
            "financial_risk": "See deterministic risks.",
            "contract_risk": "See deterministic risks.",
            "market_value_projection": "Not available in deterministic fallback.",
            "summary": reason,
            "recommendation": "Use deterministic analysis until AI analysis is available.",
        }
    )
    return fallback


def build_ai_messages(scenario_context):
    return [
        {
            "role": "system",
            "content": (
                "You are a professional football scout and transfer analyst. "
                "Use only the structured data provided by the user. Do not invent facts. "
                "If data is missing, say it is missing. Return only valid JSON matching "
                "the requested schema."
            ),
        },
        {
            "role": "user",
            "content": (
                "Analyze this transfer fit for the player and target club. "
                "Keep the scout language professional and concise.\n\n"
                "Required JSON schema:\n"
                f"{json.dumps(EXPECTED_AI_RESPONSE_SCHEMA, ensure_ascii=False)}\n\n"
                "Scenario context JSON:\n"
                f"{json.dumps(scenario_context, ensure_ascii=False, default=str)}"
            ),
        },
    ]


def analyze_transfer_scenario_with_ai(player_id, target_club, db):
    scenario_context = build_transfer_scenario_context(player_id, target_club, db)

    if not scenario_context:
        return None

    if scenario_context.get("error") == "Target club not found":
        return {"error": "Target club not found"}

    context_hash = build_context_hash(scenario_context)
    cached_analysis = (
        db.query(TransferScenarioAnalysisDB)
        .filter(TransferScenarioAnalysisDB.context_hash == context_hash)
        .first()
    )

    if is_cache_fresh(cached_analysis):
        return serialize_cached_analysis(cached_analysis)

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or not api_key.strip():
        logger.warning(
            "OPENAI_API_KEY is not configured; using deterministic fallback "
            "for transfer scenario AI analysis."
        )
        return fallback_from_context(
            scenario_context,
            "OpenAI API key missing. Returned deterministic analysis.",
        )

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=30)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            messages=build_ai_messages(scenario_context),
            temperature=0.2,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content
        parsed_response = json.loads(strip_json_code_fence(raw_content))
        ai_response = normalize_ai_response(parsed_response)
        ai_response["source"] = "openai"
        upsert_cached_analysis(
            db,
            player_id,
            target_club,
            scenario_context,
            context_hash,
            ai_response,
        )
        return ai_response
    except Exception:
        logger.warning(
            "OpenAI transfer scenario analysis failed; using deterministic fallback."
        )
        return fallback_from_context(
            scenario_context,
            "OpenAI analysis unavailable. Returned deterministic analysis.",
        )
