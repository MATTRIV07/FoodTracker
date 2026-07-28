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
        "redemption_code": None,
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
        "active": True,
    },
    {
        "restaurant": "ONO Hawaiian BBQ",
        "title": "$6 Plate Lunch",
        "description": "$6 plate lunch any day LAFC scores first, within the first half, in a home game.",
        "team": "lafc",
        "condition_type": "scores_first_half",
        "location_requirement": "home",
        "redemption_code": "LAFCSCORES",
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
        "active": True,
    },
    {
        "restaurant": "Carl's Jr.",
        "title": "Free Famous Star",
        "description": "Free Famous Star any day the Rams get an interception.",
        "team": "rams",
        "condition_type": "interception",
        "location_requirement": "any",
        "redemption_code": None,
        # NFL season hasn't started yet — flip to True once it has.
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

    for d in DEALS:
        team = team_objs[d["team"]]
        existing = Deal.query.filter_by(restaurant=d["restaurant"], title=d["title"], team_id=team.id).first()
        if existing is None:
            deal = Deal(
                restaurant=d["restaurant"],
                title=d["title"],
                description=d["description"],
                team_id=team.id,
                condition_type=d["condition_type"],
                location_requirement=d["location_requirement"],
                redemption_code=d["redemption_code"],
                active=d["active"],
            )
            db.session.add(deal)
            db.session.commit()
            print(f"Added deal: {d['restaurant']} / {d['title']}")
        else:
            print(f"Deal already exists: {d['restaurant']} / {d['title']}")
