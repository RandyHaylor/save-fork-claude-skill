#!/usr/bin/env python3
"""save-fork: create a checkpoint fork of the active Claude Code session.

Single-shot script. Discovers the active session JSONL by cwd encoding,
generates a fresh UUID for the fork, spawns `claude --resume PARENT
--fork-session --session-id FORK -p "..."` as a detached background
subprocess, appends a log line, and prints the fork SID immediately.

Usage:
    save_fork_checkpoint.py [LABEL...]

The label is optional; it goes into the fork's seed prompt and the log.
"""
import datetime
import glob
import os
import subprocess
import sys
import uuid

# Local import — same directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saved_forks_store import (
    append_fork_entry,
    saved_forks_json_path_for_cwd,
)
from platform_utils import (
    get_detached_popen_kwargs,
    get_temp_log_path_for_fork,
)


HOME_CLAUDE_DIR = os.path.expanduser("~/.claude")
PROJECTS_DIR = os.path.join(HOME_CLAUDE_DIR, "projects")
LOG_PATH = os.path.join(HOME_CLAUDE_DIR, "save-fork-log.txt")


def encode_cwd_for_project_dir(cwd: str) -> str:
    """Match Claude Code's project-dir encoding: non-alnum -> '-'."""
    return "".join(c if c.isalnum() else "-" for c in cwd)


def find_active_session_id_for_cwd(cwd: str) -> str:
    encoded = encode_cwd_for_project_dir(cwd)
    proj = os.path.join(PROJECTS_DIR, encoded)
    files = glob.glob(os.path.join(proj, "*.jsonl"))
    if not files:
        raise SystemExit(f"save-fork: no session jsonl found for cwd {cwd!r}")
    newest = max(files, key=os.path.getmtime)
    return os.path.splitext(os.path.basename(newest))[0]


def spawn_detached_save_fork_subprocess(
    parent_sid: str,
    fork_sid: str,
    label: str,
    seed_kind: str = "saved fork",
) -> subprocess.Popen:
    """Spawn `claude --resume ... --fork-session --session-id ... -p ...` detached.

    Returns the Popen so callers may optionally .wait() for completion (the
    /launch-fork pipeline waits so the saved fork's jsonl is complete before
    a second-tier fork is taken from it). stdout/stderr go to a per-fork
    temp log. Detach flags come from platform_utils.

    ``seed_kind`` controls the seed prompt text — it reads as a status line in
    the new fork's tail, e.g. "[saved fork: <label>]" or "[launched fork:
    <label>]". Caller picks whichever fits the semantic.
    """
    # Short status-style seed. The parenthetical at the end suppresses any
    # attempt by the model to actually act on the message — without it,
    # Claude treats the bracketed status as an instruction and responds
    # substantively.
    seed_prompt = f"[{seed_kind}: {label}] (save-fork process seed, ignore this)"
    child_log_path = get_temp_log_path_for_fork(fork_sid)
    child_log_fh = open(child_log_path, "wb")
    proc = subprocess.Popen(
        [
            "claude",
            "--resume", parent_sid,
            "--fork-session",
            "--session-id", fork_sid,
            "-p", seed_prompt,
        ],
        stdin=subprocess.DEVNULL,
        stdout=child_log_fh,
        stderr=subprocess.STDOUT,
        **get_detached_popen_kwargs(),
    )
    return proc


def append_checkpoint_log_line(fork_sid: str, parent_sid: str, label: str, child_pid: int) -> None:
    iso_now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (
        f"{iso_now} FORK={fork_sid} PARENT={parent_sid} "
        f"PID={child_pid} LABEL={label}\n"
    )
    with open(LOG_PATH, "a") as f:
        f.write(line)


def do_save_fork_checkpoint(
    parent_sid: str,
    label: str,
    cwd: str,
    wait_for_subprocess: bool = False,
    log_to_saved_forks: bool = True,
    seed_kind: str = "saved fork",
) -> tuple:
    """Create one save-fork checkpoint from ``parent_sid``.

    If ``wait_for_subprocess`` is True, blocks until the detached
    `claude -p` subprocess exits — so the new fork's jsonl is fully
    written (parent history + seed prompt + assistant ack) before
    callers fork-of-fork off it. Otherwise returns immediately after spawn.

    If ``log_to_saved_forks`` is False, the fork is still created on disk
    and the user-level append log records it, but ``saved-forks.json`` is
    NOT touched. This lets /launch-fork create an intermediate launched
    fork via the same primitive without polluting the saved-forks list.

    Returns (fork_sid, child_pid).
    """
    fork_sid = str(uuid.uuid4())
    proc = spawn_detached_save_fork_subprocess(parent_sid, fork_sid, label, seed_kind=seed_kind)
    append_checkpoint_log_line(fork_sid, parent_sid, label, proc.pid)

    if log_to_saved_forks:
        iso_now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        project_json_path = saved_forks_json_path_for_cwd(cwd)
        append_fork_entry(
            json_path=project_json_path,
            iso_timestamp=iso_now,
            fork_sid=fork_sid,
            parent_sid=parent_sid,
            label=label,
            pid=proc.pid,
            cwd=cwd,
            spawned_from_fork=False,
        )

    if wait_for_subprocess:
        proc.wait()

    return (fork_sid, proc.pid)


def main(argv: list) -> int:
    label_args = argv[1:]
    label = " ".join(label_args).strip()
    if not label:
        label = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    cwd = os.getcwd()
    parent_sid = find_active_session_id_for_cwd(cwd)
    fork_sid, child_pid = do_save_fork_checkpoint(
        parent_sid=parent_sid, label=label, cwd=cwd, wait_for_subprocess=False,
    )

    print(f"Created Fork: {fork_sid}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
