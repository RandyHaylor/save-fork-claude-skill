"""Cross-platform helpers for save-fork scripts.

Three concerns abstracted here:

1. Where do temp logs live? (POSIX /tmp vs Windows %TEMP%)
2. How do we spawn a fully-detached background subprocess?
3. How do we open a NEW interactive terminal window running a command?

Supported platforms: Linux, macOS (Darwin), Windows.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from typing import List


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def get_temp_log_path_for_fork(fork_sid: str) -> str:
    """Return a per-fork temp log path appropriate for this OS."""
    return os.path.join(tempfile.gettempdir(), f"save-fork-{fork_sid}.log")


def get_detached_popen_kwargs() -> dict:
    """subprocess.Popen kwargs that fully detach the child from this process."""
    if is_windows():
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP; the child has no console
        # tied to the parent.
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        return {
            "creationflags": DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            "close_fds": True,
        }
    return {
        "start_new_session": True,  # setsid on POSIX
        "close_fds": True,
    }


def _shell_quote_posix(s: str) -> str:
    if not s:
        return "''"
    safe_chars = set("@%+=:,./-_")
    if all(c.isalnum() or c in safe_chars for c in s):
        return s
    return "'" + s.replace("'", "'\\''") + "'"


def build_interactive_terminal_launch_argv(claude_argv: List[str], cwd: str) -> List[str]:
    """Return the argv to exec to pop a new terminal window running ``claude_argv``.

    The returned argv, when passed to subprocess.Popen with detached kwargs,
    will open a NEW visible terminal window in which ``claude_argv`` runs
    interactively, in directory ``cwd``. The window stays open after claude
    exits, prompting the user to press enter (POSIX) or pause (Windows), so
    they can read any startup error.

    Raises SystemExit if no supported terminal can be found.
    """
    if is_windows():
        return _build_windows_terminal_launch_argv(claude_argv, cwd)
    if is_macos():
        return _build_macos_terminal_launch_argv(claude_argv, cwd)
    return _build_linux_terminal_launch_argv(claude_argv, cwd)


def _build_linux_terminal_launch_argv(claude_argv: List[str], cwd: str) -> List[str]:
    cmd_str = " ".join(_shell_quote_posix(a) for a in claude_argv)
    wrap_cmd = (
        f"cd {_shell_quote_posix(cwd)} && {cmd_str}; "
        f'echo; echo "[claude exited; press enter to close]"; read'
    )
    if shutil.which("gnome-terminal"):
        return ["gnome-terminal", "--", "bash", "-lc", wrap_cmd]
    if shutil.which("x-terminal-emulator"):
        return ["x-terminal-emulator", "-e", "bash", "-lc", wrap_cmd]
    if shutil.which("konsole"):
        return ["konsole", "-e", "bash", "-lc", wrap_cmd]
    if shutil.which("tilix"):
        return ["tilix", "-e", "bash", "-lc", wrap_cmd]
    if shutil.which("xfce4-terminal"):
        return ["xfce4-terminal", "-e", f"bash -lc {_shell_quote_posix(wrap_cmd)}"]
    if shutil.which("alacritty"):
        return ["alacritty", "-e", "bash", "-lc", wrap_cmd]
    if shutil.which("kitty"):
        return ["kitty", "bash", "-lc", wrap_cmd]
    if shutil.which("foot"):
        return ["foot", "bash", "-lc", wrap_cmd]
    if shutil.which("terminator"):
        return ["terminator", "-e", f"bash -lc {_shell_quote_posix(wrap_cmd)}"]
    if shutil.which("xterm"):
        return ["xterm", "-e", "bash", "-lc", wrap_cmd]
    raise SystemExit("spawn-from-fork: no supported terminal emulator found on PATH (Linux).")


def _build_macos_terminal_launch_argv(claude_argv: List[str], cwd: str) -> List[str]:
    """Use osascript to drive Terminal.app — the only baked-in macOS terminal."""
    cmd_str = " ".join(_shell_quote_posix(a) for a in claude_argv)
    inner = (
        f"cd {_shell_quote_posix(cwd)} && {cmd_str}; "
        f'echo; echo "[claude exited; press enter to close]"; read'
    )
    # AppleScript-quote: backslash-escape double quotes and backslashes inside the script string.
    applescript_inner = inner.replace("\\", "\\\\").replace('"', '\\"')
    applescript = f'tell application "Terminal" to do script "{applescript_inner}"'
    return ["osascript", "-e", applescript]


def _build_windows_terminal_launch_argv(claude_argv: List[str], cwd: str) -> List[str]:
    """Prefer Windows Terminal (wt.exe); fall back to cmd in a new console."""
    cmd_pause = " && ".join([" ".join(claude_argv), "echo.", "pause"])
    if shutil.which("wt.exe"):
        # `wt.exe -d <cwd> cmd /k <cmd>` opens a new tab/window with cmd
        # running the command; /k keeps the window open after claude exits.
        return ["wt.exe", "-d", cwd, "cmd", "/k", cmd_pause]
    if shutil.which("cmd.exe") or shutil.which("cmd"):
        # `cmd /c start "" cmd /k <cmd>` opens a separate console window.
        return ["cmd", "/c", "start", "", "cmd", "/k", f"cd /d {cwd} && {cmd_pause}"]
    raise SystemExit("spawn-from-fork: no supported terminal (wt.exe or cmd) found on PATH (Windows).")
