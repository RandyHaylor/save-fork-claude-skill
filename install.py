#!/usr/bin/env python3
"""One-shot installer for the save-fork Claude Code skill bundle.

Recommended flow:
    git clone https://github.com/RandyHaylor/save-fork-claude-skill.git
    cd save-fork-claude-skill
    python3 install.py            # macOS / Linux
    py install.py                 # Windows
    # (or `python install.py` on Windows if `py` isn't on PATH)

What this script does, in order:

  1. Decides where the main skill bundle should live, with a special case:
       * If the cloned repo's PARENT directory IS ``~/.claude/skills/``,
         the install leaves the cloned folder in place and uses it AS the
         main skill bundle (no copy step). This lets a user clone with
         the GitHub repo name (e.g. ``save-fork-claude-skill``) directly
         into the skills folder if they prefer.
       * Otherwise the install copies the cloned repo into
         ``~/.claude/skills/save-fork/``.
     Existing local data under ``<target>/.claude/`` (your saved-forks
     store, plans, etc.) is preserved on copy.

  2. Marks the Python entry-point scripts executable on POSIX (a no-op
     on Windows).

  3. Does a complete REMOVE + REBUILD of the slash-command stub skill
     folders (``~/.claude/skills/launch-fork/`` and
     ``~/.claude/skills/list-forks/``) by invoking the uninstaller then
     the installer.

Idempotent — safe to re-run after `git pull` to update.

Multi-platform: works on Linux, macOS, and Windows. Standard library only.
"""
import os
import shutil
import stat
import subprocess
import sys


REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.expanduser(os.path.join("~", ".claude", "skills"))
STANDARD_TARGET_SKILL_DIR = os.path.join(SKILLS_ROOT, "save-fork")

# Names that should never be copied from source to target.
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
    return [name for name in names_in_dir if name in EXCLUDED_FILENAMES or name.endswith(".pyc")]


def detect_repo_parent_is_skills_dir(repo_dir: str, skills_root: str) -> bool:
    """Return True if ``repo_dir``'s parent is the user's skills folder.

    When True, the install should treat repo_dir AS the main skill
    bundle in place — no copy required.
    """
    return os.path.realpath(os.path.dirname(repo_dir)) == os.path.realpath(skills_root)


def resolve_main_skill_bundle_dir(repo_dir: str, skills_root: str, standard_target: str) -> tuple:
    """Pick where the main skill bundle should live, plus a status note.

    Returns (chosen_bundle_dir, status_message). status_message describes
    why we chose this path so the install log is self-explanatory.
    """
    if detect_repo_parent_is_skills_dir(repo_dir, skills_root):
        return (
            repo_dir,
            f"DETECT  repo parent IS {skills_root} — leaving bundle in place at {repo_dir}",
        )
    if os.path.realpath(repo_dir) == os.path.realpath(standard_target):
        return (repo_dir, f"DETECT  repo IS the standard target — skipping copy")
    return (standard_target, f"PLAN    will copy bundle from {repo_dir} -> {standard_target}")


def copy_repo_into_target(source_dir: str, target_dir: str) -> str:
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


def run_stub_skill_folder_uninstaller(target_dir: str) -> int:
    uninstaller_path = os.path.join(target_dir, "uninstall-commands-as-skills.py")
    if not os.path.exists(uninstaller_path):
        print(f"WARN  uninstaller not found at {uninstaller_path} — skipping remove step")
        return 0
    print(f"RUN  {sys.executable} {uninstaller_path}")
    return subprocess.call([sys.executable, uninstaller_path])


def run_stub_skill_folder_installer(target_dir: str) -> int:
    installer_path = os.path.join(target_dir, "install-commands-as-skills.py")
    if not os.path.exists(installer_path):
        print(f"ERROR: stub installer not found at {installer_path}", file=sys.stderr)
        return 1
    print(f"RUN  {sys.executable} {installer_path}")
    return subprocess.call([sys.executable, installer_path])


def main() -> int:
    print(f"# save-fork installer")
    print(f"# source: {REPO_DIR}")
    print(f"# skills root: {SKILLS_ROOT}")

    chosen_bundle_dir, choice_message = resolve_main_skill_bundle_dir(
        repo_dir=REPO_DIR,
        skills_root=SKILLS_ROOT,
        standard_target=STANDARD_TARGET_SKILL_DIR,
    )
    print(choice_message)
    print()

    if os.path.realpath(REPO_DIR) != os.path.realpath(chosen_bundle_dir):
        copy_status = copy_repo_into_target(REPO_DIR, chosen_bundle_dir)
        print(copy_status)
    else:
        print(f"SKIP COPY: bundle is already at {chosen_bundle_dir}")

    for chmod_message in mark_python_scripts_executable_on_posix(chosen_bundle_dir):
        print(chmod_message)

    print()
    print("# Stub skill folders: full REMOVE + REBUILD")
    uninstaller_returncode = run_stub_skill_folder_uninstaller(chosen_bundle_dir)
    if uninstaller_returncode != 0:
        print(f"WARN: uninstaller exited with {uninstaller_returncode} (continuing)")

    installer_returncode = run_stub_skill_folder_installer(chosen_bundle_dir)
    if installer_returncode != 0:
        print(f"ERROR: stub installer exited with {installer_returncode}", file=sys.stderr)
        return installer_returncode

    print()
    print("Install complete. You can now invoke:")
    print("  /save-fork [label]   in any Claude Code session")
    print("  /launch-fork [label] in any Claude Code session")
    print("  /list-forks          in any Claude Code session")
    print(f"Main skill bundle: {chosen_bundle_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
