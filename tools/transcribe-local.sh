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
TMP="$(mktemp /tmp/fluent-lab-whisper-XXXXXXXX)"
trap 'rm -f "${TMP}"' EXIT
ffmpeg -hide_banner -loglevel error -y -i "${FILE}" -ar 16000 -ac 1 -c:a pcm_s16le -f wav "${TMP}"
BASE="${FILE%.*}"
"${BIN}" -m "${MODEL}" -f "${TMP}" -otxt -of "${BASE}" -l en
printf 'TRANSCRIPT:%s.txt\n' "${BASE}"
