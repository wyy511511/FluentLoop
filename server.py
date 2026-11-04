#!/usr/bin/env python3
"""Fluent Lab local web server and human-readable recording archive.

The browser keeps an IndexedDB cache for a responsive UI. This server is the
durable layer: every session is written under recordings/YYYY-MM-DD/<id>/.
It intentionally uses only Python's standard library.
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


PROJECT_ROOT = Path(__file__).resolve().parent
RECORDINGS_ROOT = Path(
    os.environ.get("FLUENT_LAB_RECORDINGS", str(PROJECT_ROOT / "recordings"))
).expanduser().resolve()
HOST = os.environ.get("FLUENT_LAB_HOST", "127.0.0.1")
PORT = int(os.environ.get("FLUENT_LAB_PORT", "8765"))

SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MEDIA_EXTENSIONS = {".aac", ".m4a", ".mov", ".mp3", ".mp4", ".ogg", ".wav", ".webm"}
MIME_EXTENSIONS = {
    "audio/aac": ".aac",
    "audio/mp4": ".m4a",
    "video/mp4": ".mp4",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/webm": ".webm",
    "video/webm": ".webm",
}
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_MEDIA_BYTES = 8 * 1024 * 1024 * 1024
ARCHIVE_LOCK = threading.RLock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{threading.get_ident()}")
    with temp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def write_text(path: Path, value: object) -> None:
    text = str(value or "")
    if text and not text.endswith("\n"):
        text += "\n"
    atomic_write(path, text.encode("utf-8"))


def valid_session_id(value: str) -> str:
    if not SESSION_ID_RE.fullmatch(value):
        raise ValueError("invalid session id")
    return value


def valid_date(value: object) -> str:
    date = str(value or "")
    if not DATE_RE.fullmatch(date):
        raise ValueError("invalid session date")
    datetime.strptime(date, "%Y-%m-%d")
    return date


def session_dirs() -> list[Path]:
    if not RECORDINGS_ROOT.exists():
        return []
    results: list[Path] = []
    for date_dir in RECORDINGS_ROOT.iterdir():
        if not date_dir.is_dir() or not DATE_RE.fullmatch(date_dir.name):
            continue
        for item in date_dir.iterdir():
            if item.is_dir() and (item / "session.json").is_file():
                results.append(item)
    return results


def find_session_dir(session_id: str) -> Path | None:
    valid_session_id(session_id)
    for item in session_dirs():
        if item.name == session_id:
            return item
    return None


def session_dir_for(date: str, session_id: str) -> Path:
    return RECORDINGS_ROOT / valid_date(date) / valid_session_id(session_id)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def read_text_if_present(path: Path, fallback: object = "") -> str:
    try:
        return path.read_text(encoding="utf-8").rstrip("\n")
    except OSError:
        return str(fallback or "")


def media_path_for(folder: Path, session: dict | None = None) -> Path | None:
    if session:
        media_file = str(session.get("mediaFile") or "")
        candidate = folder / Path(media_file).name
        if media_file and candidate.is_file() and candidate.suffix.lower() in MEDIA_EXTENSIONS:
            return candidate
    for candidate in sorted(folder.iterdir() if folder.exists() else []):
        if candidate.is_file() and candidate.suffix.lower() in MEDIA_EXTENSIONS:
            return candidate
    return None


def read_session(folder: Path) -> dict:
    session = read_json(folder / "session.json")
    if not session:
        return {}
    # These plain-text files are deliberately editable outside Fluent Lab.
    session["raw"] = read_text_if_present(folder / "before.txt", session.get("raw"))
    session["polished"] = read_text_if_present(folder / "after.txt", session.get("polished"))
    media = media_path_for(folder, session)
    if media:
        session["audio"] = True
        session["mediaFile"] = media.name
        session["mediaBytes"] = media.stat().st_size
        if not session.get("mime"):
            session["mime"] = mimetypes.guess_type(media.name)[0] or "application/octet-stream"
    else:
        session["audio"] = False
        session.pop("mediaFile", None)
        session.pop("mediaBytes", None)
    session["archivePath"] = str(folder.relative_to(PROJECT_ROOT)) if folder.is_relative_to(PROJECT_ROOT) else str(folder)
    return session


def scan_sessions() -> list[dict]:
    sessions = [read_session(folder) for folder in session_dirs()]
    sessions = [session for session in sessions if session.get("id")]
    sessions.sort(key=lambda item: str(item.get("createdAt") or item.get("date") or ""), reverse=True)
    return sessions


def subtree_session_ids(root_id: str) -> list[str]:
    """Return a parent before all of its descendants, guarding against cycles."""
    sessions = scan_sessions()
    children: dict[str, list[str]] = {}
    for session in sessions:
        parent_id = session.get("parentId")
        session_id = session.get("id")
        if parent_id and session_id:
            children.setdefault(str(parent_id), []).append(str(session_id))
    result: list[str] = []
    seen = {root_id}
    frontier = [root_id]
    while frontier:
        current = frontier.pop(0)
        result.append(current)
        for child_id in children.get(current, []):
            if child_id not in seen:
                seen.add(child_id)
                frontier.append(child_id)
    return result


def rebuild_index() -> list[dict]:
    sessions = scan_sessions()
    summaries = []
    for session in sessions:
        summaries.append(
            {
                "id": session.get("id"),
                "date": session.get("date"),
                "createdAt": session.get("createdAt"),
                "updatedAt": session.get("updatedAt"),
                "title": session.get("title"),
                "purpose": session.get("purpose"),
                "duration": session.get("duration", 0),
                "audio": bool(session.get("audio")),
                "parentId": session.get("parentId"),
                "rootId": session.get("rootId") or session.get("id"),
                "takeNumber": session.get("takeNumber", 1),
                "repeatDepth": session.get("repeatDepth", 0),
                "mediaFile": session.get("mediaFile"),
                "archivePath": session.get("archivePath"),
            }
        )
    payload = {"version": 1, "updatedAt": utc_now(), "count": len(summaries), "sessions": summaries}
    atomic_write(RECORDINGS_ROOT / "index.json", (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return sessions


def render_corrections(session: dict) -> str:
    tags = session.get("errorTags") or []
    scores = session.get("scores") or {}
    lines = [
        f"# {session.get('title') or 'Untitled session'} — corrections & review",
        "",
        f"- Date: {session.get('date') or ''}",
        f"- Purpose: {session.get('purpose') or ''}",
        f"- Duration: {session.get('duration') or 0} seconds",
        f"- Take: {session.get('takeNumber') or 1}",
        f"- Parent session: {session.get('parentId') or 'None'}",
        f"- Root session: {session.get('rootId') or session.get('id') or ''}",
        "",
        "## Prompt",
        "",
        str(session.get("prompt") or ""),
        "",
        "## Error tags",
        "",
        *(f"- {tag}" for tag in tags),
        "" if tags else "- None yet",
        "",
        "## Biggest language issue",
        "",
        str(session.get("notes") or ""),
        "",
        "## Better / more natural expression",
        "",
        str(session.get("takeaway") or ""),
        "",
        "## Next action",
        "",
        str(session.get("nextAction") or ""),
        "",
        "## Self scores (1–5)",
        "",
    ]
    if scores:
        lines.extend(f"- {key}: {value}" for key, value in scores.items())
    else:
        lines.append("- None yet")
    return "\n".join(lines).rstrip() + "\n"


def write_session(incoming: dict, session_id: str) -> dict:
    if not isinstance(incoming, dict):
        raise ValueError("session must be an object")
    valid_session_id(session_id)
    if incoming.get("id") not in (None, "", session_id):
        raise ValueError("session id mismatch")
    date = valid_date(incoming.get("date"))
    existing_dir = find_session_dir(session_id)
    target_dir = session_dir_for(date, session_id)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if existing_dir and existing_dir != target_dir:
        if target_dir.exists():
            raise ValueError("target session directory already exists")
        shutil.move(str(existing_dir), str(target_dir))
    target_dir.mkdir(parents=True, exist_ok=True)

    existing = read_json(target_dir / "session.json")
    session = dict(existing)
    session.update(incoming)
    session["id"] = session_id
    session["date"] = date
    session.setdefault("parentId", None)
    session.setdefault("rootId", session_id)
    session.setdefault("takeNumber", 1)
    session.setdefault("repeatDepth", 0)
    session.setdefault("createdAt", utc_now())
    session["updatedAt"] = str(incoming.get("updatedAt") or utc_now())
    session["archivedAt"] = utc_now()
    session["archivePath"] = str(target_dir.relative_to(PROJECT_ROOT)) if target_dir.is_relative_to(PROJECT_ROOT) else str(target_dir)
    media = media_path_for(target_dir, session)
    if media:
        session["audio"] = True
        session["mediaFile"] = media.name
        session["mediaBytes"] = media.stat().st_size

    atomic_write(
        target_dir / "session.json",
        (json.dumps(session, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    )
    write_text(target_dir / "before.txt", session.get("raw"))
    write_text(target_dir / "after.txt", session.get("polished"))
    write_text(target_dir / "prompt.txt", session.get("prompt"))
    atomic_write(target_dir / "corrections.md", render_corrections(session).encode("utf-8"))
    rebuild_index()
    return read_session(target_dir)


def safe_original_name(value: str) -> str:
    name = Path(unquote(value or "")).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return name[:180]


def choose_media_extension(filename: str, content_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in MEDIA_EXTENSIONS:
        return suffix
    mime = content_type.split(";", 1)[0].strip().lower()
    return MIME_EXTENSIONS.get(mime, ".webm")


class FluentLabHandler(SimpleHTTPRequestHandler):
    server_version = "FluentLab/2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def _send_json(self, value: object, status: int = HTTPStatus.OK) -> None:
        body = (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json({"ok": False, "error": message}, status)

    def _read_body(self, limit: int) -> bytes:
        length = self._content_length(limit)
        return self.rfile.read(length)

    def _content_length(self, limit: int) -> int:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > limit:
            raise ValueError("request body is too large")
        return length

    def _api_parts(self, path: str) -> list[str]:
        return [part for part in path.split("/") if part]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            RECORDINGS_ROOT.mkdir(parents=True, exist_ok=True)
            self._send_json(
                {
                    "ok": True,
                    "archiveRoot": str(RECORDINGS_ROOT),
                    "sessionCount": len(session_dirs()),
                    "format": "recordings/YYYY-MM-DD/<session-id>",
                }
            )
            return
        if parsed.path == "/api/sessions":
            with ARCHIVE_LOCK:
                self._send_json({"ok": True, "sessions": rebuild_index()})
            return
        parts = self._api_parts(parsed.path)
        if len(parts) == 4 and parts[:2] == ["api", "sessions"] and parts[3] == "audio":
            try:
                folder = find_session_dir(parts[2])
                session = read_session(folder) if folder else {}
                media = media_path_for(folder, session) if folder else None
                if not media:
                    self._send_error_json(HTTPStatus.NOT_FOUND, "recording media not found")
                    return
                self._send_media(media)
            except ValueError as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if parsed.path.startswith("/api/"):
            self._send_error_json(HTTPStatus.NOT_FOUND, "unknown API endpoint")
            return
        super().do_GET()

    def _send_media(self, path: Path) -> None:
        size = path.stat().st_size
        start, end = 0, size - 1
        status = HTTPStatus.OK
        range_header = self.headers.get("Range", "")
        if range_header.startswith("bytes="):
            match = re.fullmatch(r"(\d*)-(\d*)", range_header[6:].strip())
            if match:
                if match.group(1):
                    start = int(match.group(1))
                if match.group(2):
                    end = min(int(match.group(2)), size - 1)
                if not match.group(1) and match.group(2):
                    amount = int(match.group(2))
                    start = max(0, size - amount)
                    end = size - 1
                if start > end or start >= size:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                status = HTTPStatus.PARTIAL_CONTENT
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as handle:
            handle.seek(start)
            remaining = length
            while remaining:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_PUT(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        parts = self._api_parts(parsed.path)
        if len(parts) == 3 and parts[:2] == ["api", "sessions"]:
            try:
                payload = json.loads(self._read_body(MAX_JSON_BYTES).decode("utf-8"))
                with ARCHIVE_LOCK:
                    session = write_session(payload, parts[2])
                self._send_json({"ok": True, "session": session})
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        if len(parts) == 4 and parts[:2] == ["api", "sessions"] and parts[3] == "audio":
            try:
                with ARCHIVE_LOCK:
                    self._store_media(parts[2], parsed.query)
            except (OSError, ValueError) as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self._send_error_json(HTTPStatus.NOT_FOUND, "unknown API endpoint")

    def _store_media(self, session_id: str, query: str) -> None:
        valid_session_id(session_id)
        folder = find_session_dir(session_id)
        if not folder:
            raise ValueError("save session metadata before uploading media")
        params = parse_qs(query)
        original_name = safe_original_name(params.get("filename", [""])[0])
        extension = choose_media_extension(original_name, self.headers.get("Content-Type", ""))
        length = self._content_length(MAX_MEDIA_BYTES)
        if not length:
            raise ValueError("recording media is empty")
        media = folder / f"media{extension}"
        session = read_json(folder / "session.json")
        old_media = media_path_for(folder, session)
        temp = folder / f".{media.name}.upload-{os.getpid()}-{threading.get_ident()}"
        received = 0
        try:
            with temp.open("wb") as handle:
                while received < length:
                    chunk = self.rfile.read(min(1024 * 1024, length - received))
                    if not chunk:
                        raise ValueError("recording upload ended early")
                    handle.write(chunk)
                    received += len(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, media)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
        session["audio"] = True
        session["mediaFile"] = media.name
        session["originalFilename"] = original_name or session.get("originalFilename") or media.name
        session["mime"] = self.headers.get("Content-Type", "").split(";", 1)[0] or mimetypes.guess_type(media.name)[0]
        session["mediaBytes"] = received
        session["updatedAt"] = utc_now()
        session["archivedAt"] = utc_now()
        atomic_write(folder / "session.json", (json.dumps(session, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        if old_media and old_media != media and old_media.exists():
            replaced = folder / f"replaced-{old_media.name}"
            if not replaced.exists():
                old_media.rename(replaced)
        rebuild_index()
        self._send_json({"ok": True, "session": read_session(folder)}, HTTPStatus.CREATED)

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        parts = self._api_parts(parsed.path)
        if len(parts) != 3 or parts[:2] != ["api", "sessions"]:
            self._send_error_json(HTTPStatus.NOT_FOUND, "unknown API endpoint")
            return
        try:
            with ARCHIVE_LOCK:
                folder = find_session_dir(parts[2])
                if not folder:
                    self._send_error_json(HTTPStatus.NOT_FOUND, "session not found")
                    return
                cascade = parse_qs(parsed.query).get("cascade", ["0"])[0] in {"1", "true", "yes"}
                session_ids = subtree_session_ids(parts[2]) if cascade else [parts[2]]
                folders = [candidate for session_id in session_ids if (candidate := find_session_dir(session_id))]
                trash = RECORDINGS_ROOT / ".trash"
                trash.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                target = trash / f"{folder.parent.name}-{folder.name}-{stamp}"
                counter = 1
                while target.exists():
                    target = trash / f"{folder.parent.name}-{folder.name}-{stamp}-{counter}"
                    counter += 1
                target.mkdir(parents=True)
                moved_ids = []
                date_dirs = set()
                for source in folders:
                    date_dirs.add(source.parent)
                    destination = target / source.parent.name / source.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(destination))
                    moved_ids.append(source.name)
                for date_dir in date_dirs:
                    try:
                        date_dir.rmdir()
                    except OSError:
                        pass
                rebuild_index()
            self._send_json({"ok": True, "trashedPath": str(target), "deletedIds": moved_ids})
        except ValueError as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

    def log_message(self, format: str, *args: object) -> None:
        message = format % args
        print(f"[{self.log_date_time_string()}] {self.address_string()} {message}")


def main() -> None:
    RECORDINGS_ROOT.mkdir(parents=True, exist_ok=True)
    with ARCHIVE_LOCK:
        rebuild_index()
    server = ThreadingHTTPServer((HOST, PORT), FluentLabHandler)
    print(f"Fluent Lab running at: http://{HOST}:{PORT}/")
    print(f"Recording archive: {RECORDINGS_ROOT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
