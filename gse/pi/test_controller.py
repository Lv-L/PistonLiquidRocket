"""Run from gse/pi: python test_controller.py"""

import time
from pathlib import Path

import config
from controller import GseController, GseError
from links import MockLink


def connect(pad, vehicle):
    controller = GseController(pad, vehicle)
    controller.connect_arduino("mock")
    controller.connect_esp32(mac="mock")
    return controller


def wait_fire(controller):
    thread = controller.fire_thread
    while thread.is_alive():
        controller.heartbeat()
        thread.join(0.2)


def first(history, command):
    for stamp, seen in history:
        if seen == command:
            return stamp
    raise AssertionError(command + " was not sent")


def test_rejects_bad_code_and_closed_valves():
    pad = MockLink("pad")
    vehicle = MockLink("vehicle")
    controller = connect(pad, vehicle)
    try:
        try:
            controller.arm("0000")
            raise AssertionError("bad arm code was accepted")
        except GseError as exc:
            assert "rejected" in str(exc).lower()
        try:
            controller.set_valve("fill", True)
            raise AssertionError("valve moved while safe")
        except GseError:
            pass
        assert pad.valves["fill"] is False
        assert "8008" not in controller.snapshot()["message"]
    finally:
        controller.close()


def test_fire_opens_mains_after_two_seconds():
    pad = MockLink("pad")
    vehicle = MockLink("vehicle")
    controller = connect(pad, vehicle)
    try:
        controller.arm(config.ARM_CODE)
        controller.start_fire()
        wait_fire(controller)
        relay_on = first(pad.history, "RELAY ON")
        ox_open = first(vehicle.history, "OX OPEN")
        fuel_open = first(vehicle.history, "FUEL OPEN")
        relay_off = first(pad.history, "RELAY OFF")
        assert ox_open - relay_on >= config.FIRE_DELAY_S - 0.05
        assert abs(fuel_open - ox_open) < 0.5
        assert relay_off - relay_on >= config.IGNITOR_MAX_S - 0.15
        assert not any(command.startswith("FILL") or command.startswith("PURGE") for _, command in pad.history)
        snap = controller.snapshot()
        assert snap["phase"] == "complete"
        assert snap["relay"] is False
        assert snap["valves"]["ox"] == "open"
        assert snap["valves"]["fuel"] == "open"
        assert snap["valves"]["fill"] == "closed"
        assert snap["valves"]["purge"] == "closed"
    finally:
        controller.close()


def test_abort_during_wait_keeps_mains_closed():
    pad = MockLink("pad")
    vehicle = MockLink("vehicle")
    controller = connect(pad, vehicle)
    try:
        controller.arm(config.ARM_CODE)
        controller.start_fire()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            controller.heartbeat()
            if any(command == "RELAY ON" for _, command in pad.history):
                break
            time.sleep(0.05)
        else:
            raise AssertionError("ignitor never turned on")
        time.sleep(0.2)
        controller.abort("test abort")
        controller.fire_thread.join(timeout=3)
        assert not any(command == "OX OPEN" for _, command in vehicle.history)
        assert not any(command == "FUEL OPEN" for _, command in vehicle.history)
        snap = controller.snapshot()
        assert snap["armed"] is False
        assert snap["relay"] is False
        assert all(position == "closed" for position in snap["valves"].values())
    finally:
        controller.close()


def test_pages_do_not_contain_the_arm_code():
    root = Path(__file__).resolve().parent
    for name in ("templates/index.html", "static/console.js", "static/console.css"):
        text = (root / name).read_text(encoding="utf-8")
        assert config.ARM_CODE not in text
        assert config.OPERATOR_PASSWORD not in text


if __name__ == "__main__":
    test_rejects_bad_code_and_closed_valves()
    test_abort_during_wait_keeps_mains_closed()
    test_fire_opens_mains_after_two_seconds()
    test_pages_do_not_contain_the_arm_code()
    print("ok")
