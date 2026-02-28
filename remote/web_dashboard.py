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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

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
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(get_html_page().encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/cmd":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
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
            self.send_header("Content-Length", str(len(payload)))
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
