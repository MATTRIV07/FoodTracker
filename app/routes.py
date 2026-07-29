from datetime import timedelta

from flask import Blueprint, redirect, render_template, url_for

from app.models import Deal, DealActivation
from app.scanner import current_game_day, scan_all_active_deals

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    today = current_game_day()
    yesterday = today - timedelta(days=1)
    deals = Deal.query.filter_by(active=True).all()
    rows = []
    for deal in deals:
        # today_activation: today's game in progress (for the live score).
        # redeemable_activation: yesterday's result, which is what actually
        # unlocks a redeemable code today -- every deal we've checked grants
        # the code the day *after* the qualifying game, not immediately.
        today_activation = DealActivation.query.filter_by(deal_id=deal.id, game_date=today).first()
        redeemable_activation = DealActivation.query.filter_by(deal_id=deal.id, game_date=yesterday).first()
        rows.append((deal, today_activation, redeemable_activation))
    return render_template("index.html", rows=rows, today=today, tomorrow=today + timedelta(days=1))


@bp.route("/scan-now", methods=["POST"])
def scan_now():
    scan_all_active_deals()
    return redirect(url_for("main.index"))
