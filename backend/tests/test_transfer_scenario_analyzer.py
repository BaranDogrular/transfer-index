import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

import app.main  # noqa: F401 - register all SQLAlchemy models for route imports
from app.api.routes import validate_transfer_target_club
from app.services.transfer_scenario_analyzer import (
    SUB_SCORE_WEIGHTS,
    calculate_transfer_fit_score,
    calculate_weighted_fit_score,
    grade_from_score,
    score_advanced_stats_subscore,
    score_age_profile_subscore,
    score_financial_fit_subscore,
)


def player_context(position, age=25, market_value=30, advanced_stats=None):
    return {
        "profile": {
            "name": "Test Player",
            "position": position,
            "age": age,
            "nationality": "England",
            "league": "Premier League",
        },
        "club": {"league": "Premier League", "country": "England"},
        "market": {"current_market_value": market_value},
        "contract": {"contract_years_left": 2},
        "performance_24_25": {
            "matches": 32,
            "starts": 28,
            "minutes": 2500,
            "goals": 12,
            "assists": 8,
            "goals_per_90": 0.43,
            "assists_per_90": 0.29,
        },
        "advanced_stats_24_25": advanced_stats or {},
        "national_team": {"international_caps": 12},
        "risk_snapshot": {"injury_days": 10},
        "transfer_history": [],
    }


def club_context():
    position_depth = {
        "Centre-Forward": 1,
        "Central Midfield": 4,
        "Centre-Back": 4,
    }
    return {
        "club_name": "Target FC",
        "league": "Premier League",
        "country": "England",
        "average_age": 26,
        "average_market_value": 20,
        "total_market_value": 500,
        "financial_profile": {"median_player_value": 18},
        "position_depth": position_depth,
        "position_distribution": position_depth,
        "nationality_distribution": {"England": 8, "France": 5},
        "club_intelligence": {
            "club_level": "top",
            "average_age": 26,
            "position_depth": position_depth,
            "needs": ["ST"],
            "transfer_policy": "prime_players",
        },
    }


class TransferScenarioAnalyzerTests(unittest.TestCase):
    def test_weights_match_product_spec_and_normalize_missing_scores(self):
        self.assertAlmostEqual(sum(SUB_SCORE_WEIGHTS.values()), 1.0)
        self.assertEqual(SUB_SCORE_WEIGHTS["player_quality_score"], 0.20)
        self.assertEqual(SUB_SCORE_WEIGHTS["transfer_risk_score"], 0.02)

        score, missing = calculate_weighted_fit_score(
            {"player_quality_score": 80}
        )
        self.assertEqual(score, 80)
        self.assertIn("advanced_stats_score", missing)

    def test_completely_missing_data_stays_null(self):
        empty_player = {
            "profile": {},
            "club": {},
            "market": {},
            "contract": {},
            "performance_24_25": {},
            "advanced_stats_24_25": {},
            "national_team": {},
            "risk_snapshot": {},
            "transfer_history": [],
        }
        result = calculate_transfer_fit_score(empty_player, {})

        self.assertIsNone(result["fit_score"])
        self.assertIsNone(result["grade"])
        self.assertTrue(all(value is None for value in result["sub_scores"].values()))

    def test_position_aware_striker_midfielder_and_defender_profiles(self):
        striker = player_context(
            "Centre-Forward",
            advanced_stats={
                "xg": 16,
                "npxg": 14,
                "shots": 90,
                "shots_on_target": 40,
            },
        )
        midfielder = player_context(
            "Central Midfield",
            advanced_stats={
                "progressive_passes": 190,
                "xa": 7,
                "key_passes": 60,
                "shot_creating_actions": 85,
                "goal_creating_actions": 12,
                "passes_into_final_third": 145,
            },
        )
        defender = player_context(
            "Centre-Back",
            advanced_stats={
                "interceptions": 62,
                "tackles": 70,
                "blocks": 60,
                "aerials_won": 82,
                "progressive_passes": 160,
            },
        )

        self.assertGreaterEqual(score_advanced_stats_subscore(striker), 80)
        self.assertGreaterEqual(score_advanced_stats_subscore(midfielder), 80)
        self.assertGreaterEqual(score_advanced_stats_subscore(defender), 80)

    def test_winger_defensive_midfielder_full_back_and_goalkeeper_metrics(self):
        cases = [
            player_context(
                "Right Winger",
                advanced_stats={
                    "xa": 7,
                    "progressive_carries": 105,
                    "key_passes": 60,
                    "shot_creating_actions": 85,
                    "goal_creating_actions": 12,
                },
            ),
            player_context(
                "Defensive Midfield",
                advanced_stats={
                    "tackles": 80,
                    "interceptions": 62,
                    "progressive_passes": 175,
                    "blocks": 58,
                },
            ),
            player_context(
                "Right-Back",
                advanced_stats={
                    "tackles": 80,
                    "interceptions": 55,
                    "progressive_carries": 95,
                    "progressive_passes": 165,
                    "xa": 7,
                    "key_passes": 55,
                },
            ),
            player_context(
                "Goalkeeper",
                advanced_stats={
                    "clean_sheets": 14,
                    "saves": 100,
                    "save_percentage": 74,
                },
            ),
        ]

        for context in cases:
            with self.subTest(position=context["profile"]["position"]):
                score = score_advanced_stats_subscore(context)
                self.assertIsNotNone(score)
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)

    def test_young_and_expensive_profiles_use_real_comparisons(self):
        young_player = player_context("Right Winger", age=20, market_value=20)
        expensive_player = player_context("Centre-Forward", market_value=120)

        self.assertGreaterEqual(
            score_age_profile_subscore(young_player, club_context()),
            60,
        )
        self.assertLess(
            score_financial_fit_subscore(expensive_player, club_context()),
            55,
        )

    def test_grade_boundaries(self):
        expected = {
            85: "Elite Fit",
            84: "Strong Fit",
            70: "Strong Fit",
            69: "Moderate Fit",
            55: "Moderate Fit",
            54: "Risky Fit",
            40: "Risky Fit",
            39: "Poor Fit",
        }

        for score, grade in expected.items():
            with self.subTest(score=score):
                self.assertEqual(grade_from_score(score), grade)

    @patch("app.api.routes.resolve_club")
    @patch("app.api.routes.get_player_club")
    def test_current_club_is_rejected(self, get_player_club, resolve_club):
        player = SimpleNamespace(id=1, club="Current FC")
        current_club = SimpleNamespace(
            club_id=10,
            name="Current FC",
            club_code="CFC",
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = player
        get_player_club.return_value = current_club
        resolve_club.return_value = current_club

        with self.assertRaises(HTTPException) as raised:
            validate_transfer_target_club(db, 1, " current fc ")

        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
