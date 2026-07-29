"""Sends a "deal unlocked" email via Resend (https://resend.com) — a
send-only API key, not a general mailbox credential.

Recipients are the optional NOTIFY_EMAIL_TO env var (the site owner's
always-on address, no unsubscribe link) plus every app.models.Subscriber
added via the site's /subscribe form (each gets a personalized unsubscribe
link). If RESEND_API_KEY isn't set, or there are no recipients at all,
sending is silently skipped (not an error).
"""

import logging

import requests
from flask import current_app

from app.models import Subscriber

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def _recipients():
    """[(email, unsubscribe_token_or_None), ...], deduped case-insensitively."""
    seen = set()
    recipients = []

    owner_email = current_app.config.get("NOTIFY_EMAIL_TO")
    if owner_email:
        seen.add(owner_email.lower())
        recipients.append((owner_email, None))

    for subscriber in Subscriber.query.all():
        if subscriber.email.lower() in seen:
            continue
        seen.add(subscriber.email.lower())
        recipients.append((subscriber.email, subscriber.unsubscribe_token))

    return recipients


def send_deal_triggered(deal, detail):
    api_key = current_app.config.get("RESEND_API_KEY")
    recipients = _recipients()
    if not api_key or not recipients:
        logger.info("Email notifications not configured, skipping.")
        return

    lines = [f"{deal.restaurant} — {deal.title}", "", deal.description]
    if detail:
        lines += ["", detail]
    if deal.redemption_code:
        lines += ["", f"Code: {deal.redemption_code}"]

    site_url = current_app.config["SITE_URL"].rstrip("/")

    # Sent individually (not one email with multiple "to" addresses) so
    # recipients don't see each other's addresses, each gets their own
    # unsubscribe link, and one bad address can't block the rest.
    for email, token in recipients:
        body_lines = list(lines)
        if token:
            body_lines += ["", f"Unsubscribe: {site_url}/unsubscribe/{token}"]
        try:
            resp = requests.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "from": current_app.config["NOTIFY_EMAIL_FROM"],
                    "to": [email],
                    "subject": f"Unlocked: {deal.restaurant} — {deal.title}",
                    "text": "\n".join(body_lines),
                },
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("Sent notification email for deal id=%s to %s", deal.id, email)
        except Exception:
            logger.exception("Failed to send notification email for deal id=%s to %s", deal.id, email)
