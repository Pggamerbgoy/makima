"""
ui/command_center.py

Dark Command Center Dashboard
───────────────────────────────
A full-featured web dashboard at localhost:9000 showing:
  - Live status of all Makima systems
  - Memory browser (search + view past conversations)
  - Skill manager (view, run, delete learned skills)
  - Background service monitor (WhatsApp, Email, Files activity)
  - Health stats
  - Habit tracker
  - Voice command input
  - Settings panel

Much richer than the basic web dashboard.
Open with: "Open command center" or visit http://localhost:9000
"""

import os
import json
import time
import logging
import threading
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("Makima.CommandCenter")
PORT = int(os.getenv("MAKIMA_CC_PORT", "9000"))

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Makima — Command Center</title>
<style>
:root {
  --bg: #07070f;
  --bg2: #0e0e1a;
  --bg3: #141426;
  --border: #1e1e35;
  --accent: #c084fc;
  --accent2: #a855f7;
  --green: #4ade80;
  --yellow: #fbbf24;
  --red: #f87171;
  --blue: #60a5fa;
  --text: #e0d4f7;
  --dim: #6b6b8a;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,sans-serif; min-height:100vh; }

/* Layout */
.layout { display:grid; grid-template-columns:220px 1fr; min-height:100vh; }
.sidebar { background:var(--bg2); border-right:1px solid var(--border); padding:20px 0; }
.main { padding:24px; overflow-y:auto; }

/* Sidebar */
.logo { text-align:center; padding:0 20px 24px; border-bottom:1px solid var(--border); }
.logo h1 { font-size:1.4rem; color:var(--accent); letter-spacing:4px; }
.logo p { font-size:0.7rem; color:var(--dim); margin-top:4px; }
.nav-item { display:flex; align-items:center; gap:10px; padding:10px 20px; cursor:pointer;
            color:var(--dim); font-size:0.85rem; transition:all 0.2s; }
.nav-item:hover, .nav-item.active { background:var(--bg3); color:var(--accent); border-right:2px solid var(--accent); }
.nav-item .icon { font-size:1rem; width:20px; }

/* Status bar */
.status-bar { display:flex; align-items:center; gap:8px; padding:8px 20px;
              background:var(--bg3); border-bottom:1px solid var(--border);
              font-size:0.75rem; color:var(--dim); }
.status-dot { width:8px; height:8px; border-radius:50%; }
.status-dot.online { background:var(--green); box-shadow:0 0 6px var(--green); }
.status-dot.busy { background:var(--yellow); box-shadow:0 0 6px var(--yellow); }

/* Cards */
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(280px,1fr)); gap:16px; margin-bottom:24px; }
.card { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:20px; }
.card-title { font-size:0.7rem; text-transform:uppercase; letter-spacing:2px; color:var(--dim); margin-bottom:12px; }
.card-value { font-size:1.6rem; font-weight:700; color:var(--accent); }
.card-sub { font-size:0.75rem; color:var(--dim); margin-top:4px; }

/* Command input */
.cmd-section { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:20px; margin-bottom:24px; }
.cmd-title { font-size:0.7rem; text-transform:uppercase; letter-spacing:2px; color:var(--dim); margin-bottom:12px; }
.cmd-row { display:flex; gap:10px; }
.cmd-input { flex:1; background:var(--bg3); border:1px solid var(--border); border-radius:8px;
             padding:12px 16px; color:var(--text); font-size:0.9rem; outline:none; }
.cmd-input:focus { border-color:var(--accent); }
.btn { padding:12px 20px; background:var(--accent2); color:white; border:none; border-radius:8px;
       cursor:pointer; font-size:0.85rem; font-weight:600; transition:background 0.2s; }
.btn:hover { background:var(--accent); }
.btn.sm { padding:6px 14px; font-size:0.75rem; }
.btn.danger { background:#7f1d1d; color:var(--red); }
.btn.danger:hover { background:#991b1b; }

/* Chat log */
.chat-log { background:var(--bg3); border-radius:8px; padding:16px;
             max-height:300px; overflow-y:auto; margin-top:12px; }
.msg { margin:6px 0; font-size:0.85rem; line-height:1.5; }
.msg.user { color:var(--blue); }
.msg.makima { color:var(--text); }
.msg .label { font-weight:700; margin-right:6px; }

/* Tables */
.table { width:100%; border-collapse:collapse; font-size:0.82rem; }
.table th { text-align:left; padding:8px 12px; color:var(--dim); font-weight:600;
             border-bottom:1px solid var(--border); font-size:0.7rem; text-transform:uppercase; letter-spacing:1px; }
.table td { padding:10px 12px; border-bottom:1px solid var(--border); }
.table tr:hover td { background:var(--bg3); }
.badge { display:inline-block; padding:2px 8px; border-radius:20px; font-size:0.7rem; font-weight:600; }
.badge.green { background:#14532d; color:var(--green); }
.badge.yellow { background:#451a03; color:var(--yellow); }
.badge.red { background:#450a0a; color:var(--red); }
.badge.purple { background:#3b0764; color:var(--accent); }

/* Activity log */
.activity-item { display:flex; gap:12px; padding:8px 0; border-bottom:1px solid var(--border); font-size:0.8rem; }
.activity-time { color:var(--dim); min-width:50px; }
.activity-service { color:var(--accent); min-width:80px; font-weight:600; }
.activity-text { color:var(--text); }

/* Section */
.section { background:var(--bg2); border:1px solid var(--border); border-radius:12px; padding:20px; margin-bottom:16px; }
.section-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }
.section-title { font-size:0.85rem; font-weight:700; }

/* Quick actions */
.quick-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(140px, 1fr)); gap:8px; }
.quick-btn { padding:10px; background:var(--bg3); border:1px solid var(--border); border-radius:8px;
             text-align:center; cursor:pointer; font-size:0.78rem; color:var(--text); transition:all 0.2s; }
.quick-btn:hover { border-color:var(--accent); color:var(--accent); background:var(--bg2); }
.quick-btn .qi { font-size:1.2rem; display:block; margin-bottom:4px; }

/* Habit bars */
.habit-row { display:flex; align-items:center; gap:12px; padding:8px 0; border-bottom:1px solid var(--border); }
.habit-name { flex:1; font-size:0.82rem; }
.habit-streak { color:var(--yellow); font-size:0.78rem; font-weight:600; min-width:60px; }
.habit-check { font-size:1.1rem; }

/* Tab panels */
.panel { display:none; }
.panel.active { display:block; }

/* Scrollbar */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }

/* Glow text */
.glow { color:var(--accent); text-shadow:0 0 12px var(--accent); }
</style>
</head>
<body>
<div class="layout">

  <!-- Sidebar -->
  <div class="sidebar">
    <div class="logo">
      <h1>🌸 MAKIMA</h1>
      <p>AI COMMAND CENTER</p>
    </div>
    <div style="margin-top:16px;">
      <div class="nav-item active" onclick="showPanel('dashboard')"><span class="icon">📊</span> Dashboard</div>
      <div class="nav-item" onclick="showPanel('commands')"><span class="icon">💬</span> Commands</div>
      <div class="nav-item" onclick="showPanel('memory')"><span class="icon">🧠</span> Memory</div>
      <div class="nav-item" onclick="showPanel('services')"><span class="icon">⚙️</span> Services</div>
      <div class="nav-item" onclick="showPanel('health')"><span class="icon">💚</span> Health</div>
      <div class="nav-item" onclick="showPanel('skills')"><span class="icon">🧬</span> Skills</div>
      <div class="nav-item" onclick="showPanel('shortcuts')"><span class="icon">⚡</span> Shortcuts</div>
      <div class="nav-item" onclick="showPanel('settings')"><span class="icon">🛠</span> Settings</div>
    </div>
  </div>

  <!-- Main -->
  <div class="main">
    <!-- Status bar -->
    <div class="status-bar">
      <div class="status-dot online" id="statusDot"></div>
      <span id="statusText">Makima is online</span>
      <span style="margin-left:auto;" id="clockText"></span>
    </div>

    <!-- DASHBOARD -->
    <div class="panel active" id="panel-dashboard">
      <div class="grid" style="margin-top:16px;">
        <div class="card">
          <div class="card-title">AI Status</div>
          <div class="card-value glow" id="aiEngine">—</div>
          <div class="card-sub" id="aiPersona">Loading...</div>
        </div>
        <div class="card">
          <div class="card-title">Memory Entries</div>
          <div class="card-value" id="memCount">—</div>
          <div class="card-sub">Total conversations stored</div>
        </div>
        <div class="card">
          <div class="card-title">Battery</div>
          <div class="card-value" id="battLevel">—</div>
          <div class="card-sub" id="battStatus">—</div>
        </div>
        <div class="card">
          <div class="card-title">CPU / RAM</div>
          <div class="card-value" id="cpuVal">—</div>
          <div class="card-sub" id="ramVal">—</div>
        </div>
      </div>

      <div class="section">
        <div class="section-header">
          <div class="section-title">⚡ Quick Actions</div>
        </div>
        <div class="quick-grid" id="quickActions">
          <div class="quick-btn" onclick="sendCmd('status')"><span class="qi">📊</span>Status</div>
          <div class="quick-btn" onclick="sendCmd('morning briefing')"><span class="qi">🌅</span>Briefing</div>
          <div class="quick-btn" onclick="sendCmd('battery status')"><span class="qi">🔋</span>Battery</div>
          <div class="quick-btn" onclick="sendCmd('screenshot')"><span class="qi">📸</span>Screenshot</div>
          <div class="quick-btn" onclick="sendCmd('start focus')"><span class="qi">🎯</span>Focus Mode</div>
          <div class="quick-btn" onclick="sendCmd('check my emails')"><span class="qi">📧</span>Emails</div>
          <div class="quick-btn" onclick="sendCmd('memory stats')"><span class="qi">🧠</span>Memory</div>
          <div class="quick-btn" onclick="sendCmd('health summary')"><span class="qi">💚</span>Health</div>
          <div class="quick-btn" onclick="sendCmd('what did you do in background')"><span class="qi">🔄</span>BG Activity</div>
          <div class="quick-btn" onclick="sendCmd('lock pc')"><span class="qi">🔒</span>Lock PC</div>
          <div class="quick-btn" onclick="sendCmd('list shortcuts')"><span class="qi">⚡</span>Shortcuts</div>
          <div class="quick-btn" onclick="sendCmd('list skills')"><span class="qi">🧬</span>Skills</div>
        </div>
      </div>

      <div class="section">
        <div class="section-header"><div class="section-title">📋 Recent Activity</div></div>
        <div id="recentActivity">Loading...</div>
      </div>
    </div>

    <!-- COMMANDS -->
    <div class="panel" id="panel-commands">
      <div class="cmd-section" style="margin-top:16px;">
        <div class="cmd-title">Send Command</div>
        <div class="cmd-row">
          <input class="cmd-input" id="cmdInput" type="text" placeholder="Type any command..." autofocus>
          <button class="btn" onclick="sendCmd()">Send</button>
        </div>
        <div class="chat-log" id="chatLog">
          <div class="msg makima"><span class="label" style="color:var(--accent)">Makima:</span>Command center ready. Send a command!</div>
        </div>
      </div>
    </div>

    <!-- MEMORY -->
    <div class="panel" id="panel-memory">
      <div class="section" style="margin-top:16px;">
        <div class="section-header">
          <div class="section-title">🧠 Memory Search</div>
        </div>
        <div class="cmd-row" style="margin-bottom:16px;">
          <input class="cmd-input" id="memSearch" type="text" placeholder="Search memories...">
          <button class="btn" onclick="searchMemory()">Search</button>
        </div>
        <div id="memResults">Enter a search term to find past conversations.</div>
      </div>
    </div>

    <!-- SERVICES -->
    <div class="panel" id="panel-services">
      <div class="section" style="margin-top:16px;">
        <div class="section-header"><div class="section-title">⚙️ Background Services</div></div>
        <div id="servicesStatus">Loading...</div>
        <div style="margin-top:16px;">
          <button class="btn sm" onclick="sendCmd('enable whatsapp auto-reply')">Enable WhatsApp</button>
          <button class="btn sm" onclick="sendCmd('disable whatsapp auto-reply')" style="margin-left:8px;">Disable WhatsApp</button>
          <button class="btn sm" onclick="sendCmd('sync memory to cloud')" style="margin-left:8px;">Cloud Sync</button>
        </div>
        <div class="section-header" style="margin-top:20px;"><div class="section-title">📋 Activity Log</div></div>
        <div id="activityLog">Loading...</div>
      </div>
    </div>

    <!-- HEALTH -->
    <div class="panel" id="panel-health">
      <div class="section" style="margin-top:16px;">
        <div class="section-header"><div class="section-title">💚 Health & Habits</div></div>
        <div id="healthData">Loading...</div>
        <div style="margin-top:16px;">
          <button class="btn sm" onclick="sendCmd('water reminder every 30 minutes')">💧 Water Reminder</button>
          <button class="btn sm" onclick="sendCmd('take a break')" style="margin-left:8px;">⏸ Take Break</button>
          <button class="btn sm" onclick="sendCmd('health summary')" style="margin-left:8px;">📊 Summary</button>
        </div>
      </div>
    </div>

    <!-- SKILLS -->
    <div class="panel" id="panel-skills">
      <div class="section" style="margin-top:16px;">
        <div class="section-header"><div class="section-title">🧬 Learned Skills</div></div>
        <div id="skillsList">Loading...</div>
        <div style="margin-top:16px;">
          <input class="cmd-input" id="learnInput" type="text" placeholder="Teach me how to..." style="margin-bottom:8px;">
          <button class="btn sm" onclick="teachSkill()">Teach Skill</button>
        </div>
      </div>
    </div>

    <!-- SHORTCUTS -->
    <div class="panel" id="panel-shortcuts">
      <div class="section" style="margin-top:16px;">
        <div class="section-header"><div class="section-title">⚡ Shortcuts</div></div>
        <div id="shortcutsList">Loading...</div>
        <div style="margin-top:16px; display:flex; gap:8px; flex-wrap:wrap;">
          <input class="cmd-input" id="shortcutPhrase" type="text" placeholder="Phrase" style="flex:1;">
          <input class="cmd-input" id="shortcutCmd" type="text" placeholder="Command(s), comma-separated" style="flex:2;">
          <button class="btn sm" onclick="addShortcut()">Add</button>
        </div>
      </div>
    </div>

    <!-- SETTINGS -->
    <div class="panel" id="panel-settings">
      <div class="section" style="margin-top:16px;">
        <div class="section-header"><div class="section-title">🛠 Settings</div></div>
        <table class="table">
          <thead><tr><th>Setting</th><th>Action</th></tr></thead>
          <tbody>
            <tr><td>Voice Speed</td><td>
              <button class="btn sm" onclick="sendCmd('speak faster')">Faster</button>
              <button class="btn sm" onclick="sendCmd('speak slower')" style="margin-left:4px;">Slower</button>
            </td></tr>
            <tr><td>AI Persona</td><td>
              <button class="btn sm" onclick="sendCmd('switch to makima mode')">Makima</button>
              <button class="btn sm" onclick="sendCmd('switch to normal mode')" style="margin-left:4px;">Normal</button>
              <button class="btn sm" onclick="sendCmd('switch to date mode')" style="margin-left:4px;">Date</button>
            </td></tr>
            <tr><td>Translation</td><td>
              <input class="cmd-input" id="langInput" type="text" placeholder="Language name" style="width:140px;">
              <button class="btn sm" onclick="setLang()" style="margin-left:4px;">Set</button>
              <button class="btn sm" onclick="sendCmd('turn off translation')" style="margin-left:4px;">Off</button>
            </td></tr>
            <tr><td>Focus Mode</td><td>
              <button class="btn sm" onclick="sendCmd('start focus')">Start</button>
              <button class="btn sm" onclick="sendCmd('stop focus')" style="margin-left:4px;">Stop</button>
            </td></tr>
            <tr><td>Clear History</td><td>
              <button class="btn sm danger" onclick="sendCmd('clear history')">Clear</button>
            </td></tr>
          </tbody>
        </table>
      </div>
    </div>

  </div><!-- main -->
</div><!-- layout -->

<script>
// ─── Navigation ──────────────────────────────────────────────────────────────
function showPanel(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  event.currentTarget.classList.add('active');
}

// ─── Clock ────────────────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  document.getElementById('clockText').textContent = now.toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// ─── API calls ────────────────────────────────────────────────────────────────
async function api(endpoint, body = null) {
  try {
    const opts = body
      ? { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) }
      : { method:'GET' };
    const res = await fetch(endpoint, opts);
    return await res.json();
  } catch(e) {
    return { error: e.message };
  }
}

// ─── Commands ─────────────────────────────────────────────────────────────────
async function sendCmd(cmd = null) {
  const input = document.getElementById('cmdInput');
  const text = cmd || (input ? input.value.trim() : '');
  if (!text) return;

  addChatMsg('user', 'You', text);
  if (input) input.value = '';

  const data = await api('/cmd', { cmd: text });
  addChatMsg('makima', 'Makima', data.response || '(no response)');
}

function addChatMsg(role, label, text) {
  const log = document.getElementById('chatLog');
  if (!log) return;
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  const color = role === 'user' ? 'var(--blue)' : 'var(--accent)';
  div.innerHTML = `<span class="label" style="color:${color}">${label}:</span> ${text}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

document.addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    const active = document.querySelector('.panel.active');
    if (active && active.id === 'panel-commands') sendCmd();
  }
});

// ─── Status polling ───────────────────────────────────────────────────────────
async function pollStatus() {
  const data = await api('/status');
  if (data.error) return;

  if (data.ai_engine) document.getElementById('aiEngine').textContent = data.ai_engine;
  if (data.persona) document.getElementById('aiPersona').textContent = 'Persona: ' + data.persona;
  if (data.memory_count !== undefined) document.getElementById('memCount').textContent = data.memory_count;
  if (data.battery !== undefined) {
    document.getElementById('battLevel').textContent = data.battery + '%';
    document.getElementById('battStatus').textContent = data.plugged ? 'Charging' : 'On battery';
  }
  if (data.cpu !== undefined) document.getElementById('cpuVal').textContent = data.cpu + '%';
  if (data.ram !== undefined) document.getElementById('ramVal').textContent = data.ram + '%';

  if (data.activity) {
    const el = document.getElementById('recentActivity');
    el.innerHTML = data.activity.map(a =>
      `<div class="activity-item">
        <span class="activity-time">${a.time}</span>
        <span class="activity-service">${a.service}</span>
        <span class="activity-text">${a.action} — ${a.detail}</span>
      </div>`
    ).join('') || '<span style="color:var(--dim)">No activity yet.</span>';
  }
}
setInterval(pollStatus, 3000);
pollStatus();

// ─── Memory search ────────────────────────────────────────────────────────────
async function searchMemory() {
  const q = document.getElementById('memSearch').value.trim();
  if (!q) return;
  const data = await api('/memory/search', { q });
  const el = document.getElementById('memResults');
  if (data.results && data.results.length) {
    el.innerHTML = data.results.map(r =>
      `<div style="padding:8px 0;border-bottom:1px solid var(--border);font-size:0.82rem;">${r}</div>`
    ).join('');
  } else {
    el.innerHTML = '<span style="color:var(--dim)">No results found.</span>';
  }
}

// ─── Skills ───────────────────────────────────────────────────────────────────
async function teachSkill() {
  const input = document.getElementById('learnInput');
  const task = input.value.trim();
  if (!task) return;
  const data = await api('/cmd', { cmd: 'learn how to ' + task });
  addChatMsg('makima', 'Makima', data.response || '');
  input.value = '';
}

// ─── Shortcuts ────────────────────────────────────────────────────────────────
async function addShortcut() {
  const phrase = document.getElementById('shortcutPhrase').value.trim();
  const cmd = document.getElementById('shortcutCmd').value.trim();
  if (!phrase || !cmd) return;
  const data = await api('/cmd', { cmd: `teach: ${phrase} = ${cmd}` });
  addChatMsg('makima', 'Makima', data.response || '');
  document.getElementById('shortcutPhrase').value = '';
  document.getElementById('shortcutCmd').value = '';
}

// ─── Language ─────────────────────────────────────────────────────────────────
async function setLang() {
  const lang = document.getElementById('langInput').value.trim();
  if (!lang) return;
  await api('/cmd', { cmd: 'translate to ' + lang });
}
</script>
</body>
</html>"""


class CCHandler(BaseHTTPRequestHandler):
    router = None
    services = None
    memory = None

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            self._send(200, "text/html", HTML.encode())

        elif path == "/status":
            data = self._build_status()
            self._send_json(data)

        else:
            self._send(404, "text/plain", b"Not found")

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")

        if path == "/cmd":
            cmd = body.get("cmd", "")
            response = self.router.route(cmd) if self.router else "Router not connected."
            self._send_json({"response": response})

        elif path == "/memory/search":
            q = body.get("q", "")
            if self.memory:
                results = self.memory.search_memories(q, top_k=5)
            else:
                results = []
            self._send_json({"results": results})

        else:
            self._send(404, "text/plain", b"Not found")

    def _build_status(self) -> dict:
        data = {"ai_engine": "Unknown", "persona": "makima"}
        try:
            import psutil
            batt = psutil.sensors_battery()
            data["cpu"] = psutil.cpu_percent()
            data["ram"] = psutil.virtual_memory().percent
            if batt:
                data["battery"] = round(batt.percent)
                data["plugged"] = batt.power_plugged
        except Exception:
            pass

        if self.router and hasattr(self.router, 'ai'):
            ai_status = self.router.ai.get_status()
            data["ai_engine"] = "Gemini" if ai_status.get("gemini_available") else "Ollama"
            data["persona"] = ai_status.get("persona", "makima")

        if self.memory:
            data["memory_count"] = self.memory.get_stats().get("total_entries", 0)

        if self.services:
            log = self.services.activity_log.recent(8)
            data["activity"] = log

        return data

    def _send(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self._send(200, "application/json", body)


class CommandCenter:
    def __init__(self, router, memory=None, services=None):
        CCHandler.router = router
        CCHandler.memory = memory
        CCHandler.services = services
        self.server = HTTPServer(("0.0.0.0", PORT), CCHandler)

    def start(self):
        logger.info(f"🖥  Command Center: http://localhost:{PORT}")
        self.server.serve_forever()

    def start_in_thread(self):
        t = threading.Thread(target=self.start, daemon=True)
        t.start()
        return f"Command Center running at http://localhost:{PORT}"
