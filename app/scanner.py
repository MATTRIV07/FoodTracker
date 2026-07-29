"""Polls the sports API and updates each active Deal's status for today.

Condition checkers are registered in CONDITION_CHECKERS by Deal.condition_type,
so new trigger conditions (stolen base, shutout, etc.) can be added as a new
function + registry entry without touching the scan loop itself.
"""

import logging
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from app import db, mlb_api, mls_api, nfl_api, notify
from app.models import Deal, DealActivation

logger = logging.getLogger(__name__)

# All tracked teams (Dodgers, LAFC, Rams) play their home games on LA time, so
# "today" for game-lookup purposes must be the Pacific calendar day, not the
# server's local date. On a UTC-clocked host (e.g. Render), the server's date
# rolls over to the next day around 5pm Pacific -- right as most home games
# are starting -- which would otherwise make the scanner look up the wrong
# day's game for the rest of the night.
GAME_DAY_TZ = ZoneInfo("America/Los_Angeles")


def current_game_day():
    return datetime.now(GAME_DAY_TZ).date()


# Guards against the periodic scheduler tick and a manual "Scan now" click
# racing each other: both would otherwise try to insert the same
# (deal_id, game_date) DealActivation row and one commit would fail.
_scan_lock = threading.Lock()

# Maps Team.sport -> module exposing get_team_game_today(team_id, date),
# get_live_feed(game_id), normalize_game(raw_game, team_external_id).
SPORT_ADAPTERS = {
    "MLB": mlb_api,
    "MLS": mls_api,
    "NFL": nfl_api,
}


def check_double_play(feed, team_external_id, team_is_home, game_state):
    """True if `team` turned a double play on defense at any point in the game."""
    plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    for play in plays:
        event_type = play.get("result", {}).get("eventType") or ""
        if "double_play" not in event_type:
            continue
        # Top of inning = away team batting, home team on defense; bottom = reverse.
        defense_is_home = play["about"]["isTopInning"]
        if defense_is_home == team_is_home:
            return True, play["result"].get("description", "Double play turned.")
    return False, None


def check_team_win(feed, team_external_id, team_is_home, game_state):
    """True if `team` won. Only evaluated once the game is Final, so a mid-game lead can't trigger it early."""
    if game_state != "Final":
        return False, None
    runs = feed.get("liveData", {}).get("linescore", {}).get("teams", {})
    home_runs = runs.get("home", {}).get("runs")
    away_runs = runs.get("away", {}).get("runs")
    if home_runs is None or away_runs is None or home_runs == away_runs:
        return False, None
    team_runs, opp_runs = (home_runs, away_runs) if team_is_home else (away_runs, home_runs)
    if team_runs > opp_runs:
        return True, f"Final: won {team_runs}-{opp_runs}."
    return False, None


def check_scores_first_half(feed, team_external_id, team_is_home, game_state):
    """True if `team` scored the match's first goal, and it came in the first half."""
    goals = [e for e in feed.get("keyEvents", []) if e.get("scoringPlay")]
    if not goals:
        return False, None
    first_goal = goals[0]
    scoring_team_id = str(first_goal.get("team", {}).get("id"))
    if scoring_team_id != str(team_external_id):
        return False, None
    if first_goal.get("period", {}).get("number") != 1:
        return False, None
    return True, first_goal.get("text", "Scored first, in the first half.")


def check_pitching_strikeouts_7plus(feed, team_external_id, team_is_home, game_state):
    """True if `team`'s pitching staff has recorded 7+ strikeouts so far in the game."""
    side = "home" if team_is_home else "away"
    stats = (
        feed.get("liveData", {})
        .get("boxscore", {})
        .get("teams", {})
        .get(side, {})
        .get("teamStats", {})
        .get("pitching", {})
    )
    strikeouts = stats.get("strikeOuts")
    if strikeouts is None or strikeouts < 7:
        return False, None
    return True, f"Pitching staff has {strikeouts} strikeouts."


def check_interception(feed, team_external_id, team_is_home, game_state):
    """True if `team`'s defense has recorded an interception at any point in the game."""
    drives = feed.get("drives", {}).get("previous", [])
    for drive in drives:
        for play in drive.get("plays", []):
            if "Intercept" not in play.get("type", {}).get("text", ""):
                continue
            defense = next(
                (p for p in play.get("teamParticipants", []) if p.get("type") == "defense"),
                None,
            )
            if defense and str(defense.get("id")) == str(team_external_id):
                return True, play.get("text", "Interception recorded.")
    return False, None


CONDITION_CHECKERS = {
    "double_play": check_double_play,
    "team_win": check_team_win,
    "scores_first_half": check_scores_first_half,
    "interception": check_interception,
    "pitching_strikeouts_7plus": check_pitching_strikeouts_7plus,
}


def _get_or_create_activation(deal_id, game_date):
    activation = DealActivation.query.filter_by(deal_id=deal_id, game_date=game_date).first()
    if activation is None:
        activation = DealActivation(deal_id=deal_id, game_date=game_date)
        db.session.add(activation)
    return activation


def scan_deal(deal, today):
    team = deal.team
    activation = _get_or_create_activation(deal.id, today)
    activation.checked_at = datetime.utcnow()

    adapter = SPORT_ADAPTERS.get(team.sport)
    if adapter is None:
        logger.warning("No sport adapter registered for sport=%s", team.sport)
        db.session.commit()
        return

    raw_game = adapter.get_team_game_today(team.external_id, today)
    if raw_game is None:
        activation.game_id = None
        activation.game_state = None
        if not activation.triggered:
            activation.detail = "No game scheduled today."
        db.session.commit()
        return

    game = adapter.normalize_game(raw_game, team.external_id)
    is_home = game["is_home"]
    activation.game_id = str(game["id"])
    activation.game_state = game["state"]

    location_ok = (
        deal.location_requirement == "any"
        or (deal.location_requirement == "home" and is_home)
        or (deal.location_requirement == "away" and not is_home)
    )
    if not location_ok:
        if not activation.triggered:
            activation.detail = (
                f"{team.name} playing {'home' if is_home else 'away'} today; "
                f"deal requires a {deal.location_requirement} game."
            )
        db.session.commit()
        return

    if activation.game_state == "Preview":
        if not activation.triggered:
            activation.detail = "Game hasn't started yet."
        db.session.commit()
        return

    checker = CONDITION_CHECKERS.get(deal.condition_type)
    if checker is None:
        logger.warning("No checker registered for condition_type=%s", deal.condition_type)
        db.session.commit()
        return

    feed = adapter.get_live_feed(game["id"])
    triggered, detail = checker(feed, team.external_id, is_home, activation.game_state)

    # Sticky: once triggered, stays triggered for the day even if a later poll
    # somehow doesn't re-detect the play.
    just_triggered = triggered and not activation.triggered
    if just_triggered:
        activation.triggered = True
        activation.detail = detail
    elif not activation.triggered:
        activation.detail = f"Game {activation.game_state.lower()}, condition not met yet."

    db.session.commit()

    if just_triggered:
        notify.send_deal_triggered(deal, detail)


def scan_all_active_deals():
    if not _scan_lock.acquire(blocking=False):
        logger.info("Scan already in progress, skipping this trigger.")
        return
    try:
        today = current_game_day()
        deals = Deal.query.filter_by(active=True).all()
        for deal in deals:
            deal_id = deal.id
            try:
                scan_deal(deal, today)
            except Exception:
                logger.exception("Failed to scan deal id=%s", deal_id)
                db.session.rollback()
    finally:
        _scan_lock.release()
