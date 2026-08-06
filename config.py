import os
import secrets

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'food_deals.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # A hardcoded fallback here would let anyone forge session/flash cookies
    # on any deploy that forgot to set SECRET_KEY. Generate a random one at
    # boot instead -- sessions here are only used for one-request flash
    # messages, so a value that changes across restarts costs nothing. Set
    # SECRET_KEY explicitly in the environment for any deploy that needs
    # sessions to survive a process restart.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", 300))

    # Base URL used to build unsubscribe links in notification emails. Can't
    # use Flask's url_for(..., _external=True) for that because the scanner
    # runs in a background thread's app context, not a request context.
    SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:5001")

    # Email notifications (sent via https://resend.com) when a deal unlocks.
    # Notifications are skipped (not an error) if these aren't set.
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    NOTIFY_EMAIL_TO = os.environ.get("NOTIFY_EMAIL_TO")
    NOTIFY_EMAIL_FROM = os.environ.get("NOTIFY_EMAIL_FROM", "FoodTracker <onboarding@resend.dev>")
