#!/bin/zsh
# Fluent Lab: toggle a macOS audio recording from a terminal or hotkey.
# Usage: quick-record.sh [speaking|grammar|chunks|compression|interview|reflection|other]
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${FLUENT_LAB_RECORDINGS:-${PROJECT_ROOT}/recordings}"
PURPOSE="${1:-speaking}"
case "${PURPOSE}" in
  speaking|grammar|chunks|compression|interview|reflection|other) ;;
  *) echo "ERROR: invalid purpose '${PURPOSE}'"; exit 2;;
esac
mkdir -p "${ROOT}"
PID_FILE="${ROOT}/.active.pid"
PATH_FILE="${ROOT}/.active.path"
LOG_FILE="${ROOT}/.last-recording.log"
if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" 2>/dev/null; then
    kill -INT "${PID}" 2>/dev/null || true
    sleep 1
    FILE="$(cat "${PATH_FILE}" 2>/dev/null || true)"
    rm -f "${PID_FILE}" "${PATH_FILE}"
    if [[ -n "${FILE}" && -s "${FILE}" ]]; then
      SESSION_DIR="$(dirname "${FILE}")"
      DURATION="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${FILE}" 2>/dev/null || echo 0)"
      python3 - "${SESSION_DIR}" "${DURATION}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

folder = Path(sys.argv[1])
path = folder / "session.json"
session = json.loads(path.read_text(encoding="utf-8"))
session["duration"] = round(float(sys.argv[2] or 0))
session["mediaBytes"] = (folder / "media.m4a").stat().st_size
session["updatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
      echo "SAVED:${FILE}"
    else
      echo "STOPPED: Recording ended, but file may be empty. See ${LOG_FILE}"
    fi
    exit 0
  fi
  rm -f "${PID_FILE}" "${PATH_FILE}"
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: ffmpeg not found. Install with: brew install ffmpeg"
  exit 1
fi
DAY="$(date +%Y-%m-%d)"
CLOCK="$(date +%H%M%S)"
SESSION_ID="${DAY}_${CLOCK}_${PURPOSE}"
DIR="${ROOT}/${DAY}/${SESSION_ID}"
mkdir -p "${DIR}"
OUT="${DIR}/media.m4a"
CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "${DIR}/session.json" <<EOF
{
  "id": "${SESSION_ID}",
  "createdAt": "${CREATED_AT}",
  "updatedAt": "${CREATED_AT}",
  "date": "${DAY}",
  "title": "${PURPOSE} · ${DAY} ${CLOCK}",
  "purpose": "${PURPOSE}",
  "prompt": "",
  "duration": 0,
  "audio": true,
  "source": "hotkey",
  "mime": "audio/mp4",
  "filename": "${DAY}_${CLOCK}_${PURPOSE}.m4a",
  "originalFilename": "${DAY}_${CLOCK}_${PURPOSE}.m4a",
  "mediaFile": "media.m4a",
  "raw": "",
  "polished": "",
  "notes": "",
  "takeaway": "",
  "nextAction": "",
  "errorTags": [],
  "scores": {}
}
EOF
: > "${DIR}/before.txt"
: > "${DIR}/after.txt"
: > "${DIR}/prompt.txt"
cat > "${DIR}/corrections.md" <<EOF
# ${PURPOSE} · ${DAY} ${CLOCK} — corrections & review

Open this session in Fluent Lab to add Before, After, corrections, and reflection.
EOF
# AVFoundation ':default' means the default macOS audio input device.
# -nostdin prevents the background process from exiting on terminal input.
ffmpeg -hide_banner -loglevel warning -nostdin -f avfoundation -i ':default' -vn -ac 1 -c:a aac -b:a 96k -y "${OUT}" </dev/null >"${LOG_FILE}" 2>&1 &
PID=$!
echo "${PID}" > "${PID_FILE}"
echo "${OUT}" > "${PATH_FILE}"
sleep 1
if ! kill -0 "${PID}" 2>/dev/null; then
  rm -f "${PID_FILE}" "${PATH_FILE}"
  rm -f "${OUT}" "${DIR}/session.json" "${DIR}/before.txt" "${DIR}/after.txt" "${DIR}/prompt.txt" "${DIR}/corrections.md"
  rmdir "${DIR}" 2>/dev/null || true
  echo "ERROR: microphone recording could not start. Check macOS Microphone privacy settings; see ${LOG_FILE}"
  tail -n 6 "${LOG_FILE}" 2>/dev/null || true
  exit 1
fi
echo "RECORDING:${OUT}"
