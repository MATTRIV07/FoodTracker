"""Sends a "deal unlocked" email via Resend (https://resend.com) — a
send-only API key, not a general mailbox credential.

If RESEND_API_KEY or NOTIFY_EMAIL_TO isn't configured, sending is silently
skipped (not an error) so the app works fine before notifications are set up.
"""

import logging

import requests
from flask import current_app

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


def send_deal_triggered(deal, detail):
    api_key = current_app.config.get("RESEND_API_KEY")
    to_email = current_app.config.get("NOTIFY_EMAIL_TO")
    if not api_key or not to_email:
        logger.info("Email notifications not configured, skipping.")
        return

    lines = [f"{deal.restaurant} — {deal.title}", "", deal.description]
    if detail:
        lines += ["", detail]
    if deal.redemption_code:
        lines += ["", f"Code: {deal.redemption_code}"]

    try:
        resp = requests.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": current_app.config["NOTIFY_EMAIL_FROM"],
                "to": [to_email],
                "subject": f"Unlocked: {deal.restaurant} — {deal.title}",
                "text": "\n".join(lines),
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Sent notification email for deal id=%s", deal.id)
    except Exception:
        logger.exception("Failed to send notification email for deal id=%s", deal.id)
