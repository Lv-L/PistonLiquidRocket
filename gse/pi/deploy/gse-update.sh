#!/bin/bash
# Connect Wi-Fi first. Pull the pad code only after Wi-Fi is up.
set -u

REPO=/home/pad/PistonLiquidRocket
BRANCH=cursor/gse-code
REMOTE=https://github.com/Lv-L/PistonLiquidRocket.git
STAMP=/var/lib/gse/build-info.json
VENV=/home/pad/gse-venv
LOG=/var/log/gse-update.log

mkdir -p /var/lib/gse /var/log
touch "$LOG"
exec >>"$LOG" 2>&1
echo "---- $(date '+%d %b %Y, %H:%M %Z') ----"

wifi_connected() {
  if command -v nmcli >/dev/null 2>&1; then
    nmcli -t -f DEVICE,TYPE,STATE device 2>/dev/null | grep -q '^wlan[^:]*:wifi:connected'
    return $?
  fi
  ip -4 addr show wlan0 2>/dev/null | grep -q 'inet '
}

echo "Turning Wi-Fi on before git"
rfkill unblock wifi || true
if command -v nmcli >/dev/null 2>&1; then
  nmcli radio wifi on || true
  nmcli networking on || true
  nmcli device connect wlan0 || true
  nmcli -t -f NAME,TYPE connection show 2>/dev/null | while IFS=: read -r name typ; do
    if [ "$typ" = "802-11-wireless" ] && [ -n "$name" ]; then
      nmcli connection up "$name" || true
    fi
  done
fi

connected=0
for _ in $(seq 1 30); do
  if wifi_connected; then
    connected=1
    break
  fi
  sleep 2
done

if [ "$connected" -ne 1 ]; then
  echo "Wi-Fi did not connect. Skipping git pull."
  exit 0
fi

echo "Wi-Fi is connected. Waiting for DNS."
resolved=0
for _ in $(seq 1 15); do
  if getent hosts github.com >/dev/null 2>&1; then
    resolved=1
    break
  fi
  sleep 2
done
if [ "$resolved" -ne 1 ]; then
  echo "github.com did not resolve. Skipping git pull."
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is not installed. Skipping git pull."
  exit 0
fi

as_pad() {
  runuser -u pad -- "$@"
}

if [ ! -d "$REPO/.git" ]; then
  echo "Cloning $BRANCH"
  as_pad git clone --branch "$BRANCH" "$REMOTE" "$REPO" || {
    echo "Clone failed"
    exit 0
  }
else
  echo "Pulling $BRANCH"
  as_pad git -C "$REPO" fetch origin "$BRANCH" || { echo "Fetch failed"; exit 0; }
  as_pad git -C "$REPO" checkout "$BRANCH" || { echo "Checkout failed"; exit 0; }
  as_pad git -C "$REPO" pull --ff-only origin "$BRANCH" || { echo "Pull failed"; exit 0; }
fi

if [ ! -x "$VENV/bin/pip" ]; then
  as_pad python3 -m venv "$VENV" || { echo "venv failed"; exit 0; }
fi
as_pad "$VENV/bin/pip" install -q -r "$REPO/gse/pi/requirements.txt" || echo "Dependency install failed"

count=$(as_pad git -C "$REPO" rev-list --count HEAD)
short=$(as_pad git -C "$REPO" rev-parse --short HEAD)
pulled=$(date '+%d %b %Y, %H:%M %Z')
printf '{"version":"v%s · %s","pulled":"%s"}\n' "$count" "$short" "$pulled" > "$STAMP"
chown pad:pad "$STAMP"
if [ -f "$REPO/gse/pi/deploy/gse-update.sh" ]; then
  install -m 755 "$REPO/gse/pi/deploy/gse-update.sh" /usr/local/sbin/gse-update
fi
echo "Updated to v${count} · ${short}"
