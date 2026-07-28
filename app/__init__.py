import atexit
import os
from datetime import datetime

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()


def create_app(start_background_scanner=True):
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)

    from app.routes import bp
    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()

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
