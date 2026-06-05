# save-fork

A bundle of user-invoked [Claude Code](https://claude.com/claude-code) skills for **checkpointing your live session** into separate, resumable sessions — without disturbing the session you're currently in — and for opening forks of those sessions in their own terminal windows.

Think of it as save points + parallel-window branching for a conversation: stamp a recoverable checkpoint at any moment, keep working, and later resume the checkpoint, fork it into a new live window, or reopen a previously-launched live window.

Simply: This is a skill with the commands and instruction needed to guide Claude to quickly use command line calls to fork your current conversation whenever you type /save-fork in the claude cli.  It is relatively quick (10-20sec), and does not disrupt your current session in any way. You can open a terminal in that directory later and run 'claude --resume' (with no session id) and choose from a list of your generated milestone session forks. You can also fork FROM those if you wish to retain them as a checkpoint (Anthropic claims they don't support forking from a fork but I have had no issues so far - still be aware it's unofficial once you fork the fork).

---

## Installation

Clone anywhere, then run `install.py`. Linux, macOS, and Windows. Requires Python 3.8+ and the `claude` CLI on `PATH`. Standard library only.

```bash
git clone https://github.com/RandyHaylor/save-fork-claude-skill.git
cd save-fork-claude-skill

python3 install.py        # macOS / Linux
py install.py             # Windows (or `python install.py`)
```

Re-run `python3 install.py` after `git pull` to update — it's idempotent.

---

## Quick start

Once installed, the three slash commands work in any Claude Code session:

- **`/save-fork`** — create a new session on disk as a copy of the current session you can resume/branch from later.
- **`/launch-fork`** — immediately open a current-session copy in a new window (and save a separate copy as a checkpoint).
- **`/list-forks`** — show saved and launched forks. You can request to resume or launch a fork from one by name (just tell Claude "relaunch #2" or "spawn from #3").

Both `/save-fork` and `/launch-fork` accept an optional label. 
By default, source session display name is used with appended/incremented `(fork)` / `(fork-N)` suffix.
If the session has no display name set, a UTC timestamp is used instead.

---

## What install.py does

1. Copies the cloned repo to `~/.claude/skills/save-fork/` (creating the directory if needed). Existing local files under `<target>/.claude/` (your saved-forks and launched-forks JSON stores) are preserved.
2. Marks the Python entry-point scripts executable on POSIX (no-op on Windows).
3. Runs `install-commands-as-skills.py` to create `~/.claude/skills/{launch-fork, list-forks}/SKILL.md` stub folders that register `/launch-fork` and `/list-forks` as Claude Code slash commands. The `/save-fork` slash command comes from the bundle's own `SKILL.md`.

**Uninstall the slash-command stubs** (leaves `~/.claude/skills/save-fork/` and your stores intact):

```bash
python3 ~/.claude/skills/save-fork/uninstall-commands-as-skills.py
# Windows:
python "%USERPROFILE%\.claude\skills\save-fork\uninstall-commands-as-skills.py"
```

Only directories carrying the sentinel file `.installed-by-save-fork-commands-installer` are removed, so unrelated skill folders are never touched.

---

## What's included

Three user-facing slash commands (installed by `install-commands-as-skills.py`):

| Slash command | Effect |
|--------------|--------|
| **`/save-fork [label]`** | Snapshot the current conversation as a new resumable session. Your active session continues unchanged. `[label]` is **optional** — a UTC timestamp is used if omitted. |
| **`/launch-fork [label]`** | One-shot: save-fork the live session, then open the result in a new GUI terminal window — two durable forks created (a checkpoint plus a live working session in a window). `[label]` is **optional** — a UTC timestamp is used if omitted. |
| **`/list-forks`** | Show BOTH the saved-forks and launched-forks tables for the current project. **This is the entry point for re-launching or spawning** — after viewing, just tell Claude in the chat "relaunch #2" or "spawn from #3" and it will run the right script directly. |

Two helper scripts live in the repo but are NOT exposed as slash commands — they're called by Claude on your behalf from the `/list-forks` flow:

- `spawn_from_saved_fork.py` — fork an existing saved checkpoint into a new GUI window.
- `relaunch_forked_session.py` — reopen a previously launched fork in a new GUI window.

Three on-disk stores:

- **User-level append log:** `~/.claude/save-fork-log.txt` — quick scan across all projects.
- **Project saved-forks store:** `<cwd>/.claude/saved-forks.json` — checkpoint records.
- **Project launched-forks store:** `<cwd>/.claude/launched-forks.json` — windowed live-session records, each linking back to the saved-fork it was launched from and the original live session everything branched off.

---

## How to use

### Save a checkpoint of your current session

Inside any Claude Code session:

```
/save-fork before risky refactor
```

The label is optional. The skill prints a single line, `Created Fork: <SID>`, and returns in well under a second; the actual `claude -p` checkpoint subprocess runs detached. To resume the fork later: `claude --resume <SID>`.

All four window-affecting scripts follow the same one-line output style:

- `/save-fork`               → `Created Fork: <SID>`
- `/launch-fork`             → `Launched Fork: <SID>` (after the ~10-60s two-tier setup)
- `spawn_from_saved_fork.py` → `Spawned Fork: <SID>` (invoked via `/list-forks` flow)
- `relaunch_forked_session.py` → `Relaunched Fork: <SID>` (invoked via `/list-forks` flow)

The full lineage (parent SID, intermediate save-fork SID, terminal PID, display name, log paths) is always recoverable from `<cwd>/.claude/saved-forks.json` and `<cwd>/.claude/launched-forks.json`. Use `/list-forks` to see it.

### Fork an existing saved checkpoint into a new live window

Just tell Claude in chat: *"spawn from saved fork #3"* or *"spawn from saved fork 6db573e3"*. Claude reads the `/list-forks` output, finds the row, and runs `spawn_from_saved_fork.py` for you. You can also run the script directly:

```bash
python3 ~/.claude/skills/save-fork/spawn_from_saved_fork.py 3 explore alt approach
python3 ~/.claude/skills/save-fork/spawn_from_saved_fork.py 6db573e3 explore alt approach
```

Opens a new GUI terminal window running an interactive forked copy of the selected checkpoint.

### One-shot: fork the current session into a new window

```
/launch-fork explore an alternative
```

Internally this is a two-tier operation, both tiers durable on disk **before** the window opens:

1. **Tier 1** — save-fork the live session via `claude -p "<seed>"`. Recorded in `saved-forks.json`.
2. **Tier 2** — save-fork that saved-fork into a *launched* fork, also via `claude -p "<seed>"`. Recorded in `launched-forks.json` (not in saved-forks).
3. **Window open** — `claude --resume <LAUNCHED_FORK_SID> --name "<parent> (fork)"` runs in a new detached terminal window.

Total wall-clock: ~10-60s (two consecutive `claude -p` calls). This is the cost of guaranteed durability: even if you Ctrl+C the new window before typing anything, `claude --resume <LAUNCHED_FORK_SID>` still works because the jsonl was materialized at launch time, not lazily on first input.

The seed prompts are kept short and status-like — `[saved fork: <label>] (save-fork process seed, ignore this)` for the tier-1 checkpoint and `[launched fork: <label>] (save-fork process seed, ignore this)` for the tier-2 launched fork — so they read as status lines in the new window's history rather than instructions you have to scroll past. The trailing parenthetical is needed because without it the model treats the bracketed status as a prompt and writes a substantive reply.

### List everything in the current project

```
/list-forks
```

Prints both tables (saved checkpoints + launched live sessions) with the lineage columns explained, followed by next-step hints. The list itself is the entry point: just tell Claude *"relaunch #2"* or *"spawn from #3"* in the chat and it runs the right script for you.

### Reopen a previously-launched fork in another window

Tell Claude in chat: *"relaunch launched fork #1"* or *"relaunch 49c07d03"*. Or invoke the script directly:

```bash
python3 ~/.claude/skills/save-fork/relaunch_forked_session.py 1
python3 ~/.claude/skills/save-fork/relaunch_forked_session.py 49c07d03
```

Resumes the chosen launched-fork SID directly (no further fork). The same session is reopened — your prior conversation in that fork is still there.

---

## Window behavior

Every launched/spawned window:

- **Title** = the session's display name, including a `(fork)` suffix (via OSC 0 on POSIX, `title` builtin on Windows).
- **In-session display name** (the blue text above the CLI prompt) is set via `claude --name "<parent> (fork)"`.
- **Stays open after claude exits** — the wrap shell drops into an interactive shell (`exec bash -l` on POSIX, `cmd /k` on Windows) with a post-exit message including a `claude --resume <SID>` command. Ctrl+C inside claude no longer closes the window.
- **Is fully detached** from the launcher — closing your original Claude Code session does not close the window.

---

## Creative approaches used

This skill leans on several non-obvious techniques. They are described here in prose (no source listings) so you can understand *why* it works the way it does.

- **Reconstructing the active session ID with no public API.** Claude Code doesn't hand a skill its own session ID. The skill recovers it by reproducing Claude Code's own project-directory encoding (every non-alphanumeric character in the working directory path is mapped to a dash), locating the matching folder under `~/.claude/projects/`, and selecting the most-recently-modified `*.jsonl` transcript as the active session.

- **Reading the live session's display name from its jsonl.** Claude Code stores the human-readable session name in `{"type":"agent-name","agentName":"...","sessionId":"..."}` records inside the session's jsonl. We scan for the latest such record so the launched fork can be named `"<parent> (fork)"` automatically.

- **Forking via a headless seed prompt so nothing steals your terminal.** The checkpoint is created by invoking the `claude` CLI in headless mode against the parent session with `--fork-session` and a freshly minted session UUID. Because it runs headless with a one-shot seed prompt, the child process materializes a resumable session and exits on its own — your foreground session is never interrupted.

- **Two-tier launch for guaranteed durability.** `claude --resume X --fork-session --session-id NEW` does NOT write `NEW.jsonl` to disk until the new session has user input. To make `/launch-fork`'s new window resumable even if the user Ctrl+C's immediately, the skill performs *two* headless `-p` invocations: tier-1 produces the saved-fork checkpoint, tier-2 produces the launched fork that the window will resume. Only then is the GUI terminal opened, against an already-on-disk jsonl. Cost: ~10-60s wall-clock per `/launch-fork`.

- **Fully detached background spawning, cross-platform.** The child is launched so it survives independently of the skill process. On POSIX this uses a new session (the `setsid` behavior); on Windows it uses detached-process creation flags. File descriptors are closed and output is redirected to a per-fork temp log so a failed spawn can still be inspected afterward.

- **Terminal-emulator autodetection for the interactive spawn.** Opening a *visible* new window is intentionally OS-specific:
  - **Linux:** walks a preference chain of common emulators (gnome-terminal → x-terminal-emulator → konsole → tilix → xfce4-terminal → alacritty → kitty → foot → terminator → xterm), using whichever is found on `PATH`.
  - **macOS:** drives the built-in Terminal.app through AppleScript via `osascript`, with careful quote-escaping.
  - **Windows:** prefers Windows Terminal (`wt.exe`) and falls back to a new `cmd` console.
  In every case the launched window stays open after `claude` exits by dropping into an interactive shell, and prints a `claude --resume <SID>` resume command so the session can be re-attached.

- **OSC 0 + title builtin for fail-quiet window naming.** Window/tab title is set inside the wrap shell — `printf '\033]0;%s\007' "<name>"` on POSIX, `title <name>` on Windows. Both are fail-quiet: emulators that ignore them just keep their default title.

- **Crash-safe, schema-versioned state stores.** Both project-level JSON stores (`saved-forks.json` and `launched-forks.json`) are always written to a temporary file and then atomically moved into place, so an interrupted write can never corrupt them. Reads tolerate a missing or malformed file by falling back to an empty, versioned store, and the schemas carry version numbers for forward compatibility.

- **Sentinel-gated installer.** `install-commands-as-skills.py` and its uninstaller refuse to touch any skill folder that lacks the marker file `.installed-by-save-fork-commands-installer`. Re-running the installer is safe; uninstall never deletes unrelated skill dirs.

- **Deliberate fork-of-fork support.** Some tooling refuses to fork a session that is itself a fork. Claude Code's CLI permits it, and this skill intentionally allows spawning from any historical fork regardless of its lineage — so a checkpoint chain can branch as deeply as you like.

---

## Files

| File | Role |
|------|------|
| `SKILL.md` | Skill manifest and the instructions Claude follows when `/save-fork` is invoked. |
| `save_fork_checkpoint.py` | The **save** operation: discover session, mint UUID, spawn detached fork, log. Exports `do_save_fork_checkpoint` reused by `/launch-fork`. |
| `list_saved_forks.py` | Saved-forks table renderer. Used directly via CLI; the renderer is also imported by `/list-forks`. |
| `list_forks.py` | The **list** operation (`/list-forks`): renders both saved-forks and launched-forks tables with action hints. |
| `spawn_from_saved_fork.py` | The **spawn-from** operation: open a detached interactive window from a chosen saved fork. Exports `do_spawn_window_from_fork`. |
| `launch_fork_current_session_into_new_window.py` | The **launch** operation (`/launch-fork`): two-tier orchestration; uses `do_save_fork_checkpoint` twice and then `do_spawn_window_from_fork` with `refork_source=False`. |
| `relaunch_forked_session.py` | The **relaunch** operation (invoked via `/list-forks` flow): reopen a launched fork. |
| `saved_forks_store.py` | Shared helpers for the atomic, schema-versioned saved-forks JSON store. |
| `launched_forks_store.py` | Shared helpers for the atomic, schema-versioned launched-forks JSON store. |
| `active_session_locator.py` | Discover the active session ID and read its display name from the JSONL. |
| `platform_utils.py` | Cross-platform helpers: temp-log paths, detached-spawn flags, terminal launch argv, OSC-title injection, post-exit resume-hint block. |
| `install.py` | One-shot installer: copies the repo to `~/.claude/skills/save-fork/`, chmods scripts, runs the stub installer below. |
| `install-commands-as-skills.py` / `uninstall-commands-as-skills.py` | Register/remove the slash-command skill stubs (called by `install.py`). |

---

## Notes & limitations

- All slash commands are **user-invoked only** — Claude will not trigger them on its own. BUT: it can be powerful to have Claude reference these commands when creating automation!
- The skill depends on the internal layout of `~/.claude/projects/` and on `claude` CLI flags (`--resume`, `--fork-session`, `--session-id`, `-p`, `--name`). If a future Claude Code release changes any of these, the discovery, spawn, or naming step may need updating.
- The interactive spawn needs a GUI terminal emulator on `PATH`; in a pure headless/SSH environment with none available, the spawn step will report that no supported terminal was found.
- `/launch-fork` waits for both tier-1 and tier-2 `claude -p` subprocesses to finish writing their jsonls before opening the window, so it has noticeable latency (~10-60s end to end). This is by design — it's what makes the launched fork durable even on an immediate Ctrl+C.
- `--fork-session --session-id NEW` without `-p` does NOT materialize `NEW.jsonl` until first user input. The two-tier launch path is the workaround. The single-tier `spawn_from_saved_fork.py` retains this Claude-Code quirk by design (it's forking a pre-existing checkpoint you want to preserve).
