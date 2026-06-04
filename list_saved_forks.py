#!/usr/bin/env python3
"""List forks recorded in the current project's .claude/saved-forks.json.

Usage:
    list_saved_forks.py [--json] [--cwd PATH]

Default output is a compact table; --json dumps the raw store.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saved_forks_store import load_saved_forks, saved_forks_json_path_for_cwd


def render_forks_table(forks: list) -> str:
    if not forks:
        return "(no saved forks in this project)"
    header = f"{'IDX':>3}  {'TIMESTAMP':<20}  {'FORK_SID':<36}  {'PARENT_SID':<36}  {'FROM_FORK':<9}  LABEL"
    rows = [header]
    for idx, entry in enumerate(forks, start=1):
        rows.append(
            f"{idx:>3}  "
            f"{entry.get('iso_timestamp',''):<20}  "
            f"{entry.get('fork_sid',''):<36}  "
            f"{entry.get('parent_sid',''):<36}  "
            f"{str(entry.get('spawned_from_fork', False)):<9}  "
            f"{entry.get('label','')}"
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="dump raw JSON store")
    parser.add_argument("--cwd", default=os.getcwd(), help="project root (default: cwd)")
    args = parser.parse_args()

    json_path = saved_forks_json_path_for_cwd(args.cwd)
    data = load_saved_forks(json_path)

    if args.json:
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    print(f"# saved-forks store: {json_path}")
    print("# FORK_SID   = this checkpoint's session ID")
    print("# PARENT_SID = the live session this checkpoint was forked from")
    print("# FROM_FORK  = True if created by forking an existing saved-fork (fork-of-fork)")
    print(render_forks_table(data.get("forks", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
