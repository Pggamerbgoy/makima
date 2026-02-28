"""
systems/system_commands.py
OS-level commands: volume, lock, screenshot, window management, battery, CPU/RAM.
Windows-first with Linux fallbacks.
"""

import os
import sys
import logging
import subprocess
import platform
from datetime import datetime

logger = logging.getLogger("Makima.System")
OS = platform.system()

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

SCREENSHOTS_DIR = "screenshots"


class SystemCommands:

    def __init__(self):
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # ─── Volume ───────────────────────────────────────────────────────────────

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        if OS == "Windows":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                scalar = level / 100.0
                volume.SetMasterVolumeLevelScalar(scalar, None)
                return f"Volume set to {level}%."
            except Exception:
                # Fallback: keyboard simulation
                pass
        if PYAUTOGUI_AVAILABLE:
            import pyautogui
            # Rough approximation
            for _ in range(50):
                pyautogui.press('volumedown')
            for _ in range(level // 2):
                pyautogui.press('volumeup')
            return f"Volume approximately set to {level}%."
        return "Volume control not available."

    def volume_up(self) -> str:
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press('volumeup')
            return "Volume increased."
        return "Volume control not available."

    def volume_down(self) -> str:
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press('volumedown')
            return "Volume decreased."
        return "Volume control not available."

    def mute(self) -> str:
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press('volumemute')
            return "Muted."
        return "Volume control not available."

    def unmute(self) -> str:
        if PYAUTOGUI_AVAILABLE:
            pyautogui.press('volumemute')
            return "Unmuted."
        return "Volume control not available."

    # ─── Window Management ────────────────────────────────────────────────────

    def maximize_window(self) -> str:
        if OS == "Windows" and PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey('win', 'up')
            return "Window maximized."
        return "Window management not available."

    def minimize_window(self) -> str:
        if OS == "Windows" and PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey('win', 'down')
            return "Window minimized."
        return "Window management not available."

    def close_window(self) -> str:
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey('alt', 'F4')
            return "Window closed."
        return "Window management not available."

    # ─── System Actions ───────────────────────────────────────────────────────

    def lock_pc(self) -> str:
        if OS == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "PC locked."
        elif OS == "Linux":
            subprocess.run(["xdg-screensaver", "lock"])
            return "Screen locked."
        return "Lock not supported on this OS."

    def screenshot(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SCREENSHOTS_DIR, f"screenshot_{timestamp}.png")
        if PYAUTOGUI_AVAILABLE:
            img = pyautogui.screenshot()
            img.save(path)
            return f"Screenshot saved to {path}."
        try:
            if OS == "Windows":
                import ctypes
                # Fallback: use Snipping tool
                subprocess.Popen(["snippingtool"])
                return "Snipping tool opened."
        except Exception as e:
            logger.warning(f"Screenshot failed: {e}")
        return "Screenshot not available."

    def empty_recycle_bin(self) -> str:
        if OS == "Windows":
            try:
                import winshell
                winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
                return "Recycle bin emptied."
            except ImportError:
                subprocess.run(
                    ["powershell", "-Command", "Clear-RecycleBin -Confirm:$false"],
                    capture_output=True
                )
                return "Recycle bin emptied."
        return "Recycle bin emptying not supported on this OS."

    # ─── Stats ────────────────────────────────────────────────────────────────

    def cpu_usage(self) -> str:
        if PSUTIL_AVAILABLE:
            usage = psutil.cpu_percent(interval=1)
            return f"CPU usage is at {usage:.1f}%."
        return "psutil not installed. Can't read CPU usage."

    def ram_usage(self) -> str:
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            used = mem.used / (1024 ** 3)
            total = mem.total / (1024 ** 3)
            return f"RAM usage: {used:.1f} GB used out of {total:.1f} GB ({mem.percent:.1f}%)."
        return "psutil not installed. Can't read RAM usage."

    def battery_status(self) -> str:
        if PSUTIL_AVAILABLE:
            try:
                batt = psutil.sensors_battery()
                if batt is None:
                    return "No battery detected (desktop)."
                plugged = "charging" if batt.power_plugged else "on battery"
                return f"Battery at {batt.percent:.0f}%, {plugged}."
            except Exception:
                pass
        return "Battery status unavailable."
