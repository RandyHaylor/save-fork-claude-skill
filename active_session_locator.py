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
    encoded = encode_cwd_for_claude_project_dir(cwd)
    proj = os.path.expanduser(os.path.join("~/.claude/projects", encoded))
    files = glob.glob(os.path.join(proj, "*.jsonl"))
    if not files:
        raise SystemExit(f"No Claude session jsonl found for cwd {cwd!r}")
    newest = max(files, key=os.path.getmtime)
    return os.path.splitext(os.path.basename(newest))[0]


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
