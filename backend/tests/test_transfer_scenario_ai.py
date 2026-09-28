import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import app.main  # noqa: F401 - register all SQLAlchemy models
from app.models.transfer_scenario_analysis_db import TransferScenarioAnalysisDB
from app.services.transfer_scenario_ai import (
    CACHE_TTL_DAYS,
    analyze_transfer_scenario_with_ai,
    build_compact_ai_context,
    build_context_hash,
    get_cached_transfer_analysis,
    save_transfer_analysis_cache,
    stable_json,
)


def scenario_context():
    return {
        "player_context": {
            "profile": {
                "name": "Example Striker",
                "age": 24,
                "position": "Centre-Forward",
                "club": "Current FC",
            },
            "club": {"current_club": "Current FC"},
            "market": {
                "current_market_value": 50,
                "market_value_history": [{"date": "old", "value": 1}],
            },
            "contract": {"contract_years_left": 2},
            "performance_24_25": {
                "matches": 30,
                "starts": 25,
                "minutes": 2400,
                "goals": 18,
                "assists": 4,
            },
            "advanced_stats_24_25": {
                "xg": 16,
                "npxg": 14,
                "shots": 90,
                "shots_on_target": 40,
                "progressive_passes": 100,
            },
            "transfer_history": [{"from": "A", "to": "B"}],
        },
        "target_club_context": {
            "club": {
                "name": "Target FC",
                "league": "Premier League",
                "squad_count": 25,
                "average_age": 26,
            },
            "squad_profile": {
                "position_distribution": {"Centre-Forward": 2},
                "age_distribution": {"23-27": 15},
                "nationality_distribution": {"England": 8, "France": 5},
                "foot_distribution": {"right": 18, "left": 7},
            },
            "position_depth": {"Centre-Forward": 2},
            "total_market_value": 500,
            "average_market_value": 20,
            "financial_profile": {
                "median_player_value": 18,
                "top_player_value": 80,
                "value_concentration": 0.4,
            },
        },
        "scenario": {
            "source_club": "Current FC",
            "target_club": "Target FC",
        },
        "deterministic_analysis": {
            "fit_score": 74,
            "grade": "Strong Fit",
            "sub_scores": {"player_quality_score": 80},
            "strengths": ["Strong scoring and shooting profile."],
            "risks": ["Financially difficult move."],
            "missing_data": ["culture_fit_score"],
            "missing_data_notes": ["No verified culture-fit data."],
            "summary": "Deterministic summary.",
        },
        "scout_fit_layers": {},
    }


def cached_record(updated_at):
    return SimpleNamespace(
        context_hash="a" * 64,
        updated_at=updated_at,
        fit_score=74,
        grade="Strong Fit",
        sub_scores={"player_quality_score": 80, "culture_fit_score": None},
        strengths=[],
        risks=[],
        recommendation="Strong Fit",
        summary="Cached summary.",
        tactical_fit="",
        financial_risk="",
        contract_risk="",
        squad_fit="",
        culture_fit="",
        missing_data_notes=[],
        market_value_projection="",
    )


class TransferScenarioAIInfrastructureTests(unittest.TestCase):
    def test_compact_context_contains_only_required_sections(self):
        context = build_compact_ai_context(scenario_context())
        serialized = stable_json(context)

        self.assertEqual(
            set(context),
            {"player", "performance", "target_club", "analysis"},
        )
        self.assertNotIn("market_value_history", serialized)
        self.assertNotIn("transfer_history", serialized)
        self.assertEqual(
            set(context["performance"]),
            {
                "matches",
                "starts",
                "minutes",
                "goals",
                "xg",
                "npxg",
                "shots",
                "shots_on_target",
            },
        )

    def test_stable_json_and_hash_are_deterministic_and_data_sensitive(self):
        first = build_compact_ai_context(scenario_context())
        reordered = {key: first[key] for key in reversed(first)}

        self.assertEqual(stable_json(first), stable_json(reordered))
        self.assertEqual(build_context_hash(first), build_context_hash(reordered))

        changed = build_compact_ai_context(scenario_context())
        changed["analysis"]["fit_score"] = 75
        self.assertNotEqual(build_context_hash(first), build_context_hash(changed))

    def test_cache_model_has_required_columns(self):
        columns = set(TransferScenarioAnalysisDB.__table__.columns.keys())
        required = {
            "player_id",
            "target_club",
            "context_hash",
            "fit_score",
            "grade",
            "sub_scores",
            "source",
            "created_at",
            "updated_at",
            "summary",
            "recommendation",
            "tactical_fit",
            "financial_risk",
            "contract_risk",
        }
        self.assertTrue(required.issubset(columns))

    def test_cache_lookup_enforces_seven_day_ttl(self):
        self.assertEqual(CACHE_TTL_DAYS, 7)
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = cached_record(
            datetime.now(UTC).replace(tzinfo=None) - timedelta(days=6)
        )
        self.assertIsNotNone(get_cached_transfer_analysis("a" * 64, db))

        db.query.return_value.filter.return_value.first.return_value = cached_record(
            datetime.now(UTC).replace(tzinfo=None) - timedelta(days=8)
        )
        self.assertIsNone(get_cached_transfer_analysis("a" * 64, db))

    def test_cache_storage_saves_ai_result(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        response = {
            "source": "openai",
            "fit_score": 74,
            "grade": "Strong Fit",
            "sub_scores": {"player_quality_score": 80},
            "strengths": ["Strength"],
            "risks": ["Risk"],
            "summary": "Summary",
        }

        saved = save_transfer_analysis_cache(
            1,
            "Target FC",
            "a" * 64,
            response,
            db,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        self.assertEqual(saved["source"], "cache")
        self.assertEqual(saved["fit_score"], 74)

    def test_fallback_is_not_cached(self):
        db = MagicMock()
        saved = save_transfer_analysis_cache(
            1,
            "Target FC",
            "a" * 64,
            {"source": "fallback", "fit_score": 74},
            db,
        )

        self.assertIsNone(saved)
        db.query.assert_not_called()
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @patch("app.services.transfer_scenario_ai.get_cached_transfer_analysis")
    @patch("app.services.transfer_scenario_ai.build_transfer_scenario_context")
    def test_cache_miss_returns_deterministic_fallback(
        self,
        build_scenario,
        get_cached,
    ):
        build_scenario.return_value = scenario_context()
        get_cached.return_value = None

        response = analyze_transfer_scenario_with_ai(1, "Target FC", MagicMock())

        self.assertEqual(response["source"], "fallback")
        self.assertEqual(response["fit_score"], 74)
        self.assertEqual(response["grade"], "Strong Fit")
        self.assertEqual(response["summary"], "Deterministic summary.")
        self.assertEqual(response["missing_data"], ["culture_fit_score"])


if __name__ == "__main__":
    unittest.main()
