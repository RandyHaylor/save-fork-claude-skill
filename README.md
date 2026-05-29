# save-fork

A user-invoked [Claude Code](https://claude.com/claude-code) skill that **checkpoints your live session** into a separate, resumable session — without disturbing the session you're currently in.

Think of it as a save point for a conversation: at any moment you can stamp a recoverable fork, keep working, and later either resume that fork or pop open a brand-new terminal window running an interactive copy of it.

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

## Creative approaches used

This skill leans on several non-obvious techniques. They are described here in prose (no source listings) so you can understand *why* it works the way it does.

- **Reconstructing the active session ID with no public API.** Claude Code doesn't hand a skill its own session ID. The skill recovers it by reproducing Claude Code's own project-directory encoding (every non-alphanumeric character in the working directory path is mapped to a dash), locating the matching folder under `~/.claude/projects/`, and selecting the most-recently-modified `*.jsonl` transcript as the active session.

- **Forking via a headless seed prompt so nothing steals your terminal.** The checkpoint is created by invoking the `claude` CLI in headless mode against the parent session with `--fork-session` and a freshly minted session UUID. Because it runs headless with a one-shot seed prompt, the child process materializes a resumable session and exits on its own — your foreground session is never interrupted.

- **Fully detached background spawning, cross-platform.** The child is launched so it survives independently of the skill process. On POSIX this uses a new session (the `setsid` behavior); on Windows it uses detached-process creation flags. File descriptors are closed and output is redirected to a per-fork temp log so a failed spawn can still be inspected afterward.

- **Terminal-emulator autodetection for the interactive spawn.** Opening a *visible* new window is intentionally OS-specific:
  - **Linux:** walks a preference chain of common emulators (gnome-terminal → x-terminal-emulator → konsole → tilix → xfce4-terminal → alacritty → kitty → foot → terminator → xterm), using whichever is found on `PATH`.
  - **macOS:** drives the built-in Terminal.app through AppleScript via `osascript`, with careful quote-escaping.
  - **Windows:** prefers Windows Terminal (`wt.exe`) and falls back to a new `cmd` console.
  In every case the launched window is told to stay open after `claude` exits so you can read any startup error.

- **Crash-safe, schema-versioned state store.** The project-level JSON store is always written to a temporary file and then atomically moved into place, so an interrupted write can never corrupt it. Reads tolerate a missing or malformed file by falling back to an empty, versioned store, and the schema carries a version number for forward compatibility.

- **Dual logging by design.** Every checkpoint is recorded both in a human-friendly append-only log under your home directory and in the structured per-project JSON store — one for quick scanning across all projects, one for programmatic listing and spawning within a project.

- **Deliberate fork-of-fork support.** Some tooling refuses to fork a session that is itself a fork. Claude Code's CLI permits it, and this skill intentionally allows spawning from any historical fork regardless of its lineage — so a checkpoint chain can branch as deeply as you like.

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

- The skill is **user-invoked only** — Claude will not trigger it on its own.
- It depends on the internal layout of `~/.claude/projects/` and on `claude` CLI flags (`--resume`, `--fork-session`, `--session-id`, `-p`). If a future Claude Code release changes either, the discovery or spawn step may need updating.
- The interactive spawn needs a GUI terminal emulator on `PATH`; in a pure headless/SSH environment with none available, the spawn step will report that no supported terminal was found.
