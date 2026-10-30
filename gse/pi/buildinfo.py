"""Version shown on the pad screen.

The boot script writes /var/lib/gse/build-info.json after a successful pull.
A developer checkout with no stamp falls back to the local git revision.
"""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAMP = Path(os.environ.get("GSE_BUILD_INFO", "/var/lib/gse/build-info.json"))


def apply(body):
    body.update(read_build())
    return body


def read_build():
    stamped = _read_stamp()
    if stamped:
        return stamped
    version = _git_version()
    return {"version": version or "unknown", "pulled": "not yet"}


def _read_stamp():
    if not STAMP.is_file():
        return None
    try:
        data = json.loads(STAMP.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    version = str(data.get("version") or "").strip()
    pulled = str(data.get("pulled") or "").strip()
    if not version:
        return None
    return {"version": version, "pulled": pulled or "not yet"}


def _git_version():
    try:
        count = _git("rev-list", "--count", "HEAD")
        short = _git("rev-parse", "--short", "HEAD")
    except (OSError, subprocess.SubprocessError):
        return ""
    if not count or not short:
        return ""
    return "v%s · %s" % (count, short)


def _git(*args):
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args],
        text=True,
        timeout=3,
        stderr=subprocess.DEVNULL,
    ).strip()
