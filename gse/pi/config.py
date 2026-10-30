"""Local pad-console settings. The arm code is checked only on the Pi."""

import os

HOST = os.environ.get("GSE_HOST", "0.0.0.0")
PORT = int(os.environ.get("GSE_PORT", "8080"))

# Sign-on for the webpage. Change these before the pad is used.
OPERATOR_USER = os.environ.get("GSE_USER", "operator")
OPERATOR_PASSWORD = os.environ.get("GSE_PASSWORD", "pad-login")
ARM_CODE = os.environ.get("GSE_ARM_CODE", "8008")

SECRET_KEY = os.environ.get("GSE_SECRET", "piston-gse-local-console")

# How long an arm stays valid while the operator page is open.
ARM_TIMEOUT_S = float(os.environ.get("GSE_ARM_TIMEOUT", "600"))
# Page polls count as a heartbeat. Lose the page and the pad safes.
HEARTBEAT_TIMEOUT_S = float(os.environ.get("GSE_HEARTBEAT_TIMEOUT", "3"))
# Five bad arm codes, then a short lockout.
ARM_LOCKOUT_S = 30
ARM_MAX_TRIES = 5

# Fire sequence: relay on, wait, then both main valves.
FIRE_DELAY_S = float(os.environ.get("GSE_FIRE_DELAY", "2.0"))
# Relay drops this long after it turns on so a lost command cannot hold the ignitor.
IGNITOR_MAX_S = float(os.environ.get("GSE_IGNITOR_MAX", "4.0"))
RELAY_PULSE_S = 0.3

ARDUINO_PORT = os.environ.get("GSE_ARDUINO_PORT", "/dev/ttyACM0")
ARDUINO_BAUD = 115200
# How often to look for the Uno again after it drops off USB.
ARDUINO_SCAN_S = float(os.environ.get("GSE_ARDUINO_SCAN", "3"))
# Vehicle link. MAC is classic Bluetooth (GSE-VEHICLE). Port is USB bench only.
ESP32_MAC = os.environ.get("GSE_ESP32_MAC", "")
ESP32_PORT = os.environ.get("GSE_ESP32_PORT", "")
ESP32_NAME = "GSE-VEHICLE"

# Firmware closes itself if STATUS polls stop. Keep the poll inside that window.
STATUS_POLL_S = 1.0
SERIAL_TIMEOUT_S = 1.5
UNO_RESET_WAIT_S = 2.0

MOCK = os.environ.get("GSE_MOCK", "0") == "1"
