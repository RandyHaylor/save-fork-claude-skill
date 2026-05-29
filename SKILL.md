---
name: save-fork
description: Create a backup fork of the active Claude Code session as a recoverable checkpoint under a new session ID. The original session continues unchanged. Use before risky work or when asked to checkpoint.
disable-model-invocation: true
---

# save-fork

Checkpoint forks of the active Claude Code session, list them later, and spawn fresh interactive windows from any historical fork.

Three operations:

1. **save** — `/save-fork [label]` → snapshot the current conversation as a new resumable session.
2. **list** — `python3 ~/.claude/skills/save-fork/list_saved_forks.py` → show this project's saved-forks store.
3. **spawn-from** — `python3 ~/.claude/skills/save-fork/spawn_from_saved_fork.py <idx-or-sid-prefix> [label]` → open a new terminal window running an interactive fork of one of the saved forks (untethered to the current session).

Logs:

- User-level append log: `~/.claude/save-fork-log.txt`
- Project-level structured store: `<cwd>/.claude/saved-forks.json`

## What to do when invoked

`/save-fork` invokes this skill. Run ONE command. Everything else (SID discovery, UUID generation, detached subprocess spawn, dual logging) is in the script.

Pick the invocation that matches the runtime platform shown in the system prompt:

```bash
# macOS / Linux:
python3 ~/.claude/skills/save-fork/save_fork_checkpoint.py "$ARGUMENTS"

# Windows (any shell with `python` on PATH):
python "%USERPROFILE%\.claude\skills\save-fork\save_fork_checkpoint.py" "%*"
```

Relay the script's output (FORK_SID, resume command, log paths) to the user verbatim and stop. Do not narrate, do not summarize the conversation, do not run any follow-up verification.

## List / spawn operations

These are NOT invoked by `/save-fork`. They run as plain CLI. Substitute `python` on Windows and use `%USERPROFILE%\.claude\skills\save-fork\...` as the path.

```bash
# POSIX:
python3 ~/.claude/skills/save-fork/list_saved_forks.py
python3 ~/.claude/skills/save-fork/spawn_from_saved_fork.py 3 "explore alt approach"
python3 ~/.claude/skills/save-fork/spawn_from_saved_fork.py 6db573e3 "explore alt approach"
```

`spawn_from_saved_fork.py` opens a new GUI terminal window running `claude --resume <selected_fork_sid> --fork-session --session-id <new_sid>`. The new window is fully detached.

Terminal autodetect by platform:
- **Linux:** gnome-terminal → x-terminal-emulator → konsole → tilix → xfce4-terminal → alacritty → kitty → foot → terminator → xterm.
- **macOS:** Terminal.app via `osascript`.
- **Windows:** Windows Terminal (`wt.exe`) → `cmd /c start`.

The spawn itself is recorded in the saved-forks store with `spawned_from_fork: true`.

Note: the supervised-tdd-worker library refuses fork-of-fork, but Claude Code itself accepts it; this skill intentionally allows spawning from historical forks regardless of their lineage.

## Constraints

- `/save-fork`: one Bash call, no follow-up `ls`/`cat`/verification commands.
- If any script exits non-zero, report its stderr and stop. Do not retry.
- This skill is user-invoked only (`disable-model-invocation: true`).
