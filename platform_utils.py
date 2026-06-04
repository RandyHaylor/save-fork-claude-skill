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


def _posix_title_set_prefix(window_title: str) -> str:
    """Return a shell snippet that sets the terminal window/tab title via OSC 0.

    OSC 0 (`ESC ] 0 ; <text> BEL`) is honored by virtually every xterm-family
    terminal (gnome-terminal, konsole, xterm, iTerm2, Terminal.app, Windows
    Terminal, alacritty, kitty, foot, wezterm, tilix, ...). On terminals that
    don't honor it, printf still succeeds, so this is fail-quiet — never
    aborts the launch.
    """
    if not window_title:
        return ""
    return f"printf '\\033]0;%s\\007' {_shell_quote_posix(window_title)} ; "


def _posix_post_exit_echo_block(post_exit_resume_sid: str) -> str:
    """Return a `;`-joined echo block for after claude exits on POSIX shells.

    Always includes the "shell remains" hint; appends a resume command when
    a SID is supplied so the user can re-attach the fork they just exited.
    """
    lines = [
        "echo",
        'echo "[claude exited — shell remains. Ctrl+D or exit to close]"',
    ]
    if post_exit_resume_sid:
        lines.append('echo "Resume this fork with:"')
        lines.append(f'echo "  claude --resume {post_exit_resume_sid}"')
        lines.append("echo")
    return "; ".join(lines) + "; "


def build_interactive_terminal_launch_argv(
    claude_argv: List[str],
    cwd: str,
    window_title: str = "",
    post_exit_resume_sid: str = "",
) -> List[str]:
    """Return the argv to exec to pop a new terminal window running ``claude_argv``.

    The returned argv, when passed to subprocess.Popen with detached kwargs,
    will open a NEW visible terminal window in which ``claude_argv`` runs
    interactively, in directory ``cwd``. The window stays open after claude
    exits by dropping into an interactive shell.

    If ``window_title`` is provided, the terminal's window/tab title is set
    to it via an OSC 0 escape (POSIX) or ``title`` command (Windows). Fail-
    quiet: a terminal that ignores the escape just shows its default title.

    If ``post_exit_resume_sid`` is provided, the post-claude echo block
    includes ``claude --resume <SID>`` so the user can re-attach the fork.

    Raises SystemExit if no supported terminal can be found.
    """
    if is_windows():
        return _build_windows_terminal_launch_argv(claude_argv, cwd, window_title, post_exit_resume_sid)
    if is_macos():
        return _build_macos_terminal_launch_argv(claude_argv, cwd, window_title, post_exit_resume_sid)
    return _build_linux_terminal_launch_argv(claude_argv, cwd, window_title, post_exit_resume_sid)


def _build_linux_terminal_launch_argv(claude_argv: List[str], cwd: str, window_title: str, post_exit_resume_sid: str) -> List[str]:
    cmd_str = " ".join(_shell_quote_posix(a) for a in claude_argv)
    title_prefix = _posix_title_set_prefix(window_title)
    post_exit_block = _posix_post_exit_echo_block(post_exit_resume_sid)
    # After claude exits (whether by Ctrl+C, /exit, or otherwise), print the
    # resume hint and drop into an interactive login shell instead of closing
    # the window.
    wrap_cmd = (
        f"cd {_shell_quote_posix(cwd)} && {title_prefix}{cmd_str}; "
        f"{post_exit_block}"
        f"exec bash -l"
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


def _build_macos_terminal_launch_argv(claude_argv: List[str], cwd: str, window_title: str, post_exit_resume_sid: str) -> List[str]:
    """Use osascript to drive Terminal.app — the only baked-in macOS terminal."""
    cmd_str = " ".join(_shell_quote_posix(a) for a in claude_argv)
    title_prefix = _posix_title_set_prefix(window_title)
    post_exit_block = _posix_post_exit_echo_block(post_exit_resume_sid)
    inner = (
        f"cd {_shell_quote_posix(cwd)} && {title_prefix}{cmd_str}; "
        f"{post_exit_block}"
        f"exec bash -l"
    )
    # AppleScript-quote: backslash-escape double quotes and backslashes inside the script string.
    applescript_inner = inner.replace("\\", "\\\\").replace('"', '\\"')
    applescript = f'tell application "Terminal" to do script "{applescript_inner}"'
    return ["osascript", "-e", applescript]


def _build_windows_terminal_launch_argv(claude_argv: List[str], cwd: str, window_title: str, post_exit_resume_sid: str) -> List[str]:
    """Prefer Windows Terminal (wt.exe); fall back to cmd in a new console.

    Title is set via cmd's built-in `title` command if provided. Fail-quiet:
    an unrecognized title still leaves the window with its default title.
    """
    parts = []
    if window_title:
        # cmd's `title` builtin takes the rest of the line literally; just
        # strip embedded CR/LF to be safe.
        safe_title = window_title.replace("\r", " ").replace("\n", " ")
        parts.append(f"title {safe_title}")
    parts.append(" ".join(claude_argv))
    parts.append("echo.")
    parts.append("echo [claude exited - cmd shell remains. exit to close]")
    if post_exit_resume_sid:
        parts.append("echo Resume this fork with:")
        parts.append(f"echo   claude --resume {post_exit_resume_sid}")
        parts.append("echo.")
    # Note: NOT calling `pause` here — cmd /k keeps the prompt alive after
    # the chain finishes, so the window stays as a normal cmd shell.
    cmd_pause = " & ".join(parts)
    if shutil.which("wt.exe"):
        return ["wt.exe", "-d", cwd, "cmd", "/k", cmd_pause]
    if shutil.which("cmd.exe") or shutil.which("cmd"):
        return ["cmd", "/c", "start", "", "cmd", "/k", f"cd /d {cwd} && {cmd_pause}"]
    raise SystemExit("spawn-from-fork: no supported terminal (wt.exe or cmd) found on PATH (Windows).")
