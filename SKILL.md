---
name: save-fork
description: Create a backup fork of the active Claude Code session as a recoverable checkpoint under a new session ID. The original session continues unchanged. Use before risky work or when asked to checkpoint.
disable-model-invocation: true
---

# save-fork

Checkpoint the active Claude Code session into a separate resumable session. This is the **save** entry point in a small family of related slash commands:

| Slash command | What it does |
|--------------|--------------|
| **`/save-fork [label]`** (this skill) | Checkpoint the current session. Returns immediately; the actual `claude -p` subprocess runs detached. |
| `/launch-fork [label]` | One-shot: save-fork the current session, then open the result in a new GUI terminal window. Two durable forks created. |
| `/list-forks` | Show both saved-fork and launched-fork tables for the project. The list is the entry point for re-launching or spawning: tell Claude "relaunch #2" or "spawn from #3" in chat and it runs the corresponding script directly. |

Stores written by this skill:

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

Relay the script's output (a single `Created Fork: <SID>` line) to the user verbatim and stop. Do not narrate, do not summarize the conversation, do not run any follow-up verification.

## Constraints

- One Bash call, no follow-up `ls`/`cat`/verification commands.
- If the script exits non-zero, report its stderr and stop. Do not retry.
- This skill is user-invoked only (`disable-model-invocation: true`).
