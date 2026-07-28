"""Shared logic for ESPN's free, public (unofficial) sports APIs.

Different sports (soccer, football, ...) live under different league paths
but share the same JSON shape for team schedules and event summaries, so
each sport-specific adapter module just calls make_adapter() with its path.

Game "day" for a team is defined by kickoff time converted to US/Eastern —
games often kick off in the evening and cross UTC midnight, so a naive
UTC-date comparison would put some games on the wrong day.
"""

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import requests

_EASTERN = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")

# ESPN's normalized status.state values map onto the same vocabulary
# app/mlb_api.py effectively uses via abstractGameState.
_STATE_MAP = {"pre": "Preview", "in": "Live", "post": "Final"}


def _kickoff_eastern_date(iso_utc):
    dt = datetime.strptime(iso_utc, "%Y-%m-%dT%H:%MZ").replace(tzinfo=_UTC)
    return dt.astimezone(_EASTERN).date()


def make_adapter(league_path):
    """Build a get_team_game_today/get_live_feed/normalize_game trio for the
    given ESPN league path, e.g. "soccer/usa.1" or "football/nfl"."""
    base = f"https://site.api.espn.com/apis/site/v2/sports/{league_path}"
    schedule_url = base + "/teams/{team_id}/schedule"
    summary_url = base + "/summary"

    def get_team_game_today(team_id, game_date):
        resp = requests.get(schedule_url.format(team_id=team_id), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for event in data.get("events", []):
            event_date = event.get("date")
            if event_date and _kickoff_eastern_date(event_date) == game_date:
                return event
        return None

    def get_live_feed(event_id):
        resp = requests.get(summary_url, params={"event": event_id}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def normalize_game(event, team_external_id):
        comp = event["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        is_home = home["team"]["id"] == str(team_external_id)
        state = _STATE_MAP.get(comp["status"]["type"]["state"], "Preview")
        return {"id": event["id"], "is_home": is_home, "state": state}

    return SimpleNamespace(
        get_team_game_today=get_team_game_today,
        get_live_feed=get_live_feed,
        normalize_game=normalize_game,
    )
