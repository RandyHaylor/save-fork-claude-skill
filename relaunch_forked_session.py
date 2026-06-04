#!/usr/bin/env python3
"""Relaunch a previously-launched fork in a new terminal window.

Reads <cwd>/.claude/launched-forks.json, picks an entry by 1-based index
or launched-fork SID prefix, and opens a new terminal window running
`claude --resume <launched_fork_sid> --name "<display_name>"`. NO further
fork — the launched fork already exists on disk, so we resume it
directly.

Usage:
    relaunch_launched_fork.py <index-or-sid-prefix>
    relaunch_launched_fork.py --list
    relaunch_launched_fork.py --cwd PATH ...
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launched_forks_store import (
    find_launched_entry_by_sid_or_index,
    launched_forks_json_path_for_cwd,
    load_launched_forks,
)
from list_forks import render_launched_forks_table
from platform_utils import (
    build_interactive_terminal_launch_argv,
    get_detached_popen_kwargs,
)


def do_relaunch_launched_fork(entry: dict, cwd: str) -> tuple:
    """Open a new terminal window resuming entry['launched_fork_sid'].

    Returns (terminal_pid, terminal_argv).
    """
    launched_fork_sid = entry["launched_fork_sid"]
    display_name = entry.get("display_name") or "Claude (relaunched)"

    claude_argv = [
        "claude",
        "--resume", launched_fork_sid,
        "--name", display_name,
    ]
    terminal_argv = build_interactive_terminal_launch_argv(
        claude_argv, cwd,
        window_title=display_name,
        post_exit_resume_sid=launched_fork_sid,
    )
    proc = subprocess.Popen(
        terminal_argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **get_detached_popen_kwargs(),
    )
    return (proc.pid, terminal_argv)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("identifier", nargs="?", help="1-based index or SID prefix")
    parser.add_argument("--list", action="store_true", help="list and exit")
    parser.add_argument("--cwd", default=os.getcwd(), help="project root (default: cwd)")
    args = parser.parse_args()

    json_path = launched_forks_json_path_for_cwd(args.cwd)
    data = load_launched_forks(json_path)

    if args.list or not args.identifier:
        print(f"# launched-forks store: {json_path}")
        print(render_launched_forks_table(data.get("launched_forks", [])))
        if args.list:
            return 0
        if not args.identifier:
            print("\nrelaunch-launched-fork: pass an index or SID prefix.", file=sys.stderr)
            return 2

    entry = find_launched_entry_by_sid_or_index(data, args.identifier)
    if entry is None:
        print(f"relaunch-launched-fork: no launched fork matched {args.identifier!r}", file=sys.stderr)
        return 1

    do_relaunch_launched_fork(entry, args.cwd)
    print(f"Relaunched Fork: {entry['launched_fork_sid']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
