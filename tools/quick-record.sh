#!/bin/zsh
# Fluent Lab: toggle a macOS audio recording from a terminal or hotkey.
# Usage: quick-record.sh [speaking|grammar|chunks|compression|interview|reflection|other]
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"
ROOT="${FLUENT_LAB_RECORDINGS:-${HOME}/Documents/FluentLab/recordings}"
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
DIR="${ROOT}/${DAY}/${PURPOSE}"
mkdir -p "${DIR}"
OUT="${DIR}/${DAY}_${CLOCK}_${PURPOSE}.m4a"
# AVFoundation ':default' means the default macOS audio input device.
# -nostdin prevents the background process from exiting on terminal input.
ffmpeg -hide_banner -loglevel warning -nostdin -f avfoundation -i ':default' -vn -ac 1 -c:a aac -b:a 96k -y "${OUT}" </dev/null >"${LOG_FILE}" 2>&1 &
PID=$!
echo "${PID}" > "${PID_FILE}"
echo "${OUT}" > "${PATH_FILE}"
sleep 1
if ! kill -0 "${PID}" 2>/dev/null; then
  rm -f "${PID_FILE}" "${PATH_FILE}"
  echo "ERROR: microphone recording could not start. Check macOS Microphone privacy settings; see ${LOG_FILE}"
  tail -n 6 "${LOG_FILE}" 2>/dev/null || true
  exit 1
fi
echo "RECORDING:${OUT}"
