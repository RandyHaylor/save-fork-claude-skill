"""Shared helpers for the project-level .claude/saved-forks.json store.

Schema (top-level dict for forward compat):

    {
      "schema_version": 1,
      "forks": [
        {
          "iso_timestamp": "2026-05-25T17:48:02Z",
          "fork_sid":  "uuid",
          "parent_sid": "uuid",
          "label": "free text",
          "pid": 12345,
          "cwd": "/abs/path",
          "spawned_from_fork": false   # true when created via spawn_from_saved_fork
        },
        ...
      ]
    }
"""
import json
import os
from typing import Optional


SAVED_FORKS_RELPATH = os.path.join(".claude", "saved-forks.json")
SCHEMA_VERSION = 1


def saved_forks_json_path_for_cwd(cwd: str) -> str:
    return os.path.join(cwd, SAVED_FORKS_RELPATH)


def load_saved_forks(json_path: str) -> dict:
    """Return the parsed store, or a fresh empty store if file missing/invalid."""
    if not os.path.exists(json_path):
        return {"schema_version": SCHEMA_VERSION, "forks": []}
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"schema_version": SCHEMA_VERSION, "forks": []}
    if not isinstance(data, dict) or "forks" not in data:
        return {"schema_version": SCHEMA_VERSION, "forks": []}
    data.setdefault("schema_version", SCHEMA_VERSION)
    return data


def append_fork_entry(
    json_path: str,
    iso_timestamp: str,
    fork_sid: str,
    parent_sid: str,
    label: str,
    pid: Optional[int],
    cwd: str,
    spawned_from_fork: bool = False,
) -> None:
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    data = load_saved_forks(json_path)
    data["forks"].append({
        "iso_timestamp": iso_timestamp,
        "fork_sid": fork_sid,
        "parent_sid": parent_sid,
        "label": label,
        "pid": pid,
        "cwd": cwd,
        "spawned_from_fork": spawned_from_fork,
    })
    tmp_path = json_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp_path, json_path)


def find_entry_by_sid_or_index(data: dict, identifier: str) -> Optional[dict]:
    """Return the entry whose fork_sid matches, OR by 1-based index from list-forks output."""
    forks = data.get("forks", [])
    if identifier.isdigit():
        idx = int(identifier) - 1
        if 0 <= idx < len(forks):
            return forks[idx]
        return None
    for entry in forks:
        if entry.get("fork_sid", "").startswith(identifier):
            return entry
    return None
