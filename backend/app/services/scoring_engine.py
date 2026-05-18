class TransferIndexEngine:
    def calculate(self, player, team):
        performance_score = self._performance_score(player)
        tactical_fit_score = self._tactical_fit_score(player, team)
        financial_score = self._financial_score(player, team)
        risk_score = self._risk_score(player)

        transfer_index = (
            performance_score * 0.35
            + tactical_fit_score * 0.25
            + financial_score * 0.20
            + risk_score * 0.20
        )

        return {
            "player": player.name,
            "target_team": team.team_name,
            "transfer_index": round(transfer_index, 2),
            "scores": {
                "performance": performance_score,
                "tactical_fit": tactical_fit_score,
                "financial": financial_score,
                "risk": risk_score,
            },
            "risk_level": self._risk_level(transfer_index),
        }

    def _performance_score(self, player):
        if player.matches == 0:
            return 0

        goal_contribution = (player.goals + player.assists) / player.matches
        expected_contribution = (player.xg + player.xa) / player.matches

        score = 0
        score += min(goal_contribution * 100, 50)
        score += min(expected_contribution * 100, 50)

        return round(min(score, 100), 2)

    def _tactical_fit_score(self, player, team):
        score = 50

        if player.position.upper() == team.needed_position.upper():
            score += 35

        if team.preferred_age_min <= player.age <= team.preferred_age_max:
            score += 15
        elif player.age <= 30:
            score += 5
        else:
            score -= 10

        return round(max(0, min(score, 100)), 2)

    def _financial_score(self, player, team):
        score = 100

        if player.market_value_m > team.max_market_value_m:
            score -= 20

        if player.salary_m > team.max_salary_m:
            score -= 20

        if player.contract_years_left > 2:
            score -= 10

        return round(max(0, min(score, 100)), 2)

    def _risk_score(self, player):
        score = 100

        if player.injury_days > 30:
            score -= 20

        if player.injury_days > 90:
            score -= 25

        if player.age > 30:
            score -= 15

        if player.matches < 15:
            score -= 15

        return round(max(0, min(score, 100)), 2)

    def _risk_level(self, transfer_index):
        if transfer_index >= 80:
            return "Düşük risk / yüksek uygunluk"
        if transfer_index >= 65:
            return "Orta risk / izlenebilir transfer"
        if transfer_index >= 50:
            return "Yüksek risk / dikkatli olunmalı"
        return "Çok yüksek risk / önerilmez"