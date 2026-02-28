"""
systems/battery_monitor.py
Alerts user when battery drops below 20%.
"""

import time
import logging
from typing import Callable

logger = logging.getLogger("Makima.BatteryMonitor")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class BatteryMonitor:

    ALERT_THRESHOLD = 20
    CHECK_INTERVAL = 120  # seconds

    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._alerted = False
        self._running = True

    def run(self):
        if not PSUTIL_AVAILABLE:
            return
        while self._running:
            try:
                batt = psutil.sensors_battery()
                if batt and not batt.power_plugged:
                    if batt.percent <= self.ALERT_THRESHOLD and not self._alerted:
                        self.callback(
                            f"Warning! Battery is at {batt.percent:.0f}%. Please plug in your charger."
                        )
                        self._alerted = True
                    elif batt.percent > self.ALERT_THRESHOLD:
                        self._alerted = False
            except Exception:
                pass
            time.sleep(self.CHECK_INTERVAL)
