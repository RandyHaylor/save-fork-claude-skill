#!/usr/bin/env python3
"""Fork the CURRENT Claude Code session and open it in a NEW terminal window.

Two-tier orchestration so BOTH tiers are durable on disk before the new
window opens:

  Tier 1 (saved-fork checkpoint):
    do_save_fork_checkpoint(parent=live_session, log_to_saved_forks=True,
                            wait_for_subprocess=True) → SAVE_FORK_SID
    - Materialized via `claude -p "<seed>"`. Recorded in
      <cwd>/.claude/saved-forks.json so `spawn_from_saved_fork.py` can
      fork additional copies later (invoked via the /list-forks flow).

  Tier 2 (launched fork):
    do_save_fork_checkpoint(parent=SAVE_FORK_SID, log_to_saved_forks=False,
                            wait_for_subprocess=True) → LAUNCHED_FORK_SID
    - Same -p mechanism so the launched fork's jsonl is fully written
      BEFORE the window opens — sidesteps Claude Code's quirk of not
      materializing `--fork-session --session-id NEW` jsonls until first
      user input. Recorded ONLY in launched-forks.json (not saved-forks).

  Window open:
    do_spawn_window_from_fork(source=LAUNCHED_FORK_SID, refork_source=False)
    - Window runs `claude --resume LAUNCHED_FORK_SID --name "<parent> (fork)"`.
      One durable SID; visible tail is the tier-2 seed exchange.

Total wall-clock: ~10-60s (both tiers run `claude -p`). The cost of
guaranteed durability for both tiers.

Usage:
    launch_fork_current_session_into_new_window.py [LABEL...]
    launch_fork_current_session_into_new_window.py --cwd PATH [LABEL...]
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from active_session_locator import find_active_session_id_for_cwd
from launched_forks_store import (
    append_launched_fork_entry,
    launched_forks_json_path_for_cwd,
)
from save_fork_checkpoint import do_save_fork_checkpoint
from spawn_from_saved_fork import do_spawn_window_from_fork


def main(argv: list) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("label_words", nargs="*", help="optional label for the new fork")
    parser.add_argument("--cwd", default=os.getcwd(), help="project root (default: cwd)")
    args = parser.parse_args(argv[1:])

    label = " ".join(args.label_words).strip()
    if not label:
        label = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    parent_session_sid = find_active_session_id_for_cwd(args.cwd)

    # Tier 1: durable saved-fork checkpoint of the live session.
    saved_fork_sid, _ = do_save_fork_checkpoint(
        parent_sid=parent_session_sid,
        label=label,
        cwd=args.cwd,
        wait_for_subprocess=True,
        log_to_saved_forks=True,
        seed_kind="saved fork",
    )

    # Tier 2: durable launched-fork from the saved-fork. Same -p
    # mechanism so its jsonl exists before the window opens.
    launched_fork_sid, _ = do_save_fork_checkpoint(
        parent_sid=saved_fork_sid,
        label=label,
        cwd=args.cwd,
        wait_for_subprocess=True,
        log_to_saved_forks=False,  # belongs in launched-forks.json
        seed_kind="launched fork",
    )

    # Window: resume the launched fork directly. refork_source=False so
    # no third tier is created.
    _, terminal_pid, new_display_name, _ = do_spawn_window_from_fork(
        source_fork_sid=launched_fork_sid,
        label=label,
        cwd=args.cwd,
        refork_source=False,
    )

    # Log the launched fork in its own store.
    iso_now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    launched_json_path = launched_forks_json_path_for_cwd(args.cwd)
    append_launched_fork_entry(
        json_path=launched_json_path,
        iso_timestamp=iso_now,
        launched_fork_sid=launched_fork_sid,
        saved_fork_sid=saved_fork_sid,
        parent_session_sid=parent_session_sid,
        label=label,
        terminal_pid=terminal_pid,
        display_name=new_display_name,
        cwd=args.cwd,
    )

    print(f"Launched Fork: {launched_fork_sid}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
