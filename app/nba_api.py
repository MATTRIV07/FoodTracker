"""NBA adapter built on ESPN's free, public (unofficial) basketball API.

No API key required. Same pattern as nfl_api.py / mls_api.py.
"""

from app.espn_common import make_adapter

_adapter = make_adapter("basketball/nba")

get_team_game_today = _adapter.get_team_game_today
get_live_feed = _adapter.get_live_feed
normalize_game = _adapter.normalize_game
get_score = _adapter.get_score
