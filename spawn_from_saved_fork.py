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
from platform_utils import (
    build_interactive_terminal_launch_argv,
    get_detached_popen_kwargs,
)


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

    parent_sid_for_new = entry["fork_sid"]
    new_fork_sid = str(uuid.uuid4())
    label = " ".join(args.label_words).strip() or f"spawn-from {parent_sid_for_new[:8]}"

    claude_argv = [
        "claude",
        "--resume", parent_sid_for_new,
        "--fork-session",
        "--session-id", new_fork_sid,
    ]

    terminal_argv = build_interactive_terminal_launch_argv(claude_argv, args.cwd)

    proc = subprocess.Popen(
        terminal_argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **get_detached_popen_kwargs(),
    )

    iso_now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    append_fork_entry(
        json_path=json_path,
        iso_timestamp=iso_now,
        fork_sid=new_fork_sid,
        parent_sid=parent_sid_for_new,
        label=label,
        pid=proc.pid,
        cwd=args.cwd,
        spawned_from_fork=True,
    )

    print(f"SPAWNED_FORK_SID={new_fork_sid}")
    print(f"PARENT_FORK_SID={parent_sid_for_new}")
    print(f"LABEL={label}")
    print(f"TERMINAL_PID={proc.pid}")
    print(f"TERMINAL_ARGV={terminal_argv[0]} ...")
    print(f"project log: {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
