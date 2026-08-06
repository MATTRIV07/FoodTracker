"""Seeds the database with teams and deals. Safe to run multiple times —
existing teams/deals are left alone, only missing ones are added.

To add a new deal: add an entry to TEAMS if the team isn't there yet, then
add an entry to DEALS. condition_type must be a key in
app.scanner.CONDITION_CHECKERS.
"""

from app import create_app, db
from app.models import Team, Deal

app = create_app(start_background_scanner=False)

TEAMS = {
    "dodgers": {"name": "Los Angeles Dodgers", "sport": "MLB", "external_id": 119},
    "lafc": {"name": "LAFC", "sport": "MLS", "external_id": 18966},
    "rams": {"name": "Los Angeles Rams", "sport": "NFL", "external_id": 14},
    "lakers": {"name": "Los Angeles Lakers", "sport": "NBA", "external_id": 13},
    "kings": {"name": "Los Angeles Kings", "sport": "NHL", "external_id": 8},
    "galaxy": {"name": "LA Galaxy", "sport": "MLS", "external_id": 187},
}

DEALS = [
    {
        "restaurant": "The Habit Burger Grill",
        "title": "Free Double Char Burger",
        "description": (
            "Free Double Char burger with any purchase when the Dodgers "
            "turn a double play in a home game."
        ),
        "team": "dodgers",
        "condition_type": "double_play",
        "location_requirement": "home",
        "redemption_code": "DODGERS26",
        "redemption_window": "Redeemable the next day only, until close of business.",
        "how_to_redeem": (
            "Log into the Habit app or website (MyHabit account), open My "
            "Offers, enter the code, and add a Double Char plus $8+ in other "
            "items to your order."
        ),
        "active": True,
    },
    {
        "restaurant": "Panda Express",
        "title": "$7 Panda Plate",
        "description": "$7 two-entree Panda Plate any day the Dodgers win.",
        "team": "dodgers",
        "condition_type": "team_win",
        "location_requirement": "any",
        "redemption_code": "DODGERSWIN",
        "redemption_window": "Redeemable the next day only, until 11:59 PM.",
        "how_to_redeem": (
            "Order through the Panda Express app or website (Panda Rewards "
            "account), pick a 2-entree Panda Plate, and enter the code at "
            "checkout."
        ),
        "active": True,
    },
    {
        "restaurant": "ONO Hawaiian BBQ",
        "title": "$5.99 Plate Lunch",
        "description": "$5.99 plate lunch any day LAFC scores first, within the first half, in a home game.",
        "team": "lafc",
        "condition_type": "scores_first_half",
        "location_requirement": "home",
        "redemption_code": "LAFCSCORES",
        "redemption_window": "Redeemable the next business day only.",
        "how_to_redeem": (
            "Online orders only via onohawaiianbbq.com (registered account "
            "required) — enter the code at checkout."
        ),
        "active": True,
    },
    {
        "restaurant": "Jack in the Box",
        "title": "Free Jumbo Jack",
        "description": (
            "Free Jumbo Jack with purchase of a large drink any day Dodgers "
            "pitchers record 7+ strikeouts, home or away."
        ),
        "team": "dodgers",
        "condition_type": "pitching_strikeouts_7plus",
        "location_requirement": "any",
        "redemption_code": "GODODGERS26",
        "redemption_window": "Redeemable the next day only.",
        "how_to_redeem": "Redeem in-store or via the Jack in the Box app using the code.",
        "active": True,
    },
    {
        "restaurant": "Carl's Jr.",
        "title": "Free Famous Star",
        "description": (
            "Free Famous Star (with cheese) with the purchase of a large "
            "drink any day the Rams get an interception."
        ),
        "team": "rams",
        "condition_type": "interception",
        "location_requirement": "any",
        "redemption_code": None,
        "redemption_window": (
            "Promo code unlocks in the Carl's Jr. app 2 days after the "
            "qualifying game; offer expires 1 week after it unlocks."
        ),
        "how_to_redeem": (
            "Open the Carl's Jr. app (My Rewards account), tap Add Promo "
            "Code once it unlocks, then redeem in-app (Order Ahead) or "
            "in-restaurant by showing the QR code — purchase of a large "
            "drink required. Carl's Jr.'s own page is inconsistent about "
            "whether a purchase is required (body text says no, the promo "
            "graphic says a large drink is required) — we're listing the "
            "safer, purchase-required version."
        ),
        "active": True,
    },
    {
        "restaurant": "McDonald's",
        "title": "Free 6pc Chicken McNuggets",
        "description": (
            "Free 6-piece Chicken McNuggets with a $2 minimum purchase any "
            "day the Dodgers score 6 or more runs in a home game."
        ),
        "team": "dodgers",
        "condition_type": "team_runs_6plus",
        "location_requirement": "home",
        "redemption_code": None,
        "redemption_window": "Redeemable the next day only.",
        "how_to_redeem": (
            "Open the McDonald's app, find the offer under Rewards & Deals, "
            "and redeem with a $2+ purchase."
        ),
        "active": True,
    },
    {
        "restaurant": "ampm",
        "title": "Free Hot Dog & Slim Coca-Cola",
        "description": (
            "Free hot dog and 12oz Slim Coca-Cola any day the Dodgers steal "
            "a base in a home game."
        ),
        "team": "dodgers",
        "condition_type": "steals_base",
        "location_requirement": "home",
        "redemption_code": None,
        "redemption_window": "Redeemable the next day only.",
        "how_to_redeem": "Redeem via the ampm app.",
        "active": True,
    },
    {
        "restaurant": "Jack in the Box",
        "title": "Free 2 Tacos",
        "description": "Free 2 tacos with any size drink purchase any day the Lakers win.",
        "team": "lakers",
        "condition_type": "espn_team_win",
        "location_requirement": "any",
        "redemption_code": "LETSGOLAKERS",
        "redemption_window": "Redeemable the next day only.",
        "how_to_redeem": (
            "Open the Jack in the Box app, add any size drink to your "
            "order, and enter code LETSGOLAKERS at checkout."
        ),
        # Sourced from recent (2026) social posts, not Jack in the Box's own
        # site — and unconfirmed whether it's home-only or any game. Hidden
        # until double-checked; see foodtracker_project memory.
        "active": False,
    },
    {
        "restaurant": "McDonald's",
        "title": "Free McFlurry",
        "description": "Free McFlurry with a $2 minimum purchase any day the Kings win.",
        "team": "kings",
        "condition_type": "espn_team_win",
        "location_requirement": "any",
        "redemption_code": None,
        "redemption_window": "Redeemable the next day only.",
        "how_to_redeem": "Redeem via the McDonald's app with a $2+ purchase.",
        # Weakly sourced (a single ~7-month-old Instagram post, no official
        # McDonald's/Kings page found) — exact terms unconfirmed. Hidden
        # until verified; see foodtracker_project memory.
        "active": False,
    },
    {
        "restaurant": "NORMS Restaurants",
        "title": "Free Stack of Buttermilk Hotcakes",
        "description": "Free stack of Buttermilk Hotcakes any day the LA Galaxy score at least one goal at home.",
        "team": "galaxy",
        "condition_type": "scores_goal",
        "location_requirement": "home",
        "redemption_code": None,
        "redemption_window": "Valid for 3 days after the goal is scored.",
        "how_to_redeem": (
            "NORMS Rewards members only. Dine-in or to-go at a Southern "
            "California NORMS location — not valid on NORMS.com, the "
            "NORMS Rewards app, third-party delivery, or catering orders. "
            "Must present the offer at checkout."
        ),
        # Confirmed on lagalaxy.com/norms, so terms are solid — hidden for
        # now purely because it's a new team/sport combo we haven't run
        # live yet. Safe to activate once verified end-to-end.
        "active": False,
    },
]

with app.app_context():
    team_objs = {}
    for key, info in TEAMS.items():
        team = Team.query.filter_by(sport=info["sport"], external_id=info["external_id"]).first()
        if team is None:
            team = Team(name=info["name"], sport=info["sport"], external_id=info["external_id"])
            db.session.add(team)
            db.session.commit()
            print(f"Added team: {info['name']}")
        team_objs[key] = team

    # Matched on (restaurant, team, condition_type) rather than including
    # title -- that's a deal's stable identity, while title/description/
    # price/etc. are presentational details we sometimes need to correct
    # (e.g. a price fix) without that correction being mistaken for a new
    # deal and creating a duplicate row.
    UPDATABLE_FIELDS = [
        "title", "description", "location_requirement", "redemption_code",
        "redemption_window", "how_to_redeem", "active",
    ]
    for d in DEALS:
        team = team_objs[d["team"]]
        existing = Deal.query.filter_by(
            restaurant=d["restaurant"], team_id=team.id, condition_type=d["condition_type"]
        ).first()
        if existing is None:
            deal = Deal(
                restaurant=d["restaurant"],
                title=d["title"],
                description=d["description"],
                team_id=team.id,
                condition_type=d["condition_type"],
                location_requirement=d["location_requirement"],
                redemption_code=d["redemption_code"],
                redemption_window=d["redemption_window"],
                how_to_redeem=d["how_to_redeem"],
                active=d["active"],
            )
            db.session.add(deal)
            db.session.commit()
            print(f"Added deal: {d['restaurant']} / {d['title']}")
        else:
            changed = [f for f in UPDATABLE_FIELDS if getattr(existing, f) != d[f]]
            if changed:
                for f in changed:
                    setattr(existing, f, d[f])
                db.session.commit()
                print(f"Updated deal: {d['restaurant']} / {d['title']} (changed: {', '.join(changed)})")
            else:
                print(f"Deal unchanged: {d['restaurant']} / {d['title']}")
