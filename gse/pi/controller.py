"""Pad state machine. The fire sequence runs here, not in the browser."""

import threading
import time

import config
from links import LinkError
from ports import arduino_port_candidates


class GseError(Exception):
    pass


VALVES = {
    "fill": ("arduino", "FILL"),
    "purge": ("arduino", "PURGE"),
    "ox": ("esp32", "OX"),
    "fuel": ("esp32", "FUEL"),
}
ACTIVE = ("ignitor", "wait", "valves")


class GseController:
    def __init__(self, arduino, esp32):
        self.arduino = arduino
        self.esp32 = esp32
        self.hw = threading.Lock()
        self.state = threading.Lock()
        self.stop = threading.Event()
        self.abort_event = threading.Event()
        self.armed = False
        self.arm_deadline = 0.0
        self.last_heartbeat = time.monotonic()
        self.phase = "idle"
        self.relay = False
        self.valves = {"fill": False, "purge": False, "ox": False, "fuel": False}
        self.links = {"arduino": False, "esp32": False}
        self.message = ""
        self.events = []
        self.arm_fails = 0
        self.lockout_until = 0.0
        self.sequence_active = False
        self.fire_thread = None
        self.ignitor_on = 0.0
        self._last_poll = 0.0
        self._last_scan = time.monotonic()
        self.supervisor = threading.Thread(target=self._supervise, name="gse-supervisor", daemon=True)
        self.supervisor.start()

    def close(self):
        self.stop.set()
        self.abort_event.set()
        with self.hw:
            self._safe_links()
            with self.state:
                self.armed = False
                self.relay = False
                self.sequence_active = False
                for name in self.valves:
                    self.valves[name] = False
        if self.fire_thread and self.fire_thread.is_alive() and threading.current_thread() is not self.fire_thread:
            self.fire_thread.join(timeout=3)
        if threading.current_thread() is not self.supervisor:
            self.supervisor.join(timeout=2)
        self.arduino.close()
        self.esp32.close()

    def connect_arduino(self, port):
        try:
            with self.hw:
                self.arduino.connect(port, config.ARDUINO_BAUD, config.SERIAL_TIMEOUT_S)
                with self.state:
                    self.links["arduino"] = True
                    self.message = "Arduino connected"
                self._push_arm_if_needed(self.arduino)
                return True
        except GseError:
            raise
        except Exception as exc:
            self._mark_down("arduino")
            raise GseError("Arduino did not connect: " + str(exc)[:160]) from exc

    def reconnect_arduino(self):
        """Open whichever port currently answers as the pad Uno."""
        for port in arduino_port_candidates(config.ARDUINO_PORT):
            if self._claim_arduino(port):
                return True
        self._mark_down("arduino")
        return False

    def _claim_arduino(self, port):
        with self.hw:
            with self.state:
                if self.sequence_active or self.phase in ACTIVE:
                    return False
            try:
                self.arduino.connect(port, config.ARDUINO_BAUD, config.SERIAL_TIMEOUT_S)
                reply = self.arduino.send("PING")
            except Exception:
                self.arduino.close()
                return False
            if reply != "OK PONG":
                self.arduino.close()
                return False
            with self.state:
                self.links["arduino"] = True
                self.message = "Arduino connected"
                self._note("Arduino connected")
            self._push_arm_if_needed(self.arduino)
            return True

    def connect_esp32(self, mac="", port=""):
        try:
            with self.hw:
                self.esp32.connect(
                    mac=mac,
                    port=port,
                    baud=config.ARDUINO_BAUD,
                    timeout=config.SERIAL_TIMEOUT_S,
                )
                with self.state:
                    self.links["esp32"] = True
                    self.message = "ESP32 connected"
                self._push_arm_if_needed(self.esp32)
        except GseError:
            raise
        except Exception as exc:
            self._mark_down("esp32")
            raise GseError("ESP32 did not connect: " + str(exc)[:160]) from exc

    def heartbeat(self):
        with self.state:
            self.last_heartbeat = time.monotonic()

    def arm(self, code):
        now = time.monotonic()
        with self.state:
            if now < self.lockout_until:
                raise GseError("Arming is locked for a few seconds")
            if not self.links["arduino"] and not self.links["esp32"]:
                raise GseError("Connect the Arduino or the ESP32 first")
            if self.sequence_active or self.phase in ACTIVE:
                raise GseError("Fire sequence is running")
            if not _match(code, config.ARM_CODE):
                self.arm_fails += 1
                if self.arm_fails >= config.ARM_MAX_TRIES:
                    self.lockout_until = now + config.ARM_LOCKOUT_S
                    self.arm_fails = 0
                    raise GseError("Arming is locked for a few seconds")
                raise GseError("Arm code rejected")
            self.arm_fails = 0
        with self.hw:
            self._arm_links()
            with self.state:
                self.armed = True
                self.abort_event.clear()
                if self.phase != "complete":
                    self.phase = "idle"
                self.arm_deadline = time.monotonic() + config.ARM_TIMEOUT_S
                self.last_heartbeat = time.monotonic()
                self.message = "Armed"
                self._note("Pad armed")

    def abort(self, reason):
        self.abort_event.set()
        with self.hw:
            self._safe_links()
            with self.state:
                self.armed = False
                self.relay = False
                self.sequence_active = False
                for name in self.valves:
                    self.valves[name] = False
                if self.phase in ACTIVE or self.phase == "complete":
                    self.phase = "aborted"
                self.message = reason
                self._note(reason)

    def set_valve(self, valve, open_valve):
        if valve not in VALVES:
            raise GseError("Unknown valve")
        link_name, word = VALVES[valve]
        with self.hw:
            self._require_manual()
            link = self.arduino if link_name == "arduino" else self.esp32
            if not link.connected():
                raise GseError(link_name + " is not connected")
            command = word + (" OPEN" if open_valve else " CLOSE")
            self._cmd(link, command)
            with self.state:
                self.valves[valve] = open_valve
                self._note(valve + (" open" if open_valve else " closed"))

    def pulse_relay(self):
        with self.hw:
            self._require_manual()
            with self.state:
                if self.phase != "idle" or any(self.valves.values()) or self.relay:
                    raise GseError("Close every valve before the ignitor pulse")
            if not self.arduino.connected():
                raise GseError("Arduino is not connected")
            self._cmd(self.arduino, "RELAY ON")
            with self.state:
                self.relay = True
                self._note("Ignitor pulse")
        time.sleep(config.RELAY_PULSE_S)
        with self.hw:
            if self.abort_event.is_set() or not self.armed:
                return
            self._cmd(self.arduino, "RELAY OFF")
            with self.state:
                self.relay = False

    def start_fire(self):
        with self.state:
            if not self.armed:
                raise GseError("Arm the pad first")
            if not self.links["arduino"] or not self.links["esp32"]:
                raise GseError("Arduino and ESP32 must both be connected")
            if self.sequence_active or (self.fire_thread and self.fire_thread.is_alive()):
                raise GseError("Fire sequence is already running")
            if self.phase != "idle":
                raise GseError("Safe the pad before another sequence")
            if self.relay or any(self.valves.values()):
                raise GseError("Close every valve and drop the relay before firing")
            self.sequence_active = True
            self.abort_event.clear()
            self.phase = "ignitor"
            self.arm_deadline = time.monotonic() + config.ARM_TIMEOUT_S
            self.message = "Fire sequence started"
            self._note("Fire sequence started")
        self.fire_thread = threading.Thread(target=self._run_fire, name="gse-fire", daemon=True)
        self.fire_thread.start()

    def snapshot(self):
        with self.state:
            now = time.monotonic()
            remaining = 0
            if self.armed:
                remaining = max(0, int(self.arm_deadline - now))
            return {
                "authenticated": True,
                "mock": config.MOCK,
                "armed": self.armed,
                "arm_remaining_s": remaining,
                "phase": self.phase,
                "relay": self.relay,
                "valves": {name: ("open" if on else "closed") for name, on in self.valves.items()},
                "links": dict(self.links),
                "message": self.message,
                "events": list(self.events),
                "fire_delay_s": config.FIRE_DELAY_S,
            }

    def _run_fire(self):
        try:
            with self.hw:
                if self.abort_event.is_set():
                    return
                self._cmd(self.arduino, "RELAY ON")
                with self.state:
                    self.relay = True
                    self.ignitor_on = time.monotonic()
                    self.phase = "wait"
                    self._note("Ignitor on")
            if not self._wait(config.FIRE_DELAY_S):
                return
            with self.hw:
                if self.abort_event.is_set():
                    return
                with self.state:
                    self.phase = "valves"
                self._cmd(self.esp32, "OX OPEN")
                self._cmd(self.esp32, "FUEL OPEN")
                with self.state:
                    self.valves["ox"] = True
                    self.valves["fuel"] = True
                    self.phase = "complete"
                    self.message = "Mains open. Abort to close the valves."
                    self._note("Ox and fuel mains open")
            remain = config.IGNITOR_MAX_S - (time.monotonic() - self.ignitor_on)
            if remain > 0 and not self._wait(remain):
                return
            with self.hw:
                if self.abort_event.is_set():
                    return
                self._cmd(self.arduino, "RELAY OFF")
                with self.state:
                    self.relay = False
                    self.phase = "complete"
                    self.message = "Mains open. Abort to close the valves."
                    self._note("Ignitor off")
        except Exception:
            if not self.abort_event.is_set():
                self.abort("Fire sequence stopped")
        finally:
            with self.state:
                self.sequence_active = False

    def _wait(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self.abort_event.is_set() or self.stop.is_set():
                return False
            time.sleep(0.05)
        return not self.abort_event.is_set()

    def _supervise(self):
        while not self.stop.wait(0.2):
            now = time.monotonic()
            self._check_timers()
            if now - self._last_poll >= config.STATUS_POLL_S:
                self._last_poll = now
                if self.hw.acquire(blocking=False):
                    try:
                        self._poll("arduino", self.arduino)
                        self._poll("esp32", self.esp32)
                    finally:
                        self.hw.release()
            self._scan_for_arduino(now)

    def _scan_for_arduino(self, now):
        if now - self._last_scan < config.ARDUINO_SCAN_S:
            return
        with self.state:
            need = not self.links["arduino"] and not self.sequence_active and self.phase not in ACTIVE
        if not need:
            return
        self._last_scan = now
        self.reconnect_arduino()

    def _check_timers(self):
        with self.state:
            if not self.armed:
                return
            now = time.monotonic()
            reason = None
            if now - self.last_heartbeat > config.HEARTBEAT_TIMEOUT_S:
                reason = "Operator page lost. Pad safed."
            elif now > self.arm_deadline and not self.sequence_active:
                reason = "Arm timed out. Pad safed."
        if reason:
            self.abort(reason)

    def _poll(self, name, link):
        if not link.connected():
            with self.state:
                self.links[name] = False
            return
        try:
            line = link.send("STATUS")
        except Exception:
            with self.state:
                was = self.links[name]
                self.links[name] = False
                hot = self.armed or self.relay or any(self.valves.values()) or self.phase in ACTIVE
            if was and hot and not self.abort_event.is_set():
                self._safe_links()
                with self.state:
                    self.armed = False
                    self.relay = False
                    self.abort_event.set()
                    self.sequence_active = False
                    for valve in self.valves:
                        self.valves[valve] = False
                    self.phase = "aborted"
                    self.message = name + " link lost. Pad safed."
                    self._note(self.message)
            return
        self._apply_status(line)

    def _apply_status(self, line):
        fields = {}
        parts = line.split()
        if len(parts) < 2 or parts[0] != "STATUS":
            return
        for item in parts[2:]:
            if "=" in item:
                key, value = item.split("=", 1)
                fields[key] = value
        with self.state:
            if parts[1] == "pad":
                self.links["arduino"] = True
                if "relay" in fields:
                    self.relay = fields["relay"] == "1"
                for name in ("fill", "purge"):
                    if name in fields:
                        self.valves[name] = fields[name] == "OPEN"
            elif parts[1] == "vehicle":
                self.links["esp32"] = True
                for name in ("ox", "fuel"):
                    if name in fields:
                        self.valves[name] = fields[name] == "OPEN"

    def _require_manual(self):
        with self.state:
            if not self.armed:
                raise GseError("Arm the pad first")
            if self.sequence_active or self.phase in ACTIVE:
                raise GseError("Fire sequence is running")

    def _arm_links(self):
        for link in (self.arduino, self.esp32):
            if link.connected():
                self._cmd(link, "ARM")

    def _push_arm_if_needed(self, link):
        with self.state:
            armed = self.armed
        if armed:
            self._cmd(link, "ARM")

    def _safe_links(self):
        for link in (self.arduino, self.esp32):
            try:
                if link.connected():
                    link.send("SAFE")
            except Exception:
                pass

    def _cmd(self, link, line):
        try:
            response = link.send(line)
        except LinkError as exc:
            raise GseError(str(exc)) from exc
        if not response.startswith("OK"):
            raise GseError(response[:120])
        return response

    def _mark_down(self, name):
        with self.state:
            self.links[name] = False

    def _note(self, text):
        self.events.append(text)
        del self.events[:-12]


def _match(got, expected):
    import hmac

    got = got or ""
    if len(got) != len(expected):
        return False
    return hmac.compare_digest(got, expected)
