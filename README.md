# FoodTracker

Tracks sports-triggered fast food deals (e.g. "The Habit gives away a free
Double Char burger any day the Dodgers turn a double play at home", "Panda
Express offers a $7 Panda Plate any day the Dodgers win", "ONO Hawaiian BBQ
offers a $5.99 plate lunch any day LAFC scores first in the first half of a
home game", "Carl's Jr. gives away a Famous Star any day the Rams get an
interception") and shows today's status, plus the redemption code, on a
simple web page. No accounts, no login.

## How it works

- A background scanner polls a sports API on an interval and writes results
  to the database. Five sports are wired up: the
  [MLB Stats API](https://statsapi.mlb.com) for baseball, and
  [ESPN's public API](https://site.api.espn.com) for MLS soccer, NFL
  football, NBA basketball, and NHL hockey — all free, public, and require no
  API key.
- The web page only ever reads from the database — it never calls a sports
  API on page load. This keeps the page fast and it still shows the
  last-known state even if a sports API is briefly unreachable.
- Each `Team` has a `sport` (`MLB` / `MLS` / `NFL` / `NBA` / `NHL`), which
  `app/scanner.py`'s `SPORT_ADAPTERS` maps to `app/mlb_api.py`,
  `app/mls_api.py`, `app/nfl_api.py`, `app/nba_api.py`, or `app/nhl_api.py`.
  All but the MLB one are thin wrappers around `app/espn_common.py` (every
  ESPN sport shares the exact same JSON shape, just a different league path).
  Every adapter exposes the same four functions — `get_team_game_today`,
  `get_live_feed`, `normalize_game`, `get_score` — so `scan_deal` doesn't
  need to know which sport it's looking at. Adding another sport means
  writing a new adapter module with that same interface (or, if it's also on
  ESPN, calling `espn_common.make_adapter("<league path>")` — see
  `nba_api.py`/`nhl_api.py` for the two-line pattern).
- Each `Deal` is tied to a `Team` and a `condition_type` (see "Adding more
  condition types" below) plus a `location_requirement` (`home` / `away` /
  `any`) and an optional `redemption_code` shown once the deal unlocks. New
  condition types are added as a function in `app/scanner.py`'s
  `CONDITION_CHECKERS` registry — no changes needed to the scan loop itself.
  A condition's feed format is sport-specific (whatever its adapter's
  `get_live_feed` returns), so a given condition_type only makes sense
  paired with teams from the sport it was written for — e.g. `team_win` is
  MLB-only (reads the MLB Stats API's linescore shape) and `espn_team_win` is
  its equivalent for any ESPN-backed sport (NFL/MLS/NBA/NHL).
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
new team), then re-run `python seed.py`. It's safe to run repeatedly — deals
are matched on `(restaurant, team, condition_type)`, which is a deal's
stable functional identity, so re-running with a corrected `title` or
`description` (e.g. a price fix) updates the existing row in place instead
of creating a duplicate. You'll need the team's external id if it's not
already in `TEAMS`:

```
curl "https://statsapi.mlb.com/api/v1/teams?sportId=1"                       # MLB
curl "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/teams"      # MLS
curl "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"      # NFL
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"    # NBA
curl "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/teams"        # NHL
```

Note: exact promo terms (whether a deal is still running, home-only vs. any
game, national vs. local-market) come from you — this project doesn't have a
live source for restaurant promotions, only for game results.

## Adding more condition types

Currently implemented:
- `double_play` (MLB) — team turns a double play on defense
- `team_win` (MLB) — team wins; only checked once the game is Final
- `pitching_strikeouts_7plus` (MLB) — team's pitching staff has 7+ strikeouts so far
- `team_runs_6plus` (MLB) — team has scored 6+ runs so far
- `steals_base` (MLB) — team has recorded a stolen base so far
- `scores_first_half` (MLS) — team scores the match's first goal, in the first half
- `scores_goal` (MLS) — team scores at least one goal, any half
- `interception` (NFL) — team's defense records an interception
- `espn_team_win` (NFL/MLS/NBA/NHL) — team wins; only checked once Final.
  Separate from `team_win` because it reads ESPN's summary feed shape
  (`header.competitions[0].competitors[]`) rather than the MLB Stats API's

MLB's live game feed (`GET /api/v1.1/game/{gamePk}/feed/live`) exposes full
play-by-play under `liveData.plays.allPlays[].result.eventType`, e.g.
`grounded_into_double_play`, `strikeout_double_play`, `stolen_base_2b`,
`home_run`; final score and each team's runs live at
`liveData.linescore.teams.{home,away}.runs`; team pitching totals (including
strikeouts) live at `liveData.boxscore.teams.{home,away}.teamStats.pitching`,
and team batting totals (including stolen bases) live at
`liveData.boxscore.teams.{home,away}.teamStats.batting`.

ESPN's summary feed (`GET /summary?event={id}`) — shared by MLS, NFL, NBA,
and NHL — exposes a chronological `keyEvents` list for scoring plays (goals
have `scoringPlay: true`, a `team.id`, and `period.number`, where 1 = first
half/period including stoppage time); final score lives at
`header.competitions[0].competitors[]` (`homeAway` + `score` per entry); NFL
additionally exposes `drives.previous[].plays[]`, where each play has a
`type.text` (e.g. `"Pass Interception Return"`) and a `teamParticipants` list
whose `type: "defense"` entry is the team credited with the play — true even
for a pick-six, so no separate scoring-play check is needed.

Add a new checker function with the same signature as
`check_double_play(feed, team_external_id, team_is_home, game_state)` in
`app/scanner.py`, then register it in `CONDITION_CHECKERS`.

MLB, MLS, NFL, NBA, and NHL are wired up. A new sport needs a new adapter
module (see "How it works" above) implementing `get_team_game_today`,
`get_live_feed`, `normalize_game`, and `get_score`, then an entry in
`SPORT_ADAPTERS`.

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

### Turning off sandbox mode

A fresh Resend account is in **sandbox mode**: it will only deliver to the
account owner's own address, no matter who's in the `Subscriber` table —
every other recipient's send fails silently (logged, not raised). This is
the current state of the deployed site as of 2026-08. `NOTIFY_EMAIL_FROM`
defaults to `FoodTracker <onboarding@resend.dev>`, Resend's shared sandbox
sending address, which is the tell that it's still in this state.
`app/__init__.py` logs a warning at boot if `RESEND_API_KEY` is set and
`NOTIFY_EMAIL_FROM` still contains `resend.dev`, in case this gets missed.

To turn on real delivery (free on Resend's Free plan — no Resend upgrade
needed, only a domain purchase if you don't already own one):

1. Buy a domain from any registrar, if you don't already have one you want
   to use for this (~$10-15/year).
2. In the Resend dashboard, add the domain and add the DNS records it gives
   you (DKIM/SPF, a few TXT/CNAME entries) at your registrar.
3. Wait for Resend to verify it (usually minutes to a few hours).
4. Update the `NOTIFY_EMAIL_FROM` env var (in Render's dashboard, or `.env`
   locally) to an address on that domain, e.g.
   `FoodTracker <deals@yourdomain.com>`. Restart/redeploy to pick it up.

Resend's Free plan then supports 3,000 emails/month, capped at 100/day —
plenty for a personal-scale subscriber list; upgrade to Pro ($20/mo, 50,000
emails/mo, no daily cap) only if that's ever not enough.

## Configuration

Environment variables (see `.env.example`):

- `SCAN_INTERVAL_SECONDS` — how often the background scanner polls (default 300)
- `SECRET_KEY` — Flask secret key (also signs the flash-message session cookie); random per-boot if unset, so set this explicitly wherever session state needs to survive a restart
- `DATABASE_URL` — defaults to a local SQLite file; set to a Postgres URL in production (see "Deploying" below) since SQLite doesn't survive a Render deploy with no attached disk
- `SITE_URL` — public base URL, used to build unsubscribe links (default `http://127.0.0.1:5001`)
- `RESEND_API_KEY`, `NOTIFY_EMAIL_TO`, `NOTIFY_EMAIL_FROM` — see "Email notifications" above

## Deploying (Render / Railway)

Both platforms will pick up `Procfile` (`gunicorn wsgi:app`) and
`requirements.txt` automatically. A `render.yaml` blueprint is included for
Render, including a managed Postgres instance (see below) and
`RESEND_API_KEY`/`NOTIFY_EMAIL_TO`/`NOTIFY_EMAIL_FROM` documented as
`sync: false` env vars (set manually in the dashboard, not provisioned by
the blueprint).

**Important:** the scanner runs in-process as a background thread inside the
web process. Keep the process count at **1 worker** (already set in the
`Procfile` and `render.yaml`'s `startCommand`) — running multiple workers
would start multiple schedulers, each polling the sports API independently
and writing duplicate/racy updates; it would also break the in-memory rate
limiter (see `app/__init__.py`), since each worker would track limits
separately. For Render specifically, `python seed.py` runs once during the
build step (already wired into `render.yaml`) so the example deals exist on
first deploy, and re-running it on every subsequent deploy self-heals any
deal data that's missing or out of date (see "Adding more deals" above).

**Database**: `render.yaml` provisions a real Render Postgres instance
(`foodtracker-db`, Basic-256mb, $6/mo) and wires it in via `DATABASE_URL`.
This isn't optional set-dressing — a plain web service with no attached
disk and no external database gets a **fresh, empty filesystem on every
deploy** on Render, so without a real database, every `git push` was
silently wiping the `Subscriber` mailing list and all score history back to
empty. (Render's free Postgres tier expires after 30 days, so it isn't a
substitute here.) Provisioning the database still requires approving the
Blueprint sync in the Render dashboard — pushing this repo alone doesn't
create billed infrastructure.

`app/__init__.py`'s `_ensure_schema()` checks the live table columns against
the models on every startup and drops + recreates the database only if
something's actually missing (e.g. a deploy added a model column), instead
of unconditionally wiping it — `db.create_all()` alone only creates missing
tables, it doesn't `ALTER` an existing one to add a column, which would
otherwise 500 on every request touching that column. With Postgres actually
persisting between deploys, this means `Subscriber` rows only get reset by a
schema-changing deploy, not every deploy.
