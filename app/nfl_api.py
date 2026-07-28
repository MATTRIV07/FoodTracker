"""NFL adapter built on ESPN's free, public (unofficial) football API.

No API key required. Verified against the live API on 2026-07-27:
https://site.api.espn.com/apis/site/v2/sports/football/nfl/...
"""

from app.espn_common import make_adapter

_adapter = make_adapter("football/nfl")

get_team_game_today = _adapter.get_team_game_today
get_live_feed = _adapter.get_live_feed
normalize_game = _adapter.normalize_game
