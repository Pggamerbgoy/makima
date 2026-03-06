"""
remote/web_dashboard.py
Local web dashboard to control Makima via browser on port 8000.
Run standalone: python remote/web_dashboard.py
Or inject router and run in a thread.
"""

import os
import json
import logging
import threading
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

try:
    from systems.system_commands import SystemCommands
    sys_cmd = SystemCommands()
except ImportError:
    sys_cmd = None

logger = logging.getLogger("Makima.WebDashboard")

PORT = int(os.getenv("MAKIMA_DASHBOARD_PORT", "8000"))

def get_html_page():
    ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "makima_ui.html")
    try:
        with open(ui_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<h1>Error loading UI: {e}</h1>"


class DashboardHandler(BaseHTTPRequestHandler):

    assistant = None  # Set by WebDashboard before starting

    def log_message(self, format, *args):
        pass  # Suppress default access logs

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_html_page().encode())
        elif parsed.path == "/stats":
            stats = {
                "cpu": 0, "ram": 0, "battery": "N/A", "temp": 0
            }
            if sys_cmd:
                try:
                    # Parse numeric values from strings if possible
                    cpu_str = sys_cmd.cpu_usage() # "CPU usage is at 10.5%."
                    stats["cpu"] = float(cpu_str.split("at ")[1].replace("%", "").replace(".", "", 1).replace(".", "")) # Rough parse
                    # Actually, let's just use psutil directly if available or return raw strings
                    import psutil
                    stats["cpu"] = psutil.cpu_percent()
                    stats["ram"] = psutil.virtual_memory().percent
                    batt = psutil.sensors_battery()
                    stats["battery"] = batt.percent if batt else "N/A"
                except: pass
            
            payload = json.dumps(stats).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        elif parsed.path == "/config":
            config_path = os.path.join(os.getcwd(), "user_preferences.json")
            data = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r") as f:
                        data = json.load(f)
                except: pass
            
            # Add some .env info (masked)
            data["env"] = {
                "GEMINI_BACKEND": os.getenv("GEMINI_API_KEY") is not None,
                "CALENDAR_ENABLED": os.getenv("CALENDAR_ENABLED") == "1",
                "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "llama3.2"),
                "SPOTIPY_CLIENT_ID": os.getenv("SPOTIPY_CLIENT_ID") is not None
            }
            
            payload = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        parsed = urlparse(self.path)
        
        if parsed.path == "/cmd":
            try:
                data = json.loads(body)
                cmd = data.get("cmd", "")
                if self.assistant:
                    raw_response = self.assistant.process_input(cmd)
                    response = raw_response if raw_response else "(Action executed privately or failed)"
                else:
                    response = "Assistant not connected."
            except Exception as e:
                response = f"Error: {e}"
            payload = json.dumps({"response": response}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        elif parsed.path == "/config":
            try:
                new_config = json.loads(body)
                config_path = os.path.join(os.getcwd(), "user_preferences.json")
                # Merge with existing
                current = {}
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        current = json.load(f)
                
                # Basic deep merge or just override explicit
                if "explicit" in new_config:
                    current.setdefault("explicit", {}).update(new_config["explicit"])
                
                with open(config_path, "w") as f:
                    json.dump(current, f, indent=2)
                
                response = "Configuration updated successfully."
            except Exception as e:
                response = f"Error saving config: {e}"
            
            payload = json.dumps({"response": response}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)


class WebDashboard:

    def __init__(self, assistant):
        DashboardHandler.assistant = assistant
        self.server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)

    def start(self):
        logger.info(f"🌐 Web dashboard running at http://localhost:{PORT}")
        self.server.serve_forever()

    def start_in_thread(self):
        t = threading.Thread(target=self.start, daemon=True)
        t.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dashboard = WebDashboard(None)
    dashboard.start()
