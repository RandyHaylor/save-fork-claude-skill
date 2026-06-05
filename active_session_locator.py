"""Find the active Claude Code session ID for a given working directory.

Claude Code stores each session as a .jsonl file under
    ~/.claude/projects/<encoded-cwd>/
where <encoded-cwd> replaces every non-alphanumeric character in the
absolute cwd with '-'. The "active" session is the most-recently-modified
jsonl in that directory.
"""
import glob
import json
import os
from typing import Optional


def encode_cwd_for_claude_project_dir(cwd: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in cwd)


def get_session_jsonl_path(session_id: str, cwd: str) -> str:
    encoded = encode_cwd_for_claude_project_dir(cwd)
    return os.path.expanduser(
        os.path.join("~/.claude/projects", encoded, f"{session_id}.jsonl")
    )


def find_active_session_id_for_cwd(cwd: str) -> str:
    """Find the running session ID by encoding ``cwd`` (or any ancestor) and
    looking for the matching project dir under ~/.claude/projects/.

    Claude Code keys its project dirs to the path the ``claude`` CLI was
    launched from, NOT to whatever cwd a subprocess (or a /save-fork
    bash call) happens to be running in. So if /save-fork fires from a
    subdir of the project root, the encoded cwd has no project dir.

    Resolution: walk up from ``cwd`` to filesystem root, collect every
    candidate ``~/.claude/projects/<encoded>/`` that exists and contains
    jsonls, and return the SID of the globally newest-mtime jsonl among
    all candidates. The session that's currently being written to has
    the most-recent mtime — that's the running session.
    """
    candidate_jsonl_paths = []
    visited = set()
    current_dir = os.path.abspath(cwd)
    while current_dir and current_dir not in visited:
        visited.add(current_dir)
        encoded = encode_cwd_for_claude_project_dir(current_dir)
        candidate_project_dir = os.path.expanduser(
            os.path.join("~/.claude/projects", encoded)
        )
        candidate_jsonl_paths.extend(
            glob.glob(os.path.join(candidate_project_dir, "*.jsonl"))
        )
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            break
        current_dir = parent_dir
    if not candidate_jsonl_paths:
        raise SystemExit(
            f"No Claude session jsonl found for cwd {cwd!r} or any ancestor"
        )
    newest_jsonl_path = max(candidate_jsonl_paths, key=os.path.getmtime)
    return os.path.splitext(os.path.basename(newest_jsonl_path))[0]


def read_session_display_name(session_id: str, cwd: str) -> Optional[str]:
    """Return the live display name for a session, or None if not set.

    Claude Code records the display name (the blue text above the CLI prompt;
    settable via `claude --name <X>`; also bumped by /branch with a "(Branch)"
    suffix) as repeated JSONL records of the form
        {"type":"agent-name","agentName":"<NAME>","sessionId":"..."}
    The latest such record in the file is authoritative.
    """
    jsonl_path = get_session_jsonl_path(session_id, cwd)
    if not os.path.exists(jsonl_path):
        return None
    latest_name: Optional[str] = None
    with open(jsonl_path, "r") as f:
        for line in f:
            if '"agent-name"' not in line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") == "agent-name":
                name = obj.get("agentName")
                if isinstance(name, str) and name:
                    latest_name = name
    return latest_name
