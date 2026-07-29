# FoodTracker

Tracks sports-triggered fast food deals (e.g. "The Habit gives away a free
Double Char burger any day the Dodgers turn a double play at home", "Panda
Express offers a $7 Panda Plate any day the Dodgers win", "ONO Hawaiian BBQ
offers a $6 plate lunch any day LAFC scores first in the first half of a home
game", "Carl's Jr. gives away a Famous Star any day the Rams get an
interception") and shows today's status, plus the redemption code, on a
simple web page. No accounts, no login.

## How it works

- A background scanner polls a sports API on an interval and writes results
  to SQLite. Three are wired up: the [MLB Stats API](https://statsapi.mlb.com)
  for baseball, and [ESPN's public API](https://site.api.espn.com) for MLS
  soccer and NFL football — all free, public, and require no API key.
- The web page only ever reads from SQLite — it never calls a sports API on
  page load. This keeps the page fast and it still shows the last-known state
  even if a sports API is briefly unreachable.
- Each `Team` has a `sport` (`MLB` / `MLS` / `NFL`), which `app/scanner.py`'s
  `SPORT_ADAPTERS` maps to `app/mlb_api.py`, `app/mls_api.py`, or
  `app/nfl_api.py`. The latter two are thin wrappers around
  `app/espn_common.py` (MLS and NFL share the exact same ESPN JSON shape, just
  different league paths). Every adapter exposes the same three functions —
  `get_team_game_today`, `get_live_feed`, `normalize_game` — so `scan_deal`
  doesn't need to know which sport it's looking at. Adding another sport means
  writing a new adapter module with that same interface (or, if it's also on
  ESPN, calling `espn_common.make_adapter("<league path>")`).
- Each `Deal` is tied to a `Team` and a `condition_type` (`double_play`,
  `team_win`, `pitching_strikeouts_7plus`, `scores_first_half`,
  `interception`) plus a `location_requirement` (`home` / `away` / `any`) and
  an optional `redemption_code` shown once the deal unlocks. New condition
  types are added as a function in `app/scanner.py`'s `CONDITION_CHECKERS`
  registry — no changes needed to the scan loop itself. A condition's feed
  format is sport-specific (whatever its adapter's `get_live_feed` returns),
  so a given condition_type only makes sense paired with teams from the sport
  it was written for.
- A `Deal.active` flag controls both scanning and display — set it `False`
  for deals tied to a sport that's out of season (e.g. NFL deals added before
  kickoff), and flip it back on once games are being played.
- Conditions that depend on the final result (like `team_win`) only evaluate
  once the game state is `Final` — a checker gets the current game state
  passed in, so it can avoid triggering off a mid-game lead.
- `DealActivation` rows are the daily scan result per deal (one row per
  deal per calendar day). Once a deal triggers for the day it stays
  "unlocked" even if a later poll misses re-detecting the play.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py        # creates tables + seeds teams/deals from seed.py
python wsgi.py         # runs the dev server on http://127.0.0.1:5000
```

Visit `http://127.0.0.1:5000`. Use the "Scan now" button to trigger an
on-demand check instead of waiting for the interval.

## Adding more deals

Add an entry to the `DEALS` list in `seed.py` (add to `TEAMS` too if it's a
new team), then re-run `python seed.py` — it only inserts what's missing, so
it's safe to run repeatedly. You'll need the team's external id if it's not
already in `TEAMS`:

```
curl "https://statsapi.mlb.com/api/v1/teams?sportId=1"                       # MLB
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/teams"      # MLS
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"      # NFL
```

Note: exact promo terms (whether a deal is still running, home-only vs. any
game, national vs. local-market) come from you — this project doesn't have a
live source for restaurant promotions, only for game results.

## Adding more condition types

Currently implemented:
- `double_play` (MLB) — team turns a double play on defense
- `team_win` (MLB) — team wins; only checked once the game is Final
- `pitching_strikeouts_7plus` (MLB) — team's pitching staff has 7+ strikeouts so far
- `scores_first_half` (MLS) — team scores the match's first goal, in the first half
- `interception` (NFL) — team's defense records an interception

MLB's live game feed (`GET /api/v1.1/game/{gamePk}/feed/live`) exposes full
play-by-play under `liveData.plays.allPlays[].result.eventType`, e.g.
`grounded_into_double_play`, `strikeout_double_play`, `stolen_base_2b`,
`home_run`; final score lives at `liveData.linescore.teams.{home,away}.runs`;
team pitching totals (including strikeouts) live at
`liveData.boxscore.teams.{home,away}.teamStats.pitching`.

ESPN's MLS summary feed (`GET /summary?event={id}`) exposes a chronological
`keyEvents` list; goals have `scoringPlay: true`, a `team.id`, and
`period.number` (1 = first half, including stoppage time).

ESPN's NFL summary feed exposes `drives.previous[].plays[]`; each play has a
`type.text` (e.g. `"Pass Interception Return"`, `"Interception Return
Touchdown"`) and a `teamParticipants` list where the entry with
`type: "defense"` is the team credited with the play — that's true even for
a pick-six, so no separate scoring-play check is needed.

Add a new checker function with the same signature as
`check_double_play(feed, team_external_id, team_is_home, game_state)` in
`app/scanner.py`, then register it in `CONDITION_CHECKERS`.

MLB, MLS, and NFL are wired up. A new sport needs a new adapter module (see
"How it works" above) implementing `get_team_game_today`, `get_live_feed`,
and `normalize_game`, then an entry in `SPORT_ADAPTERS`.

## Email notifications

When a deal flips to "unlocked," `app/notify.py` sends an email via
[Resend](https://resend.com) (a send-only API key — it can't read your
inbox, unlike a Gmail App Password) to every recipient in the mailing list.
Setup:

1. Sign up free at resend.com and create an API key.
2. Copy `.env.example` to `.env` (already gitignored) and fill in
   `RESEND_API_KEY`.
3. `config.py` loads `.env` automatically via `python-dotenv` — no need to
   export env vars manually for local dev.

The recipient list is `NOTIFY_EMAIL_TO` (an always-on owner address set via
env var, optional) plus everyone who signs up through the "Get an email when
any deal unlocks" form on the site itself — those are stored in the
`Subscriber` table and each gets a one-click unsubscribe link in every email
(`/unsubscribe/<token>`, no login needed). Recipients get one email each
(not a single email with multiple `to` addresses), so a bad address can't
block anyone else's notification and subscribers never see each other's
emails.

If `RESEND_API_KEY` isn't set, or there are no recipients at all,
notifications are silently skipped — the app works fine without them, this
just adds an alert on top of the web page. On Render/Railway, set env vars
in the platform's dashboard instead of a `.env` file.

## Configuration

Environment variables (see `.env.example`):

- `SCAN_INTERVAL_SECONDS` — how often the background scanner polls (default 300)
- `SECRET_KEY` — Flask secret key (also signs the flash-message session cookie)
- `DATABASE_URL` — defaults to a local SQLite file
- `SITE_URL` — public base URL, used to build unsubscribe links (default `http://127.0.0.1:5001`)
- `RESEND_API_KEY`, `NOTIFY_EMAIL_TO`, `NOTIFY_EMAIL_FROM` — see "Email notifications" above

## Deploying (Render / Railway)

Both platforms will pick up `Procfile` (`gunicorn wsgi:app`) and
`requirements.txt` automatically. A `render.yaml` blueprint is included for
Render.

**Important:** the scanner runs in-process as a background thread inside the
web process. Keep the process count at **1 worker** (already set in the
`Procfile`) — running multiple workers would start multiple schedulers, each
polling the sports API independently and writing duplicate/racy updates. For
Render specifically, run `python seed.py` once during the build step (already
wired into `render.yaml`) so the example deal exists on first deploy.

SQLite lives on local disk. On a platform with a truly ephemeral filesystem
the DB resets on every redeploy and the scanner just repopulates it from
live data within one scan interval — but that turned out not to be a safe
assumption to build on: a deploy that added a model column, landing on a
build where the previous SQLite file survived, 500'd on every request
because `db.create_all()` only creates missing tables, it doesn't ALTER an
existing one to add a column. `app/__init__.py`'s `_ensure_schema()` now
checks the live table columns against the models on every startup and drops
+ recreates the database only if something's actually missing, instead of
either assuming the disk resets or unconditionally wiping it. This means
`Team`/`Deal`/`DealActivation` rows (already designed to be disposable) and
`Subscriber` rows (not disposable — that's your mailing list) survive any
deploy that doesn't change the schema, and only get reset on a deploy that
does.
