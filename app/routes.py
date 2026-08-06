import re
import secrets
from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app import db, limiter
from app.models import Deal, DealActivation, Subscriber
from app.scanner import current_game_day, scan_all_active_deals

bp = Blueprint("main", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
@limiter.limit("10 per minute")
def scan_now():
    scan_all_active_deals()
    return redirect(url_for("main.index"))


@bp.route("/subscribe", methods=["POST"])
@limiter.limit("5 per hour")
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if not _EMAIL_RE.match(email):
        flash("That doesn't look like a valid email address.", "error")
        return redirect(url_for("main.index"))

    subscriber = Subscriber(email=email, unsubscribe_token=secrets.token_urlsafe(32))
    db.session.add(subscriber)
    try:
        db.session.commit()
        flash(f"Subscribed — reward notifications will go to {email}.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(f"{email} is already subscribed.", "info")
    return redirect(url_for("main.index"))


@bp.route("/unsubscribe/<token>", methods=["GET"])
@limiter.limit("20 per hour")
def unsubscribe_confirm(token):
    # A bare GET that unsubscribes immediately is a known email-link pitfall:
    # corporate link scanners and mail-client "safe links" prefetchers issue
    # real GET requests to every link in an email before a human ever clicks,
    # silently unsubscribing people who never asked to be. GET here only
    # shows a confirmation page; the actual removal happens on POST below.
    subscriber = Subscriber.query.filter_by(unsubscribe_token=token).first()
    if subscriber is None:
        flash("Unsubscribe link not recognized — you may already be unsubscribed.", "info")
        return redirect(url_for("main.index"))
    return render_template("unsubscribe_confirm.html", subscriber=subscriber, token=token)


@bp.route("/unsubscribe/<token>", methods=["POST"])
@limiter.limit("20 per hour")
def unsubscribe(token):
    subscriber = Subscriber.query.filter_by(unsubscribe_token=token).first()
    if subscriber is None:
        flash("Unsubscribe link not recognized — you may already be unsubscribed.", "info")
        return redirect(url_for("main.index"))
    db.session.delete(subscriber)
    db.session.commit()
    flash(f"{subscriber.email} has been unsubscribed.", "success")
    return redirect(url_for("main.index"))
