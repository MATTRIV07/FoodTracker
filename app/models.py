from datetime import date, datetime

from app import db


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    sport = db.Column(db.String(20), nullable=False, default="MLB")
    external_id = db.Column(db.Integer, nullable=False)  # id used by the sport's stats API

    __table_args__ = (db.UniqueConstraint("sport", "external_id"),)

    def __repr__(self):
        return f"<Team {self.name}>"


class Deal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    restaurant = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("team.id"), nullable=False)
    condition_type = db.Column(db.String(40), nullable=False)  # key into scanner.CONDITION_CHECKERS
    location_requirement = db.Column(db.String(10), nullable=False, default="home")  # home/away/any
    redemption_code = db.Column(db.String(40), nullable=True)  # promo code to show once unlocked
    active = db.Column(db.Boolean, nullable=False, default=True)

    team = db.relationship("Team", backref="deals")

    def __repr__(self):
        return f"<Deal {self.restaurant}: {self.title}>"


class DealActivation(db.Model):
    """One row per (deal, calendar day): the day's scan result."""

    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey("deal.id"), nullable=False)
    game_date = db.Column(db.Date, nullable=False, default=date.today)
    game_id = db.Column(db.String(40), nullable=True)  # sport-specific game/event id
    game_state = db.Column(db.String(20), nullable=True)  # Preview / Live / Final
    triggered = db.Column(db.Boolean, nullable=False, default=False)
    detail = db.Column(db.Text, nullable=True)
    checked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    deal = db.relationship("Deal", backref="activations")

    __table_args__ = (db.UniqueConstraint("deal_id", "game_date"),)
