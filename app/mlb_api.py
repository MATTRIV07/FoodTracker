"""Thin wrapper around MLB's free, public (unofficial) Stats API.

No API key required. Verified against the live API on 2026-07-27:
https://statsapi.mlb.com/api/v1/schedule and .../api/v1.1/game/{id}/feed/live
"""

import requests

SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
LIVE_FEED_URL = "https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"


def get_team_game_today(team_id, game_date):
    """Return the schedule entry for a team on `game_date`, or None if no game."""
    resp = requests.get(
        SCHEDULE_URL,
        params={"sportId": 1, "teamId": team_id, "date": game_date.isoformat()},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    for day in data.get("dates", []):
        for game in day.get("games", []):
            return game
    return None


def get_live_feed(game_pk):
    resp = requests.get(LIVE_FEED_URL.format(game_pk=game_pk), timeout=10)
    resp.raise_for_status()
    return resp.json()


def normalize_game(game, team_external_id):
    return {
        "id": game["gamePk"],
        "is_home": game["teams"]["home"]["team"]["id"] == team_external_id,
        "state": game["status"]["abstractGameState"],
    }


def get_score(feed):
    teams = feed.get("gameData", {}).get("teams", {})
    runs = feed.get("liveData", {}).get("linescore", {}).get("teams", {})
    return {
        "home_team": teams.get("home", {}).get("abbreviation"),
        "home_score": runs.get("home", {}).get("runs"),
        "away_team": teams.get("away", {}).get("abbreviation"),
        "away_score": runs.get("away", {}).get("runs"),
    }
