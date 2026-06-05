#!/usr/bin/env python3
"""One-shot installer for the save-fork Claude Code skill bundle.

Recommended flow:
    git clone https://github.com/RandyHaylor/save-fork-claude-skill.git
    cd save-fork-claude-skill
    python3 install.py            # macOS / Linux
    py install.py                 # Windows
    # (or `python install.py` on Windows if `py` isn't on PATH)

What this script does, in order:

  1. Copies the cloned repo files into ``~/.claude/skills/save-fork/``
     (creating the directory if needed). If the clone is ALREADY at that
     location, the copy step is skipped. Existing local files (notably
     ``<target>/.claude/`` — your saved-forks store, plans, etc.) are
     preserved; only files present in the source repo are written.

  2. Marks the four Python scripts executable on POSIX (a no-op on
     Windows).

  3. Invokes ``install-commands-as-skills.py`` in the target directory
     to create the ``/launch-fork`` and ``/list-forks`` slash-command
     stub skill folders under ``~/.claude/skills/``.

Idempotent — safe to re-run after `git pull` to update.

Multi-platform: tested patterns work on Linux, macOS, and Windows. Uses
only the Python standard library.
"""
import os
import shutil
import stat
import subprocess
import sys


REPO_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_SKILL_DIR = os.path.expanduser(os.path.join("~", ".claude", "skills", "save-fork"))

# Names (anywhere in tree) that should never be copied from source to target.
EXCLUDED_FILENAMES = {
    ".git",
    "__pycache__",
    ".claude",         # local plan-mode artifacts + fork stores live here
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".DS_Store",
}


def _ignore_callback_for_copytree(src_dir: str, names_in_dir: list) -> list:
    """Return the names in src_dir/names_in_dir that copytree should skip."""
    return [name for name in names_in_dir if name in EXCLUDED_FILENAMES or name.endswith(".pyc")]


def copy_repo_into_target(source_dir: str, target_dir: str) -> str:
    """Copy source_dir into target_dir, merging with what's already there.

    Returns a one-line status describing what was done.
    """
    if os.path.realpath(source_dir) == os.path.realpath(target_dir):
        return f"SKIP COPY: source already at {target_dir}"
    os.makedirs(target_dir, exist_ok=True)
    shutil.copytree(
        src=source_dir,
        dst=target_dir,
        ignore=_ignore_callback_for_copytree,
        dirs_exist_ok=True,
    )
    return f"COPIED   {source_dir} -> {target_dir}"


def mark_python_scripts_executable_on_posix(target_dir: str) -> list:
    """chmod +x the user-invocable Python entry points on POSIX. No-op on Windows."""
    if sys.platform.startswith("win"):
        return ["SKIP CHMOD: Windows host (no POSIX execute bit needed)"]
    scripts_to_mark_executable = [
        "install.py",
        "install-commands-as-skills.py",
        "uninstall-commands-as-skills.py",
        "save_fork_checkpoint.py",
        "launch_fork_current_session_into_new_window.py",
        "list_forks.py",
        "list_saved_forks.py",
        "spawn_from_saved_fork.py",
        "relaunch_forked_session.py",
    ]
    messages = []
    for script_filename in scripts_to_mark_executable:
        script_path = os.path.join(target_dir, script_filename)
        if not os.path.exists(script_path):
            messages.append(f"CHMOD MISS: {script_filename} not present in target")
            continue
        current_mode = os.stat(script_path).st_mode
        os.chmod(script_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        messages.append(f"CHMOD +x   {script_filename}")
    return messages


def run_stub_skill_folder_installer(target_dir: str) -> int:
    """Invoke install-commands-as-skills.py in target_dir using the current Python."""
    stub_installer_path = os.path.join(target_dir, "install-commands-as-skills.py")
    if not os.path.exists(stub_installer_path):
        print(f"ERROR: stub installer not found at {stub_installer_path}", file=sys.stderr)
        return 1
    print(f"RUN      {sys.executable} {stub_installer_path}")
    return subprocess.call([sys.executable, stub_installer_path])


def main() -> int:
    print(f"# save-fork installer")
    print(f"# source: {REPO_DIR}")
    print(f"# target: {TARGET_SKILL_DIR}")
    print()

    copy_status = copy_repo_into_target(REPO_DIR, TARGET_SKILL_DIR)
    print(copy_status)

    for chmod_message in mark_python_scripts_executable_on_posix(TARGET_SKILL_DIR):
        print(chmod_message)

    stub_installer_returncode = run_stub_skill_folder_installer(TARGET_SKILL_DIR)
    if stub_installer_returncode != 0:
        print(f"ERROR: stub installer exited with code {stub_installer_returncode}", file=sys.stderr)
        return stub_installer_returncode

    print()
    print("Install complete. You can now invoke:")
    print("  /save-fork [label]   in any Claude Code session")
    print("  /launch-fork [label] in any Claude Code session")
    print("  /list-forks          in any Claude Code session")
    return 0


if __name__ == "__main__":
    sys.exit(main())
