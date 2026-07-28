import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Port 5000 is claimed by macOS's AirPlay Receiver (ControlCenter), which
    # answers with 403 Forbidden instead of failing to bind — use a different
    # default port to avoid that conflict entirely.
    # host="0.0.0.0" listens on all network interfaces, not just loopback,
    # so other devices on the same Wi-Fi (e.g. a phone) can reach it too.
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
