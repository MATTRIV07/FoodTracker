from flask import Blueprint, redirect, render_template, url_for

from app.models import Deal, DealActivation
from app.scanner import current_game_day, scan_all_active_deals

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    today = current_game_day()
    deals = Deal.query.filter_by(active=True).all()
    rows = []
    for deal in deals:
        activation = DealActivation.query.filter_by(deal_id=deal.id, game_date=today).first()
        rows.append((deal, activation))
    return render_template("index.html", rows=rows, today=today)


@bp.route("/scan-now", methods=["POST"])
def scan_now():
    scan_all_active_deals()
    return redirect(url_for("main.index"))
