import atexit
import logging
import os
from datetime import datetime

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
# In-memory storage is fine as long as we stay on a single gunicorn worker
# (see render.yaml's --workers 1) -- each worker would otherwise track
# limits separately, undermining the limit. Set explicitly to silence
# Flask-Limiter's "no storage configured" warning -- this is a deliberate
# choice, not an oversight.
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

logger = logging.getLogger(__name__)


def _ensure_schema():
    """db.create_all() only creates tables that don't exist yet -- it never
    ALTERs an existing table to add a new column. Deploying a model change
    (e.g. a new Deal/DealActivation column) against a database that survived
    from a previous deploy would otherwise leave the live table missing that
    column, and every query touching it starts raising OperationalError. If
    that's happened, drop and recreate everything rather than 500 on every
    request -- daily scan data and Team/Deal rows self-repopulate from seed.py
    and the next scan, but this does mean Subscriber rows don't survive a
    deploy that changes the schema.
    """
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        live_columns = {col["name"] for col in inspector.get_columns(table.name)}
        expected_columns = {col.name for col in table.columns}
        missing = expected_columns - live_columns
        if missing:
            logger.warning(
                "Schema drift on table=%s missing=%s -- dropping and recreating.",
                table.name,
                missing,
            )
            db.drop_all()
            break
    db.create_all()


def _set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # No inline scripts/styles and no external resources anywhere in the
    # templates (checked 2026-08-05) -- default-src 'self' covers everything.
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    # Only meaningful over HTTPS (which is how Render serves this), and
    # harmless to send otherwise -- browsers ignore it on plain HTTP.
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


def create_app(start_background_scanner=True):
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    limiter.init_app(app)
    app.after_request(_set_security_headers)

    from app.routes import bp
    app.register_blueprint(bp)

    with app.app_context():
        _ensure_schema()

    if start_background_scanner:
        # Under `flask run --debug`, Werkzeug's reloader loads this module twice
        # (a monitor process, then a child with WERKZEUG_RUN_MAIN=true). Only
        # start the scheduler in the process that actually serves requests, so
        # dev runs don't end up with two scanners polling the API in parallel.
        running_as_reloaded_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
        if running_as_reloaded_child or not app.debug:
            _start_scheduler(app)

    return app


def _start_scheduler(app):
    from app.scanner import scan_all_active_deals

    scheduler = BackgroundScheduler(daemon=True)

    def job():
        with app.app_context():
            scan_all_active_deals()

    scheduler.add_job(
        job,
        "interval",
        seconds=app.config["SCAN_INTERVAL_SECONDS"],
        next_run_time=datetime.now(),
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
