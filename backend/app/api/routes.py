import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.transfer import (
    TransferRequest,
    PlayerData,
    TeamNeed,
)
from app.models.transfer_scenario import TransferScenarioRequest
from app.models.player_db import PlayerDB
from app.models.player_advanced_stats_db import PlayerAdvancedStatsDB
from app.services.scoring_engine import TransferIndexEngine
from app.services.ai_scout import AIScoutService
from app.models.player_valuation_db import PlayerValuationDB
from app.models.player_transfer_db import PlayerTransferDB
from app.models.club_db import ClubDB
from app.schemas.player_valuation import PlayerValuationResponse, PlayerValuationItem
from app.services.club_context import build_club_context, resolve_club
from app.services.player_context import build_player_context
from app.services.player_score import analyze_player_score
from app.services.transfer_scenario_analyzer import build_transfer_scenario_context
from app.services.transfer_scenario_ai import analyze_transfer_scenario_with_ai
from app.utils.league_names import formatLeagueName


router = APIRouter()

engine = TransferIndexEngine()
ai_scout = AIScoutService()

ACCENT_TRANSLATION = {
    "á": "a",
    "à": "a",
    "â": "a",
    "ä": "a",
    "ã": "a",
    "å": "a",
    "ā": "a",
    "ç": "c",
    "ć": "c",
    "č": "c",
    "é": "e",
    "è": "e",
    "ê": "e",
    "ë": "e",
    "ē": "e",
    "ė": "e",
    "ę": "e",
    "ğ": "g",
    "í": "i",
    "ì": "i",
    "î": "i",
    "ï": "i",
    "ı": "i",
    "ñ": "n",
    "ó": "o",
    "ò": "o",
    "ô": "o",
    "ö": "o",
    "õ": "o",
    "ø": "o",
    "ō": "o",
    "ś": "s",
    "ş": "s",
    "š": "s",
    "ú": "u",
    "ù": "u",
    "û": "u",
    "ü": "u",
    "ū": "u",
    "ý": "y",
    "ÿ": "y",
    "ž": "z",
    "ź": "z",
    "ż": "z",
}
ACCENT_FROM = "".join(ACCENT_TRANSLATION.keys())
ACCENT_TO = "".join(ACCENT_TRANSLATION.values())


def normalize_search_query(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def normalized_column(column):
    return func.translate(
        func.lower(func.coalesce(column, "")),
        ACCENT_FROM,
        ACCENT_TO,
    )


def normalize_club_name_for_compare(value):
    normalized = normalize_search_query(str(value or ""))
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    ignored_tokens = {"fc", "cf", "afc", "club", "football", "futbol", "the"}
    tokens = [
        token
        for token in normalized.split()
        if token and token not in ignored_tokens
    ]
    return " ".join(tokens).strip()


def validate_transfer_target_club(db: Session, player_id: int, target_club: str):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        return None

    current_club = get_player_club(db, player)
    target_club_record = resolve_club(db, target_club)

    if (
        current_club
        and target_club_record
        and current_club.club_id == target_club_record.club_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Player is already at this club.",
        )

    current_names = [
        player.club,
        current_club.name if current_club else None,
        current_club.club_code if current_club else None,
    ]
    target_names = [
        target_club,
        target_club_record.name if target_club_record else None,
        target_club_record.club_code if target_club_record else None,
    ]
    current_normalized = {
        normalize_club_name_for_compare(name)
        for name in current_names
        if normalize_club_name_for_compare(name)
    }
    target_normalized = {
        normalize_club_name_for_compare(name)
        for name in target_names
        if normalize_club_name_for_compare(name)
    }

    if current_normalized.intersection(target_normalized):
        raise HTTPException(
            status_code=400,
            detail="Player is already at this club.",
        )

    return player


def get_club_by_id_map(db: Session, club_ids):
    clean_ids = {
        club_id
        for club_id in club_ids
        if club_id is not None
    }

    if not clean_ids:
        return {}

    clubs = db.query(ClubDB).filter(ClubDB.club_id.in_(clean_ids)).all()
    return {club.club_id: club for club in clubs}


def get_player_club(db: Session, player: PlayerDB):
    if player.current_club_id is None:
        return None

    return (
        db.query(ClubDB)
        .filter(ClubDB.club_id == player.current_club_id)
        .first()
    )


def serialize_search_player(player, club=None):
    return {
        "id": player.id,
        "name": player.name,
        "club": player.club,
        "club_id": player.current_club_id,
        "club_logo_url": club.logo_url if club else None,
        "league": formatLeagueName(player.league),
        "position": player.position,
        "market_value_m": player.market_value_m,
        "image_url": player.image_url,
    }


def serialize_player_detail(player, club=None):
    return {
        "id": player.id,
        "transfermarkt_id": player.transfermarkt_id,
        "name": player.name,
        "age": player.age,
        "position": player.position,
        "club": player.club,
        "current_club_id": player.current_club_id,
        "club_id": player.current_club_id,
        "club_logo_url": club.logo_url if club else None,
        "date_of_birth": player.date_of_birth,
        "nationality": player.nationality,
        "country_flag_url": player.country_flag_url,
        "national_team_id": player.national_team_id,
        "national_team_name": player.national_team_name,
        "national_team_flag_url": player.national_team_flag_url,
        "international_caps": player.international_caps,
        "international_goals": player.international_goals,
        "preferred_foot": player.preferred_foot,
        "height_cm": player.height_cm,
        "weight_kg": player.weight_kg,
        "league": formatLeagueName(player.league),
        "image_url": player.image_url,
        "goals": player.goals,
        "assists": player.assists,
        "matches": player.matches,
        "minutes_played": player.minutes_played,
        "yellow_cards": player.yellow_cards,
        "red_cards": player.red_cards,
        "goals_per_90": player.goals_per_90,
        "assists_per_90": player.assists_per_90,
        "goal_contributions": player.goal_contributions,
        "goal_contributions_per_90": player.goal_contributions_per_90,
        "minutes_per_goal": player.minutes_per_goal,
        "xg": player.xg,
        "xa": player.xa,
        "market_value_m": player.market_value_m,
        "salary_m": player.salary_m,
        "injury_days": player.injury_days,
        "contract_years_left": player.contract_years_left,
        "contract_expiration_date": player.contract_expiration_date,
    }


def get_clean_distinct_values(db: Session, column):
    rows = (
        db.query(column)
        .filter(column.isnot(None))
        .filter(func.trim(column) != "")
        .filter(column != "-")
        .filter(column != "Unknown")
        .distinct()
        .order_by(column.asc())
        .all()
    )
    return [row[0] for row in rows if row[0]]


def serialize_advanced_stats(player_id, stats=None, season="2024/25"):
    return {
        "player_id": player_id,
        "season": stats.season if stats else season,
        "source": stats.source if stats else "fbref",
        "matches": stats.matches if stats else None,
        "starts": stats.starts if stats else None,
        "minutes": stats.minutes if stats else None,
        "goals": stats.goals if stats else None,
        "assists": stats.assists if stats else None,
        "xg": stats.xg if stats else None,
        "xa": stats.xa if stats else None,
        "npxg": stats.npxg if stats else None,
        "shots": stats.shots if stats else None,
        "shots_on_target": stats.shots_on_target if stats else None,
        "key_passes": stats.key_passes if stats else None,
        "progressive_passes": stats.progressive_passes if stats else None,
        "progressive_carries": stats.progressive_carries if stats else None,
        "passes_into_final_third": stats.passes_into_final_third if stats else None,
        "passes_into_penalty_area": stats.passes_into_penalty_area if stats else None,
        "shot_creating_actions": stats.shot_creating_actions if stats else None,
        "goal_creating_actions": stats.goal_creating_actions if stats else None,
        "tackles": stats.tackles if stats else None,
        "interceptions": stats.interceptions if stats else None,
        "blocks": stats.blocks if stats else None,
        "aerials_won": stats.aerials_won if stats else None,
        "aerials_lost": stats.aerials_lost if stats else None,
        "yellow_cards": stats.yellow_cards if stats else None,
        "red_cards": stats.red_cards if stats else None,
        "clean_sheets": stats.clean_sheets if stats else None,
        "saves": stats.saves if stats else None,
        "save_percentage": stats.save_percentage if stats else None,
        "goals_against": stats.goals_against if stats else None,
        "pass_completion": stats.pass_completion if stats else None,
    }



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def root():
    return {"message": "Transfer Index API running"}


@router.post("/transfer-score")
def calculate_transfer_score(request: TransferRequest):
    return engine.calculate(request.player, request.team)


@router.post("/transfer-scenarios/analyze")
def analyze_transfer_scenario_endpoint(
    request: TransferScenarioRequest,
    db: Session = Depends(get_db),
):
    target_club = request.target_club.strip()

    if not target_club:
        raise HTTPException(status_code=400, detail="Target club is required")

    player = validate_transfer_target_club(db, request.player_id, target_club)

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    result = build_transfer_scenario_context(
        request.player_id,
        target_club,
        db,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Player not found")

    if result.get("error") == "Target club not found":
        raise HTTPException(status_code=404, detail="Target club not found")

    return result


@router.post("/transfer-scenarios/ai-analyze")
def prepare_transfer_scenario_ai_analyze(
    request: TransferScenarioRequest,
    db: Session = Depends(get_db),
):
    target_club = request.target_club.strip()

    if not target_club:
        raise HTTPException(status_code=400, detail="Target club is required")

    player = validate_transfer_target_club(db, request.player_id, target_club)

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    result = analyze_transfer_scenario_with_ai(
        request.player_id,
        target_club,
        db,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Player not found")

    if result.get("error") == "Target club not found":
        raise HTTPException(status_code=404, detail="Target club not found")

    return result


@router.post("/players")
def create_player(
    player: PlayerData,
    db: Session = Depends(get_db),
):
    new_player = PlayerDB(**player.model_dump())

    db.add(new_player)
    db.commit()
    db.refresh(new_player)

    return {
        "success": True,
        "player": new_player,
    }


@router.get("/players/search")
def search_players(
    request: Request,
    q: str | None = None,
    position: str | None = None,
    league: str | None = None,
    nationality: str | None = None,
    club: str | None = None,
    preferred_foot: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    min_minutes: int | None = None,
    min_goals: int | None = None,
    min_assists: int | None = None,
    max_salary: float | None = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(PlayerDB)
    normalized_query = normalize_search_query(q) if q else ""

    if normalized_query:
        normalized_name = normalized_column(PlayerDB.name)
        normalized_club = normalized_column(PlayerDB.club)
        normalized_league = normalized_column(PlayerDB.league)
        contains_query = f"%{normalized_query}%"
        starts_query = f"{normalized_query}%"
        token_pattern = f"(^|[[:space:]]){re.escape(normalized_query)}"
        token_starts_query = normalized_name.op("~")(token_pattern)

        query = query.filter(
            or_(
                normalized_name == normalized_query,
                normalized_name.like(starts_query),
                token_starts_query,
                normalized_name.like(contains_query),
                normalized_club.like(contains_query),
                normalized_league.like(contains_query),
            )
        )

    if position:
        query = query.filter(PlayerDB.position.ilike(position))

    if league:
        query = query.filter(PlayerDB.league.ilike(f"%{league}%"))

    if nationality:
        query = query.filter(PlayerDB.nationality.ilike(f"%{nationality}%"))

    if club:
        query = query.filter(PlayerDB.club.ilike(f"%{club}%"))

    if preferred_foot:
        query = query.filter(PlayerDB.preferred_foot.ilike(preferred_foot))

    if min_age is not None:
        query = query.filter(PlayerDB.age >= min_age)

    if max_age is not None:
        query = query.filter(PlayerDB.age <= max_age)

    if min_value is not None:
        query = query.filter(PlayerDB.market_value_m >= min_value)

    if max_value is not None:
        query = query.filter(PlayerDB.market_value_m <= max_value)

    if min_minutes is not None:
        query = query.filter(PlayerDB.minutes_played >= min_minutes)

    if min_goals is not None:
        query = query.filter(PlayerDB.goals >= min_goals)

    if min_assists is not None:
        query = query.filter(PlayerDB.assists >= min_assists)

    if max_salary is not None:
        query = query.filter(PlayerDB.salary_m <= max_salary)

    total = query.count()

    page = max(page, 1)
    limit = min(max(limit, 1), 100)

    if normalized_query:
        rank_score = case(
            (normalized_name == normalized_query, 1000),
            (normalized_name.like(starts_query), 700),
            (token_starts_query, 690),
            (normalized_name.like(contains_query), 400),
            (normalized_club.like(contains_query), 200),
            (normalized_league.like(contains_query), 100),
            else_=0,
        )
        market_score = func.least(
            func.coalesce(PlayerDB.market_value_m, 0),
            200,
        )

        query = query.order_by(
            (rank_score + market_score).desc(),
            PlayerDB.market_value_m.desc().nullslast(),
            PlayerDB.name.asc(),
        )
    else:
        query = query.order_by(
            PlayerDB.market_value_m.desc().nullslast(),
            PlayerDB.name.asc(),
        )

    players = query.offset((page - 1) * limit).limit(limit).all()

    has_filters = any(
        value is not None
        for value in [
            position,
            league,
            nationality,
            club,
            preferred_foot,
            min_age,
            max_age,
            min_value,
            max_value,
            min_minutes,
            min_goals,
            min_assists,
            max_salary,
        ]
    )

    query_param_keys = set(request.query_params.keys())
    is_autocomplete_request = (
        q
        and not has_filters
        and page == 1
        and (limit <= 10 or query_param_keys == {"q"})
    )

    club_map = get_club_by_id_map(
        db,
        [player.current_club_id for player in players],
    )

    if is_autocomplete_request:
        return [
            serialize_search_player(player, club_map.get(player.current_club_id))
            for player in players[:10]
        ]

    return {
        "count": len(players),
        "total": total,
        "page": page,
        "limit": limit,
        "players": [
            serialize_player_detail(player, club_map.get(player.current_club_id))
            for player in players
        ],
    }


@router.get("/players/filter-options")
def get_player_filter_options(db: Session = Depends(get_db)):
    leagues = get_clean_distinct_values(db, PlayerDB.league)

    return {
        "positions": get_clean_distinct_values(db, PlayerDB.position),
        "nationalities": get_clean_distinct_values(db, PlayerDB.nationality),
        "clubs": get_clean_distinct_values(db, PlayerDB.club),
        "preferred_feet": get_clean_distinct_values(db, PlayerDB.preferred_foot),
        "leagues": [
            {
                "value": league,
                "label": formatLeagueName(league),
            }
            for league in leagues
        ],
    }


@router.get("/players")
def get_players(db: Session = Depends(get_db)):
    players = db.query(PlayerDB).all()
    club_map = get_club_by_id_map(
        db,
        [player.current_club_id for player in players],
    )

    return {
        "count": len(players),
        "players": [
            {
                **serialize_player_detail(
                    player,
                    club_map.get(player.current_club_id),
                ),
                "nationality": player.nationality,
            }
            for player in players
        ],
    }


@router.get("/clubs/search")
def search_clubs(
    q: str = "",
    limit: int = 10,
    db: Session = Depends(get_db),
):
    normalized_query = normalize_search_query(q) if q else ""

    if len(normalized_query) < 2:
        return []

    normalized_name = normalized_column(ClubDB.name)
    contains_query = f"%{normalized_query}%"
    starts_query = f"{normalized_query}%"
    elite_leagues = [
        "premier-league",
        "gb1",
        "laliga",
        "es1",
        "serie-a",
        "it1",
        "bundesliga",
        "l1",
        "ligue-1",
        "fr1",
    ]
    match_rank = case(
        (normalized_name == normalized_query, 0),
        (normalized_name.like(starts_query), 1),
        (normalized_name.like(contains_query), 2),
        else_=3,
    )
    league_rank = case((ClubDB.league.in_(elite_leagues), 0), else_=1)
    result_limit = max(1, min(limit, 10))
    clubs = (
        db.query(ClubDB)
        .filter(normalized_name.like(contains_query))
        .order_by(
            match_rank.asc(),
            league_rank.asc(),
            ClubDB.total_market_value.desc().nullslast(),
            ClubDB.squad_size.desc().nullslast(),
            func.length(ClubDB.name).asc(),
            ClubDB.name.asc(),
        )
        .limit(result_limit)
        .all()
    )

    return [
        {
            "club_id": club.club_id,
            "club_name": club.name,
            "league": formatLeagueName(club.league),
            "country": club.country,
            "logo_url": club.logo_url,
        }
        for club in clubs
    ]


@router.get("/clubs/{club_name}/context")
def get_club_ai_context(
    club_name: str,
    db: Session = Depends(get_db),
):
    context = build_club_context(club_name, db)

    if not context:
        raise HTTPException(status_code=404, detail="Club not found")

    return context


@router.get("/clubs/{club_id_or_name}")
def get_club(club_id_or_name: str, db: Session = Depends(get_db)):
    club = None

    if club_id_or_name.isdigit():
        club = (
            db.query(ClubDB)
            .filter(ClubDB.club_id == int(club_id_or_name))
            .first()
        )

    if not club:
        normalized_name = club_id_or_name.replace("-", " ").strip()
        club = (
            db.query(ClubDB)
            .filter(ClubDB.name.ilike(normalized_name))
            .first()
        )

    club_name = club.name if club else club_id_or_name.replace("-", " ").strip()

    players = (
        db.query(PlayerDB)
        .filter(PlayerDB.club.ilike(club_name))
        .order_by(PlayerDB.market_value_m.desc().nullslast(), PlayerDB.name.asc())
        .all()
    )

    if not club and not players:
        raise HTTPException(status_code=404, detail="Club not found")

    player_items = [
        {
            "id": player.id,
            "name": player.name,
            "position": player.position,
            "age": player.age,
            "market_value_m": player.market_value_m,
            "image_url": player.image_url,
            "club_id": player.current_club_id,
            "club_logo_url": None,
        }
        for player in players
    ]

    market_values = [
        player.market_value_m
        for player in players
        if player.market_value_m is not None
    ]
    ages = [player.age for player in players if player.age is not None and player.age > 0]
    total_market_value = sum(market_values) if market_values else None
    average_age = round(sum(ages) / len(ages), 1) if ages else None

    return {
        "club_id": club.club_id if club else None,
        "club_name": club_name,
        "country": club.country if club else None,
        "league": formatLeagueName(club.league) if club else "-",
        "logo_url": club.logo_url if club else None,
        "squad_count": len(players) if players else club.squad_size if club else 0,
        "average_age": average_age if average_age is not None else club.average_age if club else None,
        "total_market_value": total_market_value,
        "top_players_by_value": player_items[:5],
        "players": player_items,
    }


@router.get("/players/compare")
def compare_players(
    player1_id: int,
    player2_id: int,
    db: Session = Depends(get_db),
):
    player1 = db.query(PlayerDB).filter(PlayerDB.id == player1_id).first()
    player2 = db.query(PlayerDB).filter(PlayerDB.id == player2_id).first()

    if not player1 or not player2:
        raise HTTPException(status_code=404, detail="Player not found")

    def serialize_player(player):
        return {
            "id": player.id,
            "name": player.name,
            "image_url": player.image_url,
            "club": player.club,
            "league": formatLeagueName(player.league),
            "position": player.position,
            "age": player.age,
            "height": player.height_cm,
            "preferred_foot": player.preferred_foot,
            "market_value_m": player.market_value_m,
            "contract_expiration_date": player.contract_expiration_date,
            "matches": player.matches,
            "goals": player.goals,
            "assists": player.assists,
            "minutes_played": player.minutes_played,
            "goals_per_90": player.goals_per_90,
            "assists_per_90": player.assists_per_90,
            "goal_contributions": player.goal_contributions,
            "goal_contributions_per_90": player.goal_contributions_per_90,
            "yellow_cards": player.yellow_cards,
            "red_cards": player.red_cards,
        }

    return {
        "player1": serialize_player(player1),
        "player2": serialize_player(player2),
    }


@router.get("/players/{player_id}")
def get_player(
    player_id: int,
    db: Session = Depends(get_db),
):
    player = (
        db.query(PlayerDB)
        .filter(PlayerDB.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    club = get_player_club(db, player)

    return serialize_player_detail(player, club)


@router.get("/players/{player_id}/ai-context")
def get_player_ai_context(
    player_id: int,
    db: Session = Depends(get_db),
):
    context = build_player_context(player_id, db)

    if not context:
        raise HTTPException(status_code=404, detail="Player not found")

    return context


@router.get("/players/{player_id}/player-score")
def get_player_score(
    player_id: int,
    db: Session = Depends(get_db),
):
    result = analyze_player_score(player_id, db)

    if not result:
        raise HTTPException(status_code=404, detail="Player not found")

    return result


@router.get("/players/{player_id}/advanced-stats")
def get_player_advanced_stats(
    player_id: int,
    season: str = "2024/25",
    db: Session = Depends(get_db),
):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    stats = (
        db.query(PlayerAdvancedStatsDB)
        .filter(PlayerAdvancedStatsDB.player_id == player_id)
        .filter(PlayerAdvancedStatsDB.season == season)
        .filter(PlayerAdvancedStatsDB.source == "fbref")
        .first()
    )

    return serialize_advanced_stats(player_id, stats, season)


@router.get("/players/{player_id}/similar")
def get_similar_players(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    candidates = (
        db.query(PlayerDB)
        .filter(PlayerDB.id != player_id)
        .filter(PlayerDB.position.isnot(None))
        .all()
    )

    def numeric_score(base_value, candidate_value, max_difference, weight):
        if base_value is None or candidate_value is None:
            return 0

        try:
            difference = abs(float(base_value) - float(candidate_value))
        except Exception:
            return 0

        return max(0, 1 - (difference / max_difference)) * weight

    def performance_score(candidate):
        score = 0
        score += numeric_score(player.matches, candidate.matches, 30, 8)
        score += numeric_score(player.goals, candidate.goals, 20, 8)
        score += numeric_score(player.assists, candidate.assists, 20, 8)
        score += numeric_score(player.minutes_played, candidate.minutes_played, 3000, 8)
        return score

    scored_players = []

    for candidate in candidates:
        score = 0

        if player.position and candidate.position:
            if player.position.lower() == candidate.position.lower():
                score += 35
            elif player.position.lower() in candidate.position.lower() or candidate.position.lower() in player.position.lower():
                score += 20

        score += numeric_score(player.age, candidate.age, 12, 14)
        score += numeric_score(player.height_cm, candidate.height_cm, 25, 8)
        score += numeric_score(player.market_value_m, candidate.market_value_m, 80, 18)
        score += performance_score(candidate)

        if (
            player.preferred_foot
            and candidate.preferred_foot
            and player.preferred_foot.lower() == candidate.preferred_foot.lower()
        ):
            score += 5

        scored_players.append(
            {
                "id": candidate.id,
                "name": candidate.name,
                "club": candidate.club,
                "league": formatLeagueName(candidate.league),
                "position": candidate.position,
                "market_value_m": candidate.market_value_m,
                "age": candidate.age,
                "image_url": candidate.image_url,
                "similarity": min(99, max(1, round(score))),
            }
        )

    scored_players.sort(key=lambda item: item["similarity"], reverse=True)
    return scored_players[:8]


@router.post("/players/{player_id}/transfer-score")
def calculate_player_transfer_score(
    player_id: int,
    team: TeamNeed,
    db: Session = Depends(get_db),
):
    player = (
        db.query(PlayerDB)
        .filter(PlayerDB.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    result = engine.calculate(player, team)

    return {
        "success": True,
        "player": player.name,
        "transfer_index": result,
    }


@router.delete("/players/{player_id}")
def delete_player(
    player_id: int,
    db: Session = Depends(get_db),
):
    player = (
        db.query(PlayerDB)
        .filter(PlayerDB.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    db.delete(player)
    db.commit()

    return {
        "success": True,
        "message": f"Player {player_id} deleted",
    }


@router.post("/players/{player_id}/ai-report")
def generate_ai_report(
    player_id: int,
    db: Session = Depends(get_db),
):
    player = (
        db.query(PlayerDB)
        .filter(PlayerDB.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(
            status_code=404,
            detail="Player not found",
        )

    team = {
        "team_name": "Fenerbahçe",
        "needed_position": player.position,
        "max_market_value_m": 20,
        "max_salary_m": 4,
        "preferred_age_min": 22,
        "preferred_age_max": 29,
    }

    class TeamObject:
        def __init__(self, data):
            self.__dict__.update(data)

    team_object = TeamObject(team)

    score_data = engine.calculate(player, team_object)

    ai_result = ai_scout.generate_report(player, score_data)

    return {
        "success": ai_result["success"],
        "player": player.name,
        "report": ai_result["report"],
        "score": score_data,
        "error": ai_result.get("error"),
    }

@router.get("/players/{player_id}/valuations", response_model=PlayerValuationResponse)
def get_player_valuations(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    valuations = (
        db.query(PlayerValuationDB)
        .filter(PlayerValuationDB.player_id == player_id)
        .order_by(PlayerValuationDB.valuation_date.asc())
        .all()
    )

    history = [
        PlayerValuationItem(
            date=item.valuation_date,
            market_value=item.market_value,
        )
        for item in valuations
    ]

    if not valuations:
        return PlayerValuationResponse(
            player_id=player_id,
            current_value=None,
            peak_value=None,
            lowest_value=None,
            growth_percent=None,
            history=[],
        )

    first_value = valuations[0].market_value
    current_value = valuations[-1].market_value
    peak_value = max(item.market_value for item in valuations)
    lowest_value = min(item.market_value for item in valuations)

    growth_percent = None
    if first_value and first_value > 0:
        growth_percent = round(((current_value - first_value) / first_value) * 100, 2)

    return PlayerValuationResponse(
        player_id=player_id,
        current_value=current_value,
        peak_value=peak_value,
        lowest_value=lowest_value,
        growth_percent=growth_percent,
        history=history,
    )


@router.get("/players/{player_id}/transfers")
def get_player_transfers(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerDB).filter(PlayerDB.id == player_id).first()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    transfers = (
        db.query(PlayerTransferDB)
        .filter(PlayerTransferDB.player_id == player_id)
        .order_by(
            PlayerTransferDB.transfer_date.desc().nullslast(),
            PlayerTransferDB.id.desc(),
        )
        .all()
    )

    club_map = get_club_by_id_map(
        db,
        [
            club_id
            for item in transfers
            for club_id in [item.from_club_id, item.to_club_id]
        ],
    )

    def format_transfer_fee(value):
        if value is None or value <= 0:
            return None

        if value >= 1000000:
            return f"€{value / 1000000:.1f}M"

        if value >= 1000:
            return f"€{value / 1000:.0f}K"

        return f"€{value}"

    def get_transfer_label(transfer):
        transfer_type = (transfer.transfer_type or "").strip().lower()

        if transfer_type in {"loan", "loaned"}:
            return "Kiralık"

        if transfer_type in {"loan return", "end of loan"}:
            return "Kiralıktan geri döndü"

        if transfer_type in {"free transfer", "free", "ablöse yok"}:
            return "Bedelsiz"

        fee = transfer.transfer_fee_in_eur
        if fee is None:
            fee = transfer.transfer_fee

        formatted_fee = format_transfer_fee(fee)
        if formatted_fee:
            return formatted_fee

        return "-"

    transfer_items = [
        {
            "id": item.id,
            "player_id": item.player_id,
            "transfer_date": item.transfer_date,
            "transfer_season": item.transfer_season,
            "from_club_id": item.from_club_id,
            "to_club_id": item.to_club_id,
            "from_club_name": item.from_club_name,
            "to_club_name": item.to_club_name,
            "from_club_logo_url": (
                club_map[item.from_club_id].logo_url
                if item.from_club_id in club_map
                else None
            ),
            "to_club_logo_url": (
                club_map[item.to_club_id].logo_url
                if item.to_club_id in club_map
                else None
            ),
            "from_club_country": item.from_club_country,
            "to_club_country": item.to_club_country,
            "transfer_type": item.transfer_type,
            "transfer_fee_text": item.transfer_fee_text,
            "transfer_fee": item.transfer_fee,
            "transfer_fee_in_eur": item.transfer_fee_in_eur,
            "formatted_transfer_fee": format_transfer_fee(item.transfer_fee_in_eur),
            "transfer_label": get_transfer_label(item),
            "market_value_in_eur": item.market_value_in_eur,
            "player_name": item.player_name,
        }
        for item in transfers
    ]

    return {
        "player_id": player_id,
        "count": len(transfer_items),
        "transfers": transfer_items,
    }
