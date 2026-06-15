class TransferIndexEngine:

    def calculate(self, player, team):
        performance_score = self._performance_score(player)
        tactical_fit_score = self._tactical_fit_score(player, team)
        financial_score = self._financial_score(player, team)
        risk_score = self._risk_score(player)

        transfer_index = (
            performance_score * 0.40
            + tactical_fit_score * 0.25
            + financial_score * 0.20
            + risk_score * 0.15
        )

        transfer_index = round(
            max(0, min(transfer_index, 100)),
            2
        )

        return {
            "player": player.name,
            "target_team": team.team_name,
            "transfer_index": transfer_index,
            "scores": {
                "performance": performance_score,
                "tactical_fit": tactical_fit_score,
                "financial": financial_score,
                "risk": risk_score,
            },
            "risk_level": self._risk_level(transfer_index),
            "recommendation": self._recommendation(
                transfer_index
            ),
        }

    # PERFORMANCE
    def _performance_score(self, player):

        if player.matches <= 0:
            return 0

        score = 0

        goal_rate = player.goals / player.matches
        assist_rate = player.assists / player.matches

        xg_rate = player.xg / player.matches
        xa_rate = player.xa / player.matches

        # POSITION WEIGHTING
        attacking_positions = [
            "ST",
            "CF",
            "LW",
            "RW",
            "CAM"
        ]

        midfield_positions = [
            "CM",
            "CDM",
            "LM",
            "RM"
        ]

        defensive_positions = [
            "CB",
            "LB",
            "RB",
            "LWB",
            "RWB"
        ]

        position = player.position.upper()

        # ATTACKERS
        if position in attacking_positions:
            score += min(goal_rate * 120, 45)
            score += min(assist_rate * 80, 20)
            score += min(xg_rate * 100, 20)
            score += min(xa_rate * 80, 15)

        # MIDFIELDERS
        elif position in midfield_positions:
            score += min(goal_rate * 70, 20)
            score += min(assist_rate * 100, 30)
            score += min(xg_rate * 60, 20)
            score += min(xa_rate * 100, 30)

        # DEFENDERS
        elif position in defensive_positions:
            score += min(goal_rate * 40, 10)
            score += min(assist_rate * 60, 20)
            score += min(xg_rate * 40, 20)
            score += min(xa_rate * 60, 20)
            score += 30

        # DEFAULT
        else:
            score += min(goal_rate * 100, 30)
            score += min(assist_rate * 100, 30)
            score += min(xg_rate * 100, 20)
            score += min(xa_rate * 100, 20)

        return round(max(0, min(score, 100)), 2)

    # TACTICAL FIT
    def _tactical_fit_score(self, player, team):

        score = 40

        # POSITION MATCH
        if player.position.upper() == team.needed_position.upper():
            score += 40

        # AGE FIT
        if (
            team.preferred_age_min
            <= player.age
            <= team.preferred_age_max
        ):
            score += 20

        elif player.age <= 30:
            score += 10

        else:
            score -= 10

        return round(max(0, min(score, 100)), 2)

    # FINANCIAL
    def _financial_score(self, player, team):

        score = 100

        # MARKET VALUE
        market_ratio = (
            player.market_value_m
            / team.max_market_value_m
        )

        if market_ratio > 1:
            score -= min(
                (market_ratio - 1) * 35,
                40
            )

        # SALARY
        salary_ratio = (
            player.salary_m
            / team.max_salary_m
        )

        if salary_ratio > 1:
            score -= min(
                (salary_ratio - 1) * 35,
                40
            )

        # CONTRACT
        if player.contract_years_left >= 4:
            score -= 15

        elif player.contract_years_left >= 2:
            score -= 8

        return round(max(0, min(score, 100)), 2)

    # RISK
    def _risk_score(self, player):

        score = 100

        # INJURY
        if player.injury_days > 180:
            score -= 45

        elif player.injury_days > 90:
            score -= 30

        elif player.injury_days > 30:
            score -= 15

        # AGE
        if player.age >= 33:
            score -= 25

        elif player.age >= 30:
            score -= 10

        # MATCH FITNESS
        if player.matches < 10:
            score -= 25

        elif player.matches < 20:
            score -= 10

        return round(max(0, min(score, 100)), 2)

    # RISK LEVEL
    def _risk_level(self, transfer_index):

        if transfer_index >= 85:
            return "Elite transfer target"

        if transfer_index >= 75:
            return "Strong transfer candidate"

        if transfer_index >= 60:
            return "Moderate risk / monitor closely"

        if transfer_index >= 45:
            return "High risk transfer"

        return "Very high risk / not recommended"

    # FINAL RECOMMENDATION
    def _recommendation(self, transfer_index):

        if transfer_index >= 80:
            return "Transfer önerilir"

        if transfer_index >= 65:
            return "Dikkatli izlenmeli"

        return "Transfer önerilmez"