#!/usr/bin/env python3
"""Spawn a NEW interactive Claude Code window forked from a saved-fork.

Reads the current project's .claude/saved-forks.json, lets the user pick a
saved fork (by 1-based index or by SID prefix), generates a fresh fork SID,
and launches `claude --resume <selected_sid> --fork-session --session-id
<new_sid>` in a NEW terminal window fully detached from this process. The
new window is the user's to drive; it is logged as a new saved-fork entry
with `spawned_from_fork = True`.

Usage:
    spawn_from_saved_fork.py <index-or-sid-prefix> [LABEL...]
    spawn_from_saved_fork.py --list           # show available saved forks
    spawn_from_saved_fork.py --cwd PATH ...   # use a different project root

Notes on fork-of-fork:
    The supervised-tdd-worker library refuses fork-of-fork, but the Claude
    Code CLI itself accepts it. This script intentionally allows it.
"""
import argparse
import datetime
import os
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saved_forks_store import (
    append_fork_entry,
    find_entry_by_sid_or_index,
    load_saved_forks,
    saved_forks_json_path_for_cwd,
)
from list_saved_forks import render_forks_table
from active_session_locator import read_session_display_name
from platform_utils import (
    build_interactive_terminal_launch_argv,
    get_detached_popen_kwargs,
)


def do_spawn_window_from_fork(
    source_fork_sid: str,
    label: str,
    cwd: str,
    refork_source: bool = True,
) -> tuple:
    """Open a new interactive terminal window resuming/forking ``source_fork_sid``.

    When ``refork_source`` is True (default — the /spawn-from-saved-fork
    semantic), a NEW fork SID is generated and the new window runs
    ``claude --resume <source> --fork-session --session-id <new>``; the
    source fork stays immutable. The new fork's jsonl is NOT materialized
    on disk until the user adds content (Claude Code design), so resuming
    the new fork after an empty session will fail; resume the source
    instead in that case.

    When ``refork_source`` is False (the /launch-fork semantic — the source
    was just created for this launch and isn't a pre-existing checkpoint),
    the new window runs ``claude --resume <source>`` directly. One SID,
    always durable, visible tail still includes the source's tail.

    Returns (resumed_or_new_sid, terminal_pid, new_display_name, terminal_argv).
    """
    parent_display_name = read_session_display_name(source_fork_sid, cwd) or "Claude"
    new_display_name = f"{parent_display_name} (fork)"

    if refork_source:
        new_fork_sid = str(uuid.uuid4())
        claude_argv = [
            "claude",
            "--resume", source_fork_sid,
            "--fork-session",
            "--session-id", new_fork_sid,
            "--name", new_display_name,
        ]
        post_exit_sid = new_fork_sid
    else:
        new_fork_sid = source_fork_sid  # window IS the source session
        claude_argv = [
            "claude",
            "--resume", source_fork_sid,
            "--name", new_display_name,
        ]
        post_exit_sid = source_fork_sid

    terminal_argv = build_interactive_terminal_launch_argv(
        claude_argv, cwd,
        window_title=new_display_name,
        post_exit_resume_sid=post_exit_sid,
    )
    proc = subprocess.Popen(
        terminal_argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **get_detached_popen_kwargs(),
    )

    # Only log a NEW fork entry when we actually created one. In the
    # ``refork_source=False`` branch the window simply resumes an
    # existing fork; no new fork-row.
    if refork_source:
        iso_now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        project_json_path = saved_forks_json_path_for_cwd(cwd)
        append_fork_entry(
            json_path=project_json_path,
            iso_timestamp=iso_now,
            fork_sid=new_fork_sid,
            parent_sid=source_fork_sid,
            label=label,
            pid=proc.pid,
            cwd=cwd,
            spawned_from_fork=True,
        )
    return (new_fork_sid, proc.pid, new_display_name, terminal_argv)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("identifier", nargs="?", help="1-based index or SID prefix from list_saved_forks")
    parser.add_argument("label_words", nargs="*", help="optional label for the new spawn")
    parser.add_argument("--list", action="store_true", help="list saved forks and exit")
    parser.add_argument("--cwd", default=os.getcwd(), help="project root (default: cwd)")
    args = parser.parse_args()

    json_path = saved_forks_json_path_for_cwd(args.cwd)
    data = load_saved_forks(json_path)

    if args.list or not args.identifier:
        print(f"# saved-forks store: {json_path}")
        print(render_forks_table(data.get("forks", [])))
        if args.list:
            return 0
        if not args.identifier:
            print("\nspawn-from-fork: pass an index or SID prefix to spawn.", file=sys.stderr)
            return 2

    entry = find_entry_by_sid_or_index(data, args.identifier)
    if entry is None:
        print(f"spawn-from-fork: no saved fork matched {args.identifier!r}", file=sys.stderr)
        return 1

    source_fork_sid = entry["fork_sid"]
    label = " ".join(args.label_words).strip() or f"spawn-from {source_fork_sid[:8]}"

    new_fork_sid, terminal_pid, new_display_name, terminal_argv = do_spawn_window_from_fork(
        source_fork_sid=source_fork_sid, label=label, cwd=args.cwd,
    )

    print(f"SPAWNED_FORK_SID={new_fork_sid}")
    print(f"PARENT_FORK_SID={source_fork_sid}")
    print(f"NEW_DISPLAY_NAME={new_display_name!r}")
    print(f"LABEL={label}")
    print(f"TERMINAL_PID={terminal_pid}")
    print(f"TERMINAL_ARGV={terminal_argv[0]} ...")
    print(f"project log: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
