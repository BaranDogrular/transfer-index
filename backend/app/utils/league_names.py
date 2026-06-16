import csv
from functools import lru_cache
from pathlib import Path


LEAGUE_NAME_OVERRIDES = {
    "premier-league": "Premier League",
    "gb1": "Premier League",
    "laliga": "LaLiga",
    "es1": "LaLiga",
    "ligue-1": "Ligue 1",
    "fr1": "Ligue 1",
    "serie-a": "Serie A",
    "it1": "Serie A",
    "bundesliga": "Bundesliga",
    "l1": "Bundesliga",
    "super-lig": "Süper Lig",
    "tr1": "Süper Lig",
    "eredivisie": "Eredivisie",
    "nl1": "Eredivisie",
    "championship": "EFL Championship",
    "gb2": "EFL Championship",
    "liga-portugal": "Liga Portugal",
    "po1": "Liga Portugal",
    "jupiler-pro-league": "Belgian Pro League",
    "be1": "Belgian Pro League",
    "super-league-greece": "Super League Greece",
    "super-league-1": "Super League Greece",
    "gr1": "Super League Greece",
    "mls": "Major League Soccer",
    "major-league-soccer": "Major League Soccer",
    "mls1": "Major League Soccer",
}


def fallback_league_name(value: str) -> str:
    words = str(value).replace("_", "-").replace("-", " ").split()
    return " ".join(word[:1].upper() + word[1:].lower() for word in words)


@lru_cache(maxsize=1)
def get_league_name_map():
    league_map = dict(LEAGUE_NAME_OVERRIDES)
    competitions_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "transfermarkt"
        / "competitions.csv"
    )

    if not competitions_path.exists():
        return league_map

    with competitions_path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            competition_name = (row.get("name") or "").strip()
            display_name = league_map.get(
                competition_name.lower(),
                fallback_league_name(competition_name),
            )

            for key in [
                row.get("competition_id"),
                row.get("competition_code"),
                row.get("name"),
                row.get("domestic_league_code"),
            ]:
                if key:
                    league_map.setdefault(str(key).strip().lower(), display_name)

    return league_map


def formatLeagueName(slug: str) -> str:
    if slug is None:
        return "-"

    value = str(slug).strip()

    if not value or value.lower() == "unknown":
        return "-"

    return get_league_name_map().get(value.lower(), fallback_league_name(value))


def format_league_name(slug: str) -> str:
    return formatLeagueName(slug)
