"""
System control tool — executes safe, sandboxed OS-level tasks.

SECURITY: Only a whitelisted set of operations is permitted.
Never run arbitrary shell commands from user input.
"""

from __future__ import annotations

import datetime
import logging
import os
import platform
import subprocess
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Whitelisted operations
# ---------------------------------------------------------------------------
ALLOWED_ACTIONS = {
    "time",
    "date",
    "system_info",
    "disk_usage",
    "open_app",
    "screenshot",
    "list_files",
}

# Apps that can be opened (Windows-centric, extend as needed)
SAFE_APPS: dict[str, str] = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "browser": "start https://www.google.com",
    "cmd": "cmd.exe",
    "settings": "ms-settings:",
}


async def run_system_task(action: str, *, args: str = "") -> str:
    """
    Execute a safe system operation.

    Args:
        action: One of the ALLOWED_ACTIONS.
        args:   Optional arguments (e.g. app name for 'open_app').

    Returns:
        A human-readable result string.
    """
    action = action.strip().lower()

    if action not in ALLOWED_ACTIONS:
        return (
            f"Action '{action}' is not permitted. "
            f"Allowed: {', '.join(sorted(ALLOWED_ACTIONS))}"
        )

    try:
        if action == "time":
            return f"Current time: {datetime.datetime.now().strftime('%I:%M %p')}"

        if action == "date":
            return f"Today's date: {datetime.date.today().strftime('%A, %B %d, %Y')}"

        if action == "system_info":
            info = {
                "OS": platform.system(),
                "OS Version": platform.version(),
                "Machine": platform.machine(),
                "Processor": platform.processor(),
                "Python": platform.python_version(),
            }
            return "\n".join(f"{k}: {v}" for k, v in info.items())

        if action == "disk_usage":
            usage = shutil.disk_usage("/")
            total_gb = usage.total / (1024 ** 3)
            free_gb = usage.free / (1024 ** 3)
            used_pct = (usage.used / usage.total) * 100
            return (
                f"Disk: {total_gb:.1f} GB total, "
                f"{free_gb:.1f} GB free, "
                f"{used_pct:.1f}% used"
            )

        if action == "open_app":
            app_key = args.strip().lower()
            if app_key not in SAFE_APPS:
                return (
                    f"App '{app_key}' is not in the safe list. "
                    f"Available: {', '.join(sorted(SAFE_APPS))}"
                )
            cmd = SAFE_APPS[app_key]
            subprocess.Popen(cmd, shell=True)
            logger.info("Opened app: %s → %s", app_key, cmd)
            return f"Opened {app_key} successfully."

        if action == "list_files":
            target = Path(args.strip()) if args.strip() else Path.home() / "Desktop"
            if not target.exists():
                return f"Path does not exist: {target}"
            items = sorted(target.iterdir())[:30]  # cap at 30
            listing = "\n".join(
                f"{'📁' if p.is_dir() else '📄'} {p.name}" for p in items
            )
            return f"Contents of {target}:\n{listing}"

        if action == "screenshot":
            return (
                "Screenshot capability requires the Playwright browser tool. "
                "Use the browser_automation tool instead."
            )

        return "Action processed but no output generated."

    except Exception as exc:
        logger.error("System task '%s' failed: %s", action, exc)
        return f"System task failed: {exc}"
