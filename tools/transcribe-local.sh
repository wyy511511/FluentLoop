#!/bin/zsh
# Optional, fully local transcription using whisper.cpp.
# Usage: ./tools/transcribe-local.sh "/path/to/recording.m4a"
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"
FILE="${1:-}"
if [[ -z "${FILE}" || ! -f "${FILE}" ]]; then
  echo "Usage: $0 /path/to/recording.m4a"; exit 2
fi
MODEL="${WHISPER_MODEL:-${HOME}/whisper.cpp/models/ggml-medium.en.bin}"
if [[ ! -f "${MODEL}" ]]; then
  echo "Model not found: ${MODEL}. Set WHISPER_MODEL=/path/to/ggml-model.bin"
  exit 1
fi
BIN="$(command -v whisper-cli || true)"
if [[ -z "${BIN}" && -x "${HOME}/whisper.cpp/build/bin/whisper-cli" ]]; then
  BIN="${HOME}/whisper.cpp/build/bin/whisper-cli"
fi
if [[ -z "${BIN}" ]]; then
  echo "whisper-cli not found. Install/build whisper.cpp first."
  exit 1
fi
WORK="$(mktemp -d /tmp/fluent-lab-whisper-XXXXXXXX)"
trap 'rm -rf "${WORK}"' EXIT
WAV="${WORK}/audio.wav"
OUT_BASE="${WORK}/transcript"
ffmpeg -hide_banner -loglevel error -y -i "${FILE}" -ar 16000 -ac 1 -c:a pcm_s16le -f wav "${WAV}"
if ! "${BIN}" -m "${MODEL}" -f "${WAV}" -otxt -of "${OUT_BASE}" -l en; then
  echo "GPU transcription failed; retrying on CPU..." >&2
  "${BIN}" -m "${MODEL}" -f "${WAV}" -otxt -of "${OUT_BASE}" -l en -ng
fi
SESSION_DIR="$(dirname "${FILE}")"
if [[ -f "${SESSION_DIR}/session.json" ]]; then
  OUTPUT="${SESSION_DIR}/before.txt"
else
  OUTPUT="${FILE%.*}.txt"
fi
cp "${OUT_BASE}.txt" "${OUTPUT}"
printf 'TRANSCRIPT:%s\n' "${OUTPUT}"
