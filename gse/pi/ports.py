"""Find the pad Arduino even when Linux renumbers the USB port."""

import glob
import os
from pathlib import Path


def arduino_port_candidates(preferred="", by_id_dir="/dev/serial/by-id", device_globs=None):
    """Arduino by-id links first, then the configured port, then ACM and USB serial ports."""
    found = []
    seen = set()

    def add(path):
        path = str(path or "").strip()
        if not path or not os.path.exists(path):
            return
        real = os.path.realpath(path)
        if real in seen:
            return
        seen.add(real)
        found.append(path)

    directory = Path(by_id_dir)
    if directory.is_dir():
        for entry in sorted(directory.iterdir()):
            if "arduino" in entry.name.lower():
                add(entry)

    add(preferred)

    for pattern in device_globs if device_globs is not None else ("/dev/ttyACM*", "/dev/ttyUSB*"):
        for path in sorted(glob.glob(pattern)):
            add(path)
    return found
