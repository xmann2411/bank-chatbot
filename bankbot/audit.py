"""Audit log: jedan JSON po retku u logs/audit.jsonl."""

import json
import threading
from contextvars import ContextVar
from datetime import datetime, timezone

from .config import AUDIT_FILE, LOG_DIR

# ContextVar da web server s više istovremenih razgovora zapiše pravi session id.
_session = ContextVar("audit_session", default=None)
_lock = threading.Lock()


def set_session(session_id):
    _session.set(session_id)


def log(event, **data):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session": _session.get(), "event": event, **data}
    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    with _lock, open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(line)
