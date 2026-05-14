"""Persistent config saved to JSON next to the EXE."""

import json
import os
from pathlib import Path

_CONFIG_FILE = Path(os.environ.get("APPDATA", ".")) / "ThreadsWorker" / "config.json"


def load() -> dict:
    try:
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _CONFIG_FILE.exists():
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save(data: dict) -> None:
    try:
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass
