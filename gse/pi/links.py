"""USB and Bluetooth command links. One command, one reply line."""

import socket
import time


class LinkError(Exception):
    pass


class SerialLink:
    """USB serial. Opening the port resets an Uno, so connect waits out the bootloader."""

    def __init__(self, reset_wait):
        self.reset_wait = reset_wait
        self.ser = None

    def connected(self):
        return self.ser is not None and self.ser.is_open

    def connect(self, port, baud, timeout):
        self.close()
        import serial

        ser = serial.Serial(port, baud, timeout=timeout, exclusive=True)
        if self.reset_wait:
            time.sleep(self.reset_wait)
        ser.reset_input_buffer()
        self.ser = ser

    def close(self):
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None

    def send(self, line):
        if not self.connected():
            raise LinkError("serial link is down")
        self.ser.write((line.strip() + "\n").encode("ascii"))
        self.ser.flush()
        raw = self.ser.readline()
        if not raw:
            raise LinkError("serial timeout")
        return raw.decode("ascii", "replace").strip()


class BluetoothLink:
    """Classic Bluetooth RFCOMM to the vehicle ESP32 (channel 1, name GSE-VEHICLE)."""

    def __init__(self):
        self.sock = None
        self.buf = b""

    def connected(self):
        return self.sock is not None

    def connect(self, mac):
        self.close()
        mac = (mac or "").strip()
        if not mac:
            raise LinkError("ESP32 Bluetooth address is not set")
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(12)
        try:
            sock.connect((mac, 1))
        except Exception:
            sock.close()
            raise
        sock.settimeout(1.5)
        self.sock = sock
        self.buf = b""

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.buf = b""

    def send(self, line):
        if not self.connected():
            raise LinkError("Bluetooth link is down")
        try:
            self.sock.sendall((line.strip() + "\n").encode("ascii"))
            return self._readline()
        except LinkError:
            raise
        except Exception as exc:
            raise LinkError("Bluetooth link failed") from exc

    def _readline(self):
        while b"\n" not in self.buf:
            try:
                chunk = self.sock.recv(128)
            except socket.timeout as exc:
                raise LinkError("Bluetooth timeout") from exc
            if not chunk:
                raise LinkError("ESP32 closed Bluetooth")
            self.buf += chunk
            if len(self.buf) > 512:
                self.buf = b""
                raise LinkError("ESP32 response too long")
        raw, self.buf = self.buf.split(b"\n", 1)
        return raw.decode("ascii", "replace").strip()


class EspLink:
    """Vehicle link: Bluetooth in use, USB serial only for a bench checkout."""

    def __init__(self, reset_wait):
        self.bluetooth = BluetoothLink()
        self.serial = SerialLink(reset_wait)
        self.mode = None

    def connected(self):
        if self.mode == "bluetooth":
            return self.bluetooth.connected()
        if self.mode == "serial":
            return self.serial.connected()
        return False

    def connect(self, mac="", port="", baud=115200, timeout=1.5):
        self.close()
        if port:
            self.serial.connect(port, baud, timeout)
            self.mode = "serial"
            return
        if mac:
            self.bluetooth.connect(mac)
            self.mode = "bluetooth"
            return
        raise LinkError("Set the ESP32 Bluetooth address, or a USB port for bench checkout")

    def close(self):
        self.bluetooth.close()
        self.serial.close()
        self.mode = None

    def send(self, line):
        if self.mode == "bluetooth":
            return self.bluetooth.send(line)
        if self.mode == "serial":
            return self.serial.send(line)
        raise LinkError("ESP32 link is down")


class MockLink:
    """Same command replies as the firmware, with no hardware attached."""

    def __init__(self, kind):
        self.kind = kind
        self.is_up = False
        self.armed = False
        self.relay = False
        self.valves = {}
        self.history = []
        if kind == "pad":
            self.valves = {"fill": False, "purge": False}
        else:
            self.valves = {"ox": False, "fuel": False}

    def connected(self):
        return self.is_up

    def connect(self, *_args, **_kwargs):
        self.is_up = True
        self._safe()

    def close(self):
        self._safe()
        self.is_up = False

    def send(self, line):
        if not self.is_up:
            raise LinkError("mock link is down")
        cmd = " ".join(line.strip().upper().split())
        self.history.append((time.monotonic(), cmd))
        if cmd == "PING":
            return "OK PONG"
        if cmd == "SAFE":
            self._safe()
            return "OK SAFE"
        if cmd == "ARM":
            self.armed = True
            return "OK ARM"
        if cmd == "STATUS":
            return self._status()
        if cmd == "RELAY ON":
            if self.kind != "pad":
                return "ERR UNKNOWN"
            if not self.armed:
                return "ERR DISARMED"
            self.relay = True
            return "OK RELAY ON"
        if cmd == "RELAY OFF":
            if self.kind != "pad":
                return "ERR UNKNOWN"
            self.relay = False
            return "OK RELAY OFF"
        parts = cmd.split()
        if len(parts) == 2 and parts[1] in ("OPEN", "CLOSE"):
            name = parts[0].lower()
            if name not in self.valves:
                return "ERR UNKNOWN"
            if parts[1] == "OPEN" and not self.armed:
                return "ERR DISARMED"
            self.valves[name] = parts[1] == "OPEN"
            return "OK " + cmd
        return "ERR UNKNOWN"

    def _safe(self):
        self.armed = False
        self.relay = False
        for name in self.valves:
            self.valves[name] = False

    def _status(self):
        if self.kind == "pad":
            return "STATUS pad armed={0} relay={1} fill={2} purge={3}".format(
                "1" if self.armed else "0",
                "1" if self.relay else "0",
                "OPEN" if self.valves["fill"] else "CLOSED",
                "OPEN" if self.valves["purge"] else "CLOSED",
            )
        return "STATUS vehicle armed={0} ox={1} fuel={2}".format(
            "1" if self.armed else "0",
            "OPEN" if self.valves["ox"] else "CLOSED",
            "OPEN" if self.valves["fuel"] else "CLOSED",
        )
