import re
import unicodedata
from collections import Counter, defaultdict

from app.database import SessionLocal
from app.models.club_db import ClubDB
from app.models.player_advanced_stats_db import PlayerAdvancedStatsDB
from app.models.player_db import PlayerDB
from app.models.player_transfer_db import PlayerTransferDB
from app.models.player_valuation_db import PlayerValuationDB
from app.utils.league_names import formatLeagueName


ELITE_LEAGUES = {
    "Premier League",
    "LaLiga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
}


def normalize_text(value):
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(value).strip().lower())
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def clean_value(value):
    if isinstance(value, str):
        value = value.strip()

        if value in {"", "-"}:
            return None

    return value


def league_priority(club):
    return 1 if formatLeagueName(club.league) in ELITE_LEAGUES else 0


def get_age_bucket(age):
    if age is None:
        return "unknown"
    if age <= 22:
        return "18-22"
    if age <= 27:
        return "23-27"
    if age <= 31:
        return "28-31"

    return "32+"


def resolve_club(db, club_name):
    normalized_target = normalize_text(club_name)

    if not normalized_target:
        return None

    clubs = db.query(ClubDB).all()

    exact_matches = []

    for club in clubs:
        normalized_name = normalize_text(club.name)
        normalized_code = normalize_text(club.club_code)

        if normalized_name and normalized_name == normalized_target:
            exact_matches.append(club)
        elif normalized_code and normalized_code == normalized_target:
            exact_matches.append(club)

    if exact_matches:
        return exact_matches[0]

    contains_matches = []

    for club in clubs:
        normalized_name = normalize_text(club.name)

        if not normalized_name:
            continue

        if normalized_target in normalized_name or normalized_name in normalized_target:
            contains_matches.append(club)

    if contains_matches:
        return sorted(
            contains_matches,
            key=lambda club: (
                -league_priority(club),
                -(club.total_market_value or 0),
                -(club.squad_size or 0),
                len(club.name or ""),
            ),
        )[0]

    return None


def resolve_players_for_club(db, club, club_name):
    if club:
        players = (
            db.query(PlayerDB)
            .filter(PlayerDB.current_club_id == club.club_id)
            .order_by(PlayerDB.market_value_m.desc().nullslast(), PlayerDB.name.asc())
            .all()
        )

        if players:
            return players

    normalized_target = normalize_text(club.name if club else club_name)
    players = db.query(PlayerDB).all()

    matched_players = []

    for player in players:
        normalized_player_club = normalize_text(player.club)

        if not normalized_target or not normalized_player_club:
            continue

        if (
            normalized_player_club == normalized_target
            or normalized_target in normalized_player_club
            or normalized_player_club in normalized_target
        ):
            matched_players.append(player)

    return sorted(
        matched_players,
        key=lambda player: (
            player.market_value_m is None,
            -(player.market_value_m or 0),
            player.name or "",
        ),
    )


def normalize_context(value):
    if isinstance(value, dict):
        return {key: normalize_context(item) for key, item in value.items()}

    if isinstance(value, list):
        return [normalize_context(item) for item in value]

    return clean_value(value)


def build_club_context(club_name, db=None):
    owns_session = db is None
    db = db or SessionLocal()

    try:
        club = resolve_club(db, club_name)
        players = resolve_players_for_club(db, club, club_name)

        if not club and not players:
            return None

        market_values = [
            player.market_value_m
            for player in players
            if player.market_value_m is not None
        ]
        ages = [player.age for player in players if player.age is not None and player.age > 0]
        if market_values:
            total_market_value = sum(market_values)
        elif club:
            total_market_value = club.total_market_value
        else:
            total_market_value = None
        average_age = round(sum(ages) / len(ages), 1) if ages else None
        average_market_value = (
            round(total_market_value / len(market_values), 2)
            if total_market_value is not None and market_values
            else None
        )
        players_by_position = defaultdict(list)
        nationality_distribution = Counter(
            player.nationality for player in players if player.nationality
        )
        age_distribution = Counter(get_age_bucket(player.age) for player in players)

        for player in players:
            position = player.position or "Unknown"
            players_by_position[position].append(
                {
                    "id": player.id,
                    "name": player.name,
                    "age": player.age,
                    "nationality": player.nationality,
                    "position": player.position,
                    "club": player.club,
                    "league": formatLeagueName(player.league),
                    "market_value_m": player.market_value_m,
                    "image_url": player.image_url,
                }
            )

        context = {
            "club_name": club.name if club else club_name,
            "league": formatLeagueName(club.league if club else players[0].league if players else None),
            "country": club.country if club else None,
            "squad_count": len(players) if players else club.squad_size if club else None,
            "average_age": average_age if average_age is not None else club.average_age if club else None,
            "total_market_value": total_market_value,
            "average_market_value": average_market_value,
            "top_players": [
                {
                    "id": player.id,
                    "name": player.name,
                    "position": player.position,
                    "age": player.age,
                    "nationality": player.nationality,
                    "market_value_m": player.market_value_m,
                    "image_url": player.image_url,
                }
                for player in players[:8]
            ],
            "nationality_distribution": dict(nationality_distribution),
            "age_distribution": dict(age_distribution),
            "position_distribution": {
                position: len(position_players)
                for position, position_players in sorted(players_by_position.items())
            },
            "current_players_by_position": dict(players_by_position),
        }

        return normalize_context(context)
    finally:
        if owns_session:
            db.close()
