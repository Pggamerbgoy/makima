"""
systems/security_manager.py
Voice-controlled antivirus scanning via Windows Defender / ClamAV.
"""

import os
import subprocess
import platform
import logging

logger = logging.getLogger("Makima.Security")
OS = platform.system()


class SecurityManager:

    def quick_scan(self) -> str:
        return self._scan("Quick")

    def stop_scan(self) -> str:
        if OS == "Windows":
            try:
                # 1. Try standard cmdlet
                subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", "Remove-MpScan"], capture_output=True)
                # 2. Forcefully kill any powershell processes trying to start a scan
                subprocess.run(["powershell", "-Command", "Get-Process powershell | Where-Object { $_.CommandLine -like '*Start-MpScan*' } | Stop-Process -Force"], capture_output=True)
                return "Forcing security scan to stop..."
            except Exception as e:
                return f"Failed to stop scan: {e}"
        return "Stop scan not supported on this OS."

    def full_scan(self) -> str:
        return self._scan("Full")

    def scan_downloads(self) -> str:
        downloads = os.path.expanduser("~/Downloads")
        if OS == "Windows":
            return self._defender_scan(downloads)
        return self._clam_scan(downloads)

    def _scan(self, scan_type: str) -> str:
        if OS == "Windows":
            return self._defender_scan(scan_type=scan_type)
        return self._clam_scan("/home")

    def _defender_scan(self, path: str = None, scan_type: str = "Quick") -> str:
        try:
            if path and os.path.isdir(path):
                cmd = ["powershell", "-Command",
                       f"Start-MpScan -ScanType CustomScan -ScanPath '{path}'"]
                msg = f"Scanning {path} with Windows Defender..."
            else:
                cmd = ["powershell", "-Command",
                       f"Start-MpScan -ScanType {scan_type}Scan"]
                msg = f"Starting {scan_type} scan with Windows Defender..."

            subprocess.Popen(cmd)
            return msg
        except Exception as e:
            return f"Could not start scan: {e}"

    def _clam_scan(self, path: str) -> str:
        try:
            result = subprocess.run(
                ["clamscan", "-r", "--bell", path],
                capture_output=True, text=True, timeout=300
            )
            lines = result.stdout.strip().split("\n")
            summary = [l for l in lines if "Infected" in l or "Scanned" in l]
            return " ".join(summary) if summary else "Scan complete."
        except FileNotFoundError:
            return "ClamAV not installed. Install it with: sudo apt install clamav"
        except Exception as e:
            return f"Scan failed: {e}"
