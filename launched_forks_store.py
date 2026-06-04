"""Project-level .claude/launched-forks.json store.

Parallel to saved_forks_store.py, but for forks that were launched as
their own interactive window. Each entry records the launched fork's
SID, the intermediate save-fork it was launched from, and the live
session that whole chain originally branched off.

Schema:

    {
      "schema_version": 1,
      "launched_forks": [
        {
          "iso_timestamp": "2026-06-04T17:51:56Z",
          "launched_fork_sid":   "<NEW window's SID>",
          "saved_fork_sid":      "<intermediate save-fork SID>",
          "parent_session_sid":  "<live session SID>",
          "label": "free text",
          "terminal_pid": 12345,
          "display_name": "<parent name> (fork)",
          "cwd": "/abs/path"
        }
      ]
    }
"""
import json
import os
from typing import Optional


LAUNCHED_FORKS_RELPATH = os.path.join(".claude", "launched-forks.json")
SCHEMA_VERSION = 1


def launched_forks_json_path_for_cwd(cwd: str) -> str:
    return os.path.join(cwd, LAUNCHED_FORKS_RELPATH)


def load_launched_forks(json_path: str) -> dict:
    """Return the parsed store, or a fresh empty store if file missing/invalid."""
    if not os.path.exists(json_path):
        return {"schema_version": SCHEMA_VERSION, "launched_forks": []}
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"schema_version": SCHEMA_VERSION, "launched_forks": []}
    if not isinstance(data, dict) or "launched_forks" not in data:
        return {"schema_version": SCHEMA_VERSION, "launched_forks": []}
    data.setdefault("schema_version", SCHEMA_VERSION)
    return data


def append_launched_fork_entry(
    json_path: str,
    iso_timestamp: str,
    launched_fork_sid: str,
    saved_fork_sid: str,
    parent_session_sid: str,
    label: str,
    terminal_pid: Optional[int],
    display_name: str,
    cwd: str,
) -> None:
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    data = load_launched_forks(json_path)
    data["launched_forks"].append({
        "iso_timestamp": iso_timestamp,
        "launched_fork_sid": launched_fork_sid,
        "saved_fork_sid": saved_fork_sid,
        "parent_session_sid": parent_session_sid,
        "label": label,
        "terminal_pid": terminal_pid,
        "display_name": display_name,
        "cwd": cwd,
    })
    tmp_path = json_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, json_path)


def find_launched_entry_by_sid_or_index(data: dict, identifier: str) -> Optional[dict]:
    """Return the entry whose launched_fork_sid matches (prefix), OR by 1-based index."""
    entries = data.get("launched_forks", [])
    if identifier.isdigit():
        idx = int(identifier) - 1
        if 0 <= idx < len(entries):
            return entries[idx]
        return None
    for entry in entries:
        if entry.get("launched_fork_sid", "").startswith(identifier):
            return entry
    return None
