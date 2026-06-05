#!/usr/bin/env python3
"""Install stub skill folders that expose save-fork scripts as slash-commands.

A "command-as-skill" stub is a tiny ~/.claude/skills/<name>/SKILL.md whose
sole purpose is to make `/<name>` invoke a script in the save-fork skill.
This avoids needing a Claude Code plugin.

Each stub created by this installer drops a sentinel file
    .installed-by-save-fork-commands-installer
inside its skill directory so the uninstaller can safely remove ONLY
directories it created.

Usage:
    install-commands-as-skills.py           # install all stubs in registry
    install-commands-as-skills.py --list    # show registry, do nothing
    install-commands-as-skills.py --only launch-fork

Add more stubs by appending to COMMAND_SKILL_STUB_REGISTRY below.
"""
import argparse
import os
import sys


SKILLS_ROOT = os.path.expanduser("~/.claude/skills")
# Source dir = wherever this installer file lives. That's the skill bundle's
# actual on-disk location, whether at ~/.claude/skills/save-fork/ (the
# standard) or ~/.claude/skills/save-fork-claude-skill/ (when the user
# cloned directly into the skills folder). Rendered stub SKILL.md files
# point at scripts under THIS directory.
SOURCE_SKILL_DIR_ABS = os.path.dirname(os.path.abspath(__file__))
INSTALLER_SENTINEL_FILENAME = ".installed-by-save-fork-commands-installer"


COMMAND_SKILL_STUB_REGISTRY = [
    {
        "skill_name": "launch-fork",
        "description": (
            "Fork the active Claude Code session and open it in a NEW terminal "
            "window running interactively. The current session continues "
            "unchanged. Use when you want to branch the conversation into a "
            "separate live window."
        ),
        "script_relpath": "launch_fork_current_session_into_new_window.py",
    },
    {
        "skill_name": "list-forks",
        "description": (
            "List BOTH saved-forks and launched-forks for the current project. "
            "This is the entry point for picking a fork to act on — say "
            "\"relaunch #2\" or \"spawn from #3\" after viewing the list and "
            "Claude will run the corresponding script directly."
        ),
        "script_relpath": "list_forks.py",
    },
]


def _render_path_pair_relative_to_home(absolute_path: str) -> tuple:
    """Return (posix_form, windows_form) of an absolute path.

    If absolute_path is under the user's home directory, both forms use
    home-relative notation (``~/foo/bar`` and ``%USERPROFILE%\\foo\\bar``)
    so the rendered SKILL.md works for any user with the same install
    layout. Otherwise both forms use the bare absolute path (the Windows
    variant will not be valid on a different OS — that's the install
    user's choice for installing outside HOME).
    """
    home = os.path.expanduser("~")
    try:
        rel_to_home = os.path.relpath(absolute_path, home)
    except ValueError:
        rel_to_home = None
    if rel_to_home is None or rel_to_home.startswith(".."):
        return (absolute_path, absolute_path.replace("/", "\\"))
    posix_form = "~/" + rel_to_home.replace(os.sep, "/")
    windows_form = "%USERPROFILE%\\" + rel_to_home.replace(os.sep, "\\")
    return (posix_form, windows_form)


def _render_stub_skill_markdown(skill_name: str, description: str, script_relpath: str) -> str:
    absolute_script_path = os.path.join(SOURCE_SKILL_DIR_ABS, script_relpath)
    posix_script_path, windows_script_path = _render_path_pair_relative_to_home(absolute_script_path)
    return f"""---
name: {skill_name}
description: {description}
disable-model-invocation: true
---

# {skill_name}

This is a thin stub that delegates to a script in the `save-fork` skill.

## What to do when invoked

Run ONE command. Pick the line for the runtime platform shown in the system prompt.

```bash
# macOS / Linux:
python3 {posix_script_path} "$ARGUMENTS"

# Windows (any shell with `python` on PATH):
python "{windows_script_path}" "%*"
```

Relay the script's output verbatim and stop. Do not narrate, do not
summarize the conversation, do not run any follow-up verification.

## Constraints

- One Bash call.
- If the script exits non-zero, report its stderr and stop. Do not retry.
- User-invoked only (`disable-model-invocation: true`).
"""


def install_one_stub(stub: dict, skills_root: str, sentinel_filename: str, dry_run: bool = False) -> str:
    skill_name = stub["skill_name"]
    target_dir = os.path.join(skills_root, skill_name)
    target_skill_md = os.path.join(target_dir, "SKILL.md")
    sentinel_path = os.path.join(target_dir, sentinel_filename)

    if os.path.exists(target_dir) and not os.path.exists(sentinel_path):
        return f"SKIP    {skill_name}: dir exists and is NOT one of ours ({target_dir})"

    if dry_run:
        return f"WOULD   install {skill_name} -> {target_skill_md}"

    os.makedirs(target_dir, exist_ok=True)
    skill_md_content = _render_stub_skill_markdown(
        skill_name=skill_name,
        description=stub["description"],
        script_relpath=stub["script_relpath"],
    )
    with open(target_skill_md, "w") as f:
        f.write(skill_md_content)
    with open(sentinel_path, "w") as f:
        f.write(
            "This directory was created by save-fork's "
            "install-commands-as-skills.py. The uninstaller will remove it.\n"
        )
    return f"INSTALL {skill_name} -> {target_skill_md}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="list registry and exit")
    parser.add_argument("--only", action="append", default=[], help="install only these (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="print actions, do not write files")
    args = parser.parse_args()

    if args.list:
        for stub in COMMAND_SKILL_STUB_REGISTRY:
            print(f"- /{stub['skill_name']}  -> {stub['script_relpath']}")
        return 0

    selected = [
        stub for stub in COMMAND_SKILL_STUB_REGISTRY
        if (not args.only) or stub["skill_name"] in args.only
    ]
    if not selected:
        print("nothing matched --only filter", file=sys.stderr)
        return 1

    for stub in selected:
        print(install_one_stub(stub, SKILLS_ROOT, INSTALLER_SENTINEL_FILENAME, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
