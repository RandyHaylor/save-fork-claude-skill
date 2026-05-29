# save-fork

A user-invoked [Claude Code](https://claude.com/claude-code) skill that **checkpoints your live session** into a separate, resumable session — without disturbing the session you're currently in.

Think of it as a save point for a conversation: at any moment you can stamp a recoverable fork, keep working, and later either resume that fork or pop open a brand-new terminal window running an interactive copy of it.

Simply: This is a skill with the commands and instruction needed to guide Claude to quickly use command line calls to fork your current conversation whenever you type /save-fork in the claude cli.  It is relatively quick (10-20sec), and does not disrupt your current session in any way. You can open a terminal in that directory later and run 'claude --resume' (with no session id) and choose from a list of your generated milestone session forks. You can also fork FROM those if you wish to retain them as a checkpoint (Anthropic claims they don't support forking from a fork but I have had no issues so far - still be aware it's unofficial once you fork the fork).

---

## What it does

Three operations:

| Operation | Entry point | Effect |
|-----------|-------------|--------|
| **save** | `/save-fork [label]` | Snapshots the current conversation as a new resumable session. Your active session continues unchanged. |
| **list** | `list_saved_forks.py` | Shows this project's saved-fork store as a table. |
| **spawn-from** | `spawn_from_saved_fork.py <idx-or-sid-prefix> [label]` | Opens a **new terminal window** running an interactive fork of one of the saved forks, fully detached from the current session. |

Two logs are kept:

- **User-level** append log: `~/.claude/save-fork-log.txt`
- **Project-level** structured store: `<cwd>/.claude/saved-forks.json`

---

## Installation

This is a Claude Code skill. Place the folder at:

- **macOS / Linux:** `~/.claude/skills/save-fork/`
- **Windows:** `%USERPROFILE%\.claude\skills\save-fork\`

It requires Python 3 on `PATH` and the `claude` CLI on `PATH`. No third-party packages — standard library only.

---

## How to use

### Save a checkpoint

Inside any Claude Code session, run the slash command:

```
/save-fork before risky refactor
```

The label is optional. The skill runs a single command and prints the fork's session ID, the resume command, and the log paths. It does **not** narrate or summarize your conversation — it just stamps the checkpoint and stops.

Under the hood the slash command runs (you normally never type this yourself):

```bash
# macOS / Linux
python3 ~/.claude/skills/save-fork/save_fork_checkpoint.py "before risky refactor"

# Windows
python "%USERPROFILE%\.claude\skills\save-fork\save_fork_checkpoint.py" "before risky refactor"
```

To return to a checkpoint later, use the resume command it printed:

```bash
claude --resume <FORK_SID>
```

### List your saved forks

```bash
# macOS / Linux
python3 ~/.claude/skills/save-fork/list_saved_forks.py
python3 ~/.claude/skills/save-fork/list_saved_forks.py --json   # raw store

# Windows
python "%USERPROFILE%\.claude\skills\save-fork\list_saved_forks.py"
```

This reads the current project's `.claude/saved-forks.json` and prints an indexed table (timestamp, fork SID, parent SID, whether it was itself spawned from a fork, and the label).

### Spawn a fresh interactive window from a saved fork

Pick a fork by its 1-based index from the list, or by a SID prefix:

```bash
# macOS / Linux — by index, then by SID prefix
python3 ~/.claude/skills/save-fork/spawn_from_saved_fork.py 3 "explore alt approach"
python3 ~/.claude/skills/save-fork/spawn_from_saved_fork.py 6db573e3 "explore alt approach"

# just show the choices
python3 ~/.claude/skills/save-fork/spawn_from_saved_fork.py --list
```

This opens a **new GUI terminal window** running an interactive, forked copy of the selected session. The new window is fully detached — it's yours to drive, and closing your original session won't affect it. The spawn is itself recorded in the store (flagged as having been spawned from a fork).

---

## Files

| File | Role |
|------|------|
| `SKILL.md` | Skill manifest and the instructions Claude follows when `/save-fork` is invoked. |
| `save_fork_checkpoint.py` | The **save** operation: discover session, mint UUID, spawn detached fork, log. |
| `list_saved_forks.py` | The **list** operation: render the project store as a table or raw JSON. |
| `spawn_from_saved_fork.py` | The **spawn-from** operation: open a detached interactive window from a chosen fork. |
| `saved_forks_store.py` | Shared helpers for the atomic, schema-versioned JSON store. |
| `platform_utils.py` | Cross-platform helpers: temp-log paths, detached-spawn flags, terminal launch argv. |

---

## Notes & limitations

- The skill is **user-invoked only** — Claude will not trigger it on its own. BUT: it can be powerful to have claude reference these commands when creating automation!
- It depends on the internal layout of `~/.claude/projects/` and on `claude` CLI flags (`--resume`, `--fork-session`, `--session-id`, `-p`). If a future Claude Code release changes either, the discovery or spawn step may need updating.
- The interactive spawn needs a GUI terminal emulator on `PATH`; in a pure headless/SSH environment with none available, the spawn step will report that no supported terminal was found.
