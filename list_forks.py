#!/usr/bin/env python3
"""Unified list of saved-forks AND launched-forks for the current project.

- saved-forks (<cwd>/.claude/saved-forks.json) are checkpoints. Each can
  be forked into a new live window via `spawn_from_saved_fork.py`
  (Claude invokes this on your behalf when you say "spawn from #N").
- launched-forks (<cwd>/.claude/launched-forks.json) are live sessions
  that were opened in their own terminal window via /launch-fork. Each
  can be reopened in a new window via `relaunch_forked_session.py`
  (Claude invokes this when you say "relaunch #N").

Usage:
    list_forks.py [--json] [--cwd PATH]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from list_saved_forks import render_forks_table as render_saved_forks_table
from saved_forks_store import load_saved_forks, saved_forks_json_path_for_cwd
from launched_forks_store import (
    launched_forks_json_path_for_cwd,
    load_launched_forks,
)


def render_launched_forks_table(entries: list) -> str:
    if not entries:
        return "(no launched forks in this project)"
    header = (
        f"{'IDX':>3}  {'TIMESTAMP':<20}  "
        f"{'LAUNCHED_FORK_SID':<36}  {'SAVED_FORK_SID':<36}  "
        f"{'PARENT_SESSION_SID':<36}  DISPLAY_NAME | LABEL"
    )
    rows = [header]
    for idx, entry in enumerate(entries, start=1):
        rows.append(
            f"{idx:>3}  "
            f"{entry.get('iso_timestamp',''):<20}  "
            f"{entry.get('launched_fork_sid',''):<36}  "
            f"{entry.get('saved_fork_sid',''):<36}  "
            f"{entry.get('parent_session_sid',''):<36}  "
            f"{entry.get('display_name','')} | {entry.get('label','')}"
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="dump raw JSON for both stores")
    parser.add_argument("--cwd", default=os.getcwd(), help="project root (default: cwd)")
    # Slash-command stubs pass "$ARGUMENTS" verbatim, which is the empty
    # string when the user invokes /list-forks with no args. Swallow any
    # such trailing positional so argparse doesn't error.
    parser.add_argument("ignored_positional", nargs="*", help=argparse.SUPPRESS)
    args = parser.parse_args()

    saved_json_path = saved_forks_json_path_for_cwd(args.cwd)
    launched_json_path = launched_forks_json_path_for_cwd(args.cwd)
    saved_data = load_saved_forks(saved_json_path)
    launched_data = load_launched_forks(launched_json_path)

    if args.json:
        json.dump({
            "saved_forks_store_path": saved_json_path,
            "launched_forks_store_path": launched_json_path,
            "saved_forks": saved_data,
            "launched_forks": launched_data,
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print("=" * 80)
    print("SAVED FORKS (checkpoints — say \"spawn from saved fork #N\" to fork one into a new window)")
    print("=" * 80)
    print(f"# store: {saved_json_path}")
    print("# FORK_SID   = this checkpoint's session ID")
    print("# PARENT_SID = the live session this checkpoint was forked from")
    print("# FROM_FORK  = True if created by forking an existing saved-fork (fork-of-fork)")
    print(render_saved_forks_table(saved_data.get("forks", [])))

    print()
    print("=" * 80)
    print("LAUNCHED FORKS (live sessions — say \"relaunch launched fork #N\" to reopen one in a new window)")
    print("=" * 80)
    print(f"# store: {launched_json_path}")
    print("# LAUNCHED_FORK_SID = live session in the window")
    print("# SAVED_FORK_SID    = checkpoint the window was launched from")
    print("# PARENT_SESSION_SID = original live session everything chained off")
    print(render_launched_forks_table(launched_data.get("launched_forks", [])))

    print()
    print("-" * 80)
    print("Next-step hints (just tell Claude in this chat — no slash command needed):")
    print("  \"relaunch launched fork #N\"   reopen launched-fork N in a new window")
    print("  \"spawn from saved fork #N\"    fork saved-fork N into a new window")
    print()
    print("Slash commands:")
    print("  /save-fork [label]   create a new save-fork checkpoint of the current session")
    print("  /launch-fork [label] fork the current session into a new GUI terminal window")
    print("  /list-forks          show this list")
    return 0


if __name__ == "__main__":
    sys.exit(main())
