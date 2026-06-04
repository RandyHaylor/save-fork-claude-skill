#!/usr/bin/env python3
"""Remove stub skill folders created by install-commands-as-skills.py.

Only removes a directory if it contains the sentinel file
    .installed-by-save-fork-commands-installer
so this is safe to run repeatedly and will never delete unrelated skill
folders.

Usage:
    uninstall-commands-as-skills.py           # remove all installer-marked stubs
    uninstall-commands-as-skills.py --only launch-fork
    uninstall-commands-as-skills.py --dry-run
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Reuse the same registry + sentinel name as the installer so they stay in sync.
import importlib.util


def _load_installer_module():
    installer_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "install-commands-as-skills.py"
    )
    spec = importlib.util.spec_from_file_location("install_commands_as_skills", installer_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def uninstall_one_stub(stub: dict, skills_root: str, sentinel_filename: str, dry_run: bool = False) -> str:
    skill_name = stub["skill_name"]
    target_dir = os.path.join(skills_root, skill_name)
    sentinel_path = os.path.join(target_dir, sentinel_filename)

    if not os.path.exists(target_dir):
        return f"MISSING {skill_name}: not installed ({target_dir})"
    if not os.path.exists(sentinel_path):
        return (
            f"REFUSE  {skill_name}: dir exists but has no installer sentinel — "
            f"not touching {target_dir}"
        )
    if dry_run:
        return f"WOULD   remove {skill_name} ({target_dir})"

    shutil.rmtree(target_dir)
    return f"REMOVE  {skill_name} ({target_dir})"


def main() -> int:
    installer = _load_installer_module()
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", default=[], help="uninstall only these (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="print actions, do not delete")
    args = parser.parse_args()

    selected = [
        stub for stub in installer.COMMAND_SKILL_STUB_REGISTRY
        if (not args.only) or stub["skill_name"] in args.only
    ]
    if not selected:
        print("nothing matched --only filter", file=sys.stderr)
        return 1

    for stub in selected:
        print(uninstall_one_stub(
            stub,
            skills_root=installer.SKILLS_ROOT,
            sentinel_filename=installer.INSTALLER_SENTINEL_FILENAME,
            dry_run=args.dry_run,
        ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
