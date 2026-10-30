"""GSE console for the Raspberry Pi 3B.

Sign on, arm, then use Test checkout or Fire sequence.
Run on the Pi from this directory:

    pip install -r requirements.txt
    python3 app.py

The operator opens http://<pi>:8080 over the Ethernet run.
Hardware links are set in config.py. GSE_MOCK=1 runs the page with no boards attached.
"""

import os
import hmac
from functools import wraps

import buildinfo
import config
from controller import GseController, GseError
from flask import Flask, jsonify, render_template, request, session
from links import EspLink, MockLink, SerialLink

if config.MOCK:
    controller = GseController(MockLink("pad"), MockLink("vehicle"))
else:
    controller = GseController(
        SerialLink(config.UNO_RESET_WAIT_S),
        EspLink(config.UNO_RESET_WAIT_S),
    )

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict")


def _signed_on():
    return session.get("user") == config.OPERATOR_USER


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _signed_on():
            return jsonify(ok=False, error="Sign on required"), 401
        controller.heartbeat()
        return fn(*args, **kwargs)

    return wrapper


def _match(got, expected):
    got = got or ""
    if len(got) != len(expected):
        return False
    return hmac.compare_digest(got, expected)


def _call(fn):
    try:
        fn()
    except GseError as exc:
        body = controller.snapshot()
        body.update(ok=False, error=str(exc))
        return jsonify(buildinfo.apply(body)), 400
    body = controller.snapshot()
    body.update(ok=True, error="")
    return jsonify(buildinfo.apply(body))


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def state():
    if not _signed_on():
        return jsonify(buildinfo.apply({"authenticated": False, "mock": config.MOCK}))
    controller.heartbeat()
    body = controller.snapshot()
    body["error"] = ""
    return jsonify(buildinfo.apply(body))


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    user_ok = _match(str(data.get("user", "")), config.OPERATOR_USER)
    pass_ok = _match(str(data.get("password", "")), config.OPERATOR_PASSWORD)
    if not (user_ok and pass_ok):
        return jsonify(ok=False, error="Sign on rejected"), 401
    session["user"] = config.OPERATOR_USER
    controller.heartbeat()
    return jsonify(ok=True)


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.post("/api/arm")
@login_required
def arm():
    data = request.get_json(silent=True) or {}
    return _call(lambda: controller.arm(str(data.get("code", ""))))


@app.post("/api/abort")
@login_required
def abort():
    return _call(lambda: controller.abort("Aborted. Valves closed, ignitor off."))


@app.post("/api/valve")
@login_required
def valve():
    data = request.get_json(silent=True) or {}
    name = str(data.get("valve", ""))
    position = str(data.get("position", ""))
    if position not in ("open", "close"):
        return jsonify(ok=False, error="Unknown position"), 400
    return _call(lambda: controller.set_valve(name, position == "open"))


@app.post("/api/relay")
@login_required
def relay():
    return _call(controller.pulse_relay)


@app.post("/api/fire")
@login_required
def fire():
    return _call(controller.start_fire)


@app.post("/api/connect")
@login_required
def connect():
    data = request.get_json(silent=True) or {}
    target = str(data.get("target", ""))

    def run():
        if target == "arduino":
            port = str(data.get("port") or config.ARDUINO_PORT)
            controller.connect_arduino(port)
        elif target == "esp32":
            controller.connect_esp32(
                mac=str(data.get("mac") or config.ESP32_MAC),
                port=str(data.get("port") or ""),
            )
        else:
            raise GseError("Unknown controller")

    return _call(run)


def _boot_links():
    if config.MOCK:
        try:
            controller.connect_arduino("mock")
            controller.connect_esp32(mac="mock")
        except GseError:
            pass
        return
    try:
        controller.reconnect_arduino()
    except Exception:
        pass
    if config.ESP32_MAC or config.ESP32_PORT:
        try:
            controller.connect_esp32(mac=config.ESP32_MAC, port=config.ESP32_PORT)
        except Exception:
            pass


if __name__ == "__main__":
    _boot_links()
    app.run(host=config.HOST, port=config.PORT, threaded=True, use_reloader=False)
else:
    # Imported by a test client. Still bring mock links up when asked.
    if os.environ.get("GSE_BOOT", "1") == "1":
        _boot_links()
