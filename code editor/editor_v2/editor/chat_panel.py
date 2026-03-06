"""
AI Chat panel — pluggable agent interface.
Users can configure any API endpoint (OpenAI, Anthropic, Ollama, custom).
"""
import json
import os
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QFrame, QComboBox, QLineEdit,
    QSizePolicy, QDialog, QFormLayout, QDialogButtonBox,
    QPlainTextEdit
)
from PyQt6.QtGui import QFont, QColor, QDesktopServices
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QUrl
import qtawesome as qta
from editor.themes import get_theme

# Add parent directory pointing to the makima root so we can import core.ai_handler
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".volt_ai_config.json")
PROMPTS_DIR = os.path.join(root_dir, "MAKIMA LAUNCHER", "prompts")


DEFAULT_CONFIGS = {
    "Makima": {
        "url": "",
        "model": "makima-auto",
        "api_key_env": "",
        "headers": {},
        "type": "makima"
    },
    "OpenAI GPT-4": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "headers": {"Content-Type": "application/json"},
        "type": "openai"
    },
    "Anthropic Claude": {
        "url": "https://api.anthropic.com/v1/messages",
        "model": "claude-opus-4-5",
        "api_key_env": "ANTHROPIC_API_KEY",
        "headers": {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        },
        "type": "anthropic"
    },
    "Ollama (local)": {
        "url": "http://localhost:11434/api/chat",
        "model": "llama3",
        "api_key_env": "",
        "headers": {"Content-Type": "application/json"},
        "type": "ollama"
    },
    "Custom": {
        "url": "",
        "model": "",
        "api_key_env": "",
        "headers": {"Content-Type": "application/json"},
        "type": "openai"
    }
}


def load_configs():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return dict(DEFAULT_CONFIGS)


def save_configs(configs):
    with open(CONFIG_FILE, "w") as f:
        json.dump(configs, f, indent=2)


class ApiWorker(QObject):
    """Runs the API call in a thread."""
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    chunk = pyqtSignal(str)

    def __init__(self, config, messages, api_key=""):
        super().__init__()
        self.config = config
        self.messages = messages
        self.api_key = api_key

    def run(self):
        try:
            cfg = self.config
            api_type = cfg.get("type", "openai")

            # Route 1: Makima native AI
            if api_type == "makima":
                from core.ai_handler import AIHandler
                handler = AIHandler()
                
                # Extract system prompt and user input
                sys_prompt = ""
                user_msg = ""
                for m in self.messages:
                    if m["role"] == "system":
                        sys_prompt = m["content"]
                    elif m["role"] == "user":
                        user_msg += m["content"] + "\n\n"
                
                user_msg = user_msg.strip()
                result = handler.generate_response(sys_prompt, user_msg)
                
                self.finished.emit(result)
                return

            # Route 2: External APIs (HTTP)
            import urllib.request, urllib.error
            
            if api_type == "anthropic":
                body = {
                    "model": cfg["model"],
                    "max_tokens": 2048,
                    "messages": [m for m in self.messages if m["role"] != "system"],
                }
                sys_msgs = [m["content"] for m in self.messages if m["role"] == "system"]
                if sys_msgs:
                    body["system"] = sys_msgs[0]
            elif api_type == "ollama":
                body = {"model": cfg["model"], "messages": self.messages, "stream": False}
            else:
                body = {
                    "model": cfg["model"],
                    "messages": self.messages,
                    "max_tokens": 2048,
                }

            headers = dict(cfg.get("headers", {}))
            if self.api_key:
                if api_type == "anthropic":
                    headers["x-api-key"] = self.api_key
                else:
                    headers["Authorization"] = f"Bearer {self.api_key}"

            data = json.dumps(body).encode()
            req = urllib.request.Request(cfg["url"], data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())

            # Extract text
            if api_type == "anthropic":
                text = result.get("content", [{}])[0].get("text", "")
            elif api_type == "ollama":
                text = result.get("message", {}).get("content", "")
            else:
                text = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            self.finished.emit(text)
        except Exception as e:
            self.error.emit(str(e))


class ConfigDialog(QDialog):
    def __init__(self, configs, parent=None):
        super().__init__(parent)
        self.configs = dict(configs)
        self.setWindowTitle("AI Agent Configuration")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        t = get_theme()
        layout = QVBoxLayout(self)

        self.agent_selector = QComboBox()
        self.agent_selector.addItems(self.configs.keys())
        self.agent_selector.currentTextChanged.connect(self._load_agent)
        layout.addWidget(QLabel("Agent:"))
        layout.addWidget(self.agent_selector)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self.model_input = QLineEdit()
        self.key_env_input = QLineEdit()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Or paste key directly (not saved to disk)")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["makima", "openai", "anthropic", "ollama"])
        self.sys_prompt = QPlainTextEdit()
        self.sys_prompt.setPlaceholderText("System prompt (optional)...")
        self.sys_prompt.setFixedHeight(80)

        form.addRow("Name:", self.name_input)
        form.addRow("API URL:", self.url_input)
        form.addRow("Model:", self.model_input)
        form.addRow("API Key ENV:", self.key_env_input)
        form.addRow("API Key:", self.key_input)
        form.addRow("Type:", self.type_combo)
        form.addRow("System prompt:", self.sys_prompt)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save Agent")
        save_btn.clicked.connect(self._save_agent)
        del_btn = QPushButton("Delete Agent")
        del_btn.clicked.connect(self._delete_agent)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        if self.configs:
            self._load_agent(list(self.configs.keys())[0])

    def _load_agent(self, name):
        cfg = self.configs.get(name, {})
        self.name_input.setText(name)
        self.url_input.setText(cfg.get("url", ""))
        self.model_input.setText(cfg.get("model", ""))
        self.key_env_input.setText(cfg.get("api_key_env", ""))
        self.type_combo.setCurrentText(cfg.get("type", "openai"))
        self.sys_prompt.setPlainText(cfg.get("system_prompt", ""))

    def _save_agent(self):
        name = self.name_input.text().strip()
        if not name:
            return
        self.configs[name] = {
            "url": self.url_input.text().strip(),
            "model": self.model_input.text().strip(),
            "api_key_env": self.key_env_input.text().strip(),
            "api_key_direct": self.key_input.text().strip(),
            "type": self.type_combo.currentText(),
            "system_prompt": self.sys_prompt.toPlainText().strip(),
            "headers": {"Content-Type": "application/json"}
        }
        save_configs(self.configs)
        if self.agent_selector.findText(name) == -1:
            self.agent_selector.addItem(name)
        self.agent_selector.setCurrentText(name)

    def _delete_agent(self):
        name = self.agent_selector.currentText()
        if name in self.configs:
            del self.configs[name]
            save_configs(self.configs)
            self.agent_selector.removeItem(self.agent_selector.currentIndex())


class MessageBubble(QFrame):
    def __init__(self, role, content, parent=None):
        super().__init__(parent)
        t = get_theme()
        is_user = role == "user"
        bg = t["chat_user_bg"] if is_user else t["chat_ai_bg"]
        border = t["accent"] if is_user else t["border"]
        align = "right" if is_user else "left"
        prefix = "You" if is_user else "AI"
        prefix_color = t["accent2"] if is_user else t["green"]

        self.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border-radius: 10px;
                border: 1px solid {border};
                margin: 2px {('2px 2px 30px' if is_user else '30px 2px 2px')};
            }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(4)

        # Header
        hdr = QHBoxLayout()
        name_lbl = QLabel(prefix)
        name_lbl.setStyleSheet(f"color: {prefix_color}; font-size: 10px; font-weight: 700; letter-spacing: 1px; border: none; background: transparent;")
        time_lbl = QLabel(datetime.now().strftime("%H:%M"))
        time_lbl.setStyleSheet(f"color: {t['text3']}; font-size: 9px; border: none; background: transparent;")
        if is_user:
            hdr.addStretch()
            hdr.addWidget(time_lbl)
            hdr.addWidget(name_lbl)
        else:
            hdr.addWidget(name_lbl)
            hdr.addWidget(time_lbl)
            hdr.addStretch()
        lay.addLayout(hdr)

        # Content
        content_lbl = QLabel(content)
        content_lbl.setWordWrap(True)
        content_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_lbl.setStyleSheet(f"color: {t['text']}; font-size: 12px; background: transparent; border: none; line-height: 1.5;")
        content_lbl.setFont(QFont("JetBrains Mono", 12))
        lay.addWidget(content_lbl)

        # Copy button
        copy_btn = QPushButton("Copy")
        copy_btn.setFixedHeight(20)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {t['border']}; border-radius: 3px;
                color: {t['text3']}; font-size: 10px; padding: 0 8px;
            }}
            QPushButton:hover {{ color: {t['text']}; border-color: {t['accent']}; }}
        """)
        copy_btn.clicked.connect(lambda: self._copy(content))
        copy_hdr = QHBoxLayout()
        if is_user:
            copy_hdr.addWidget(copy_btn)
            copy_hdr.addStretch()
        else:
            copy_hdr.addStretch()
            copy_hdr.addWidget(copy_btn)
        lay.addLayout(copy_hdr)

    def _copy(self, text):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)


class ChatPanel(QWidget):
    insert_code = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.configs = load_configs()
        self.messages = []
        self._worker_thread = None
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        t = get_theme()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(36)
        header.setStyleSheet(f"background: {t['bg2']}; border-bottom: 1px solid {t['border']};")
        hdr_row = QHBoxLayout(header)
        hdr_row.setContentsMargins(10, 0, 10, 0)
        hdr_row.setSpacing(6)

        lbl = QLabel("AI AGENT")
        lbl.setStyleSheet(f"color: {t['text3']}; font-size: 10px; font-weight: 700; letter-spacing: 2px;")
        hdr_row.addWidget(lbl)
        hdr_row.addStretch()

        self.agent_combo = QComboBox()
        self.agent_combo.addItems(self.configs.keys())
        self.agent_combo.setFixedHeight(24)
        self.agent_combo.setStyleSheet(f"""
            QComboBox {{
                background: {t['bg3']}; border: 1px solid {t['border']};
                border-radius: 4px; padding: 0 6px; color: {t['text2']}; font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {t['bg3']}; border: 1px solid {t['border']}; color: {t['text']};
                selection-background-color: {t['accent']};
            }}
        """)
        hdr_row.addWidget(self.agent_combo)

        cfg_btn = QPushButton()
        cfg_btn.setIcon(qta.icon("fa5s.cog", color=t['text2']))
        cfg_btn.setFixedSize(24, 24)
        cfg_btn.setToolTip("Configure AI agents")
        cfg_btn.clicked.connect(self._open_config)
        cfg_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: %s; }" % t['bg4'])
        hdr_row.addWidget(cfg_btn)

        clear_btn = QPushButton()
        clear_btn.setIcon(qta.icon("fa5s.trash-alt", color=t['text2']))
        clear_btn.setFixedSize(24, 24)
        clear_btn.setToolTip("Clear chat")
        clear_btn.clicked.connect(self._clear_chat)
        clear_btn.setStyleSheet(cfg_btn.styleSheet())
        hdr_row.addWidget(clear_btn)

        layout.addWidget(header)

        # System prompt row (collapsible)
        self.sys_bar = QWidget()
        self.sys_bar.setFixedHeight(30)
        self.sys_bar.setStyleSheet(f"background: {t['bg3']}; border-bottom: 1px solid {t['border']};")
        sys_row = QHBoxLayout(self.sys_bar)
        sys_row.setContentsMargins(10, 0, 10, 0)
        sys_row.setSpacing(6)
        
        sys_lbl = QLabel("System:")
        sys_lbl.setStyleSheet(f"color: {t['text3']}; font-size: 10px; background: transparent; border: none;")
        
        self.prompt_combo = QComboBox()
        self.prompt_combo.addItem("Default Prompt", "") # Default empty maps to config default
        self._load_prompts_dropdown()
        self.prompt_combo.setMinimumWidth(120)
        self.prompt_combo.setStyleSheet(f"""
            QComboBox {{
                background: {t['bg4']}; border: 1px solid {t['border']}; border-radius: 4px;
                color: {t['text2']}; font-size: 11px; padding: 0 4px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {t['bg4']}; border: 1px solid {t['border']}; color: {t['text']};
                selection-background-color: {t['accent']};
            }}
        """)
        
        self.sys_input = QLineEdit()
        self.sys_input.setPlaceholderText("Or type custom prompt here...")
        self.sys_input.setFixedHeight(22)
        self.sys_input.setStyleSheet(f"""
            QLineEdit {{
                background: {t['bg4']}; border: 1px solid {t['border']}; border-radius: 4px;
                color: {t['text2']}; font-size: 11px; padding: 0 8px;
                font-family: 'JetBrains Mono';
            }}
        """)
        
        # When combo changes, reset typed input to avoid confusion
        self.prompt_combo.currentIndexChanged.connect(lambda: self.sys_input.clear())
        
        manage_btn = QPushButton()
        manage_btn.setIcon(qta.icon("fa5s.folder-plus", color=t['accent']))
        manage_btn.setFixedSize(24, 22)
        manage_btn.setToolTip("Open Prompts Folder (Add .txt files here)")
        manage_btn.clicked.connect(self._manage_prompts)
        manage_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: %s; }" % t['bg4'])

        sys_row.addWidget(sys_lbl)
        sys_row.addWidget(self.prompt_combo)
        sys_row.addWidget(self.sys_input)
        sys_row.addWidget(manage_btn)
        
        layout.addWidget(self.sys_bar)

        # Chat scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("chatArea")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f"QScrollArea {{ background: {t['bg']}; border: none; }}")

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet(f"background: {t['bg']};")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_container)
        layout.addWidget(self.scroll)

        # Loading indicator
        self.loading_lbl = QLabel("⏳  AI is thinking...")
        self.loading_lbl.setStyleSheet(f"color: {t['text3']}; font-size: 11px; padding: 4px 12px; background: {t['bg']};")
        self.loading_lbl.hide()
        layout.addWidget(self.loading_lbl)

        # Input area
        input_area = QWidget()
        input_area.setStyleSheet(f"background: {t['bg2']}; border-top: 1px solid {t['border']};")
        ia = QVBoxLayout(input_area)
        ia.setContentsMargins(8, 8, 8, 8)
        ia.setSpacing(6)

        self.chat_input = QTextEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.setPlaceholderText("Ask the AI... (Ctrl+Enter to send)")
        self.chat_input.setMaximumHeight(100)
        self.chat_input.setFont(QFont("JetBrains Mono", 12))
        self.chat_input.installEventFilter(self)
        ia.addWidget(self.chat_input)

        btn_row = QHBoxLayout()
        self.send_btn = QPushButton("Send  ⌤")
        self.send_btn.setObjectName("accent")
        self.send_btn.setFixedHeight(30)
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['accent']}; border: none; border-radius: 6px;
                color: #fff; font-size: 12px; font-weight: 600; padding: 0 16px;
            }}
            QPushButton:hover {{ background: {t['accent2']}; }}
            QPushButton:disabled {{ background: {t['bg4']}; color: {t['text3']}; }}
        """)
        btn_row.addStretch()

        self.code_ctx_btn = QPushButton("+ Add Code Context")
        self.code_ctx_btn.setFixedHeight(28)
        self.code_ctx_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1px solid {t['border']};
                border-radius: 6px; color: {t['text2']}; font-size: 11px; padding: 0 10px;
            }}
            QPushButton:hover {{ border-color: {t['accent']}; color: {t['text']}; }}
        """)
        self.code_ctx_btn.clicked.connect(self._add_code_context)
        btn_row.addWidget(self.code_ctx_btn)
        btn_row.addWidget(self.send_btn)
        ia.addLayout(btn_row)

        layout.addWidget(input_area)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj == self.chat_input and event.type() == QEvent.Type.KeyPress:
            if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and
                    event.modifiers() == Qt.KeyboardModifier.ControlModifier):
                self._send_message()
                return True
        return super().eventFilter(obj, event)

    def _add_code_context(self):
        """Signal parent to insert selected code into chat."""
        self.insert_code.emit("__get_selection__")

    def inject_code(self, code):
        if code:
            current = self.chat_input.toPlainText()
            self.chat_input.setPlainText(current + f"\n```\n{code}\n```\n")

    def _send_message(self):
        text = self.chat_input.toPlainText().strip()
        if not text:
            return
        self.chat_input.clear()
        self._add_bubble("user", text)

        agent_name = self.agent_combo.currentText()
        cfg = self.configs.get(agent_name, {})
        if cfg.get("type") != "makima" and not cfg.get("url"):
            self._add_bubble("assistant", f"⚠️ Agent '{agent_name}' has no URL configured. Open ⚙ to set it up.")
            return

        # Build messages
        messages = []
        
        # Determine system prompt
        sys_text = self.sys_input.text().strip()
        if not sys_text:
            preset_text = self.prompt_combo.currentData()
            if preset_text:
                sys_text = preset_text
            else:
                sys_text = cfg.get("system_prompt", "")
                
        if sys_text:
            messages.append({"role": "system", "content": sys_text})
        messages.extend(self.messages)
        messages.append({"role": "user", "content": text})
        self.messages.append({"role": "user", "content": text})

        # API key
        api_key = cfg.get("api_key_direct", "")
        if not api_key and cfg.get("api_key_env"):
            api_key = os.environ.get(cfg["api_key_env"], "")

        self.send_btn.setEnabled(False)
        self.loading_lbl.show()

        self._worker = ApiWorker(cfg, messages, api_key)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_response)
        self._worker.error.connect(self._on_error)
        self._worker_thread.start()

    def _on_response(self, text):
        self._worker_thread.quit()
        self.messages.append({"role": "assistant", "content": text})
        self._add_bubble("assistant", text)
        self.send_btn.setEnabled(True)
        self.loading_lbl.hide()

    def _on_error(self, err):
        self._worker_thread.quit()
        self._add_bubble("assistant", f"❌ Error: {err}\n\nCheck your API key and URL in ⚙ settings.")
        self.send_btn.setEnabled(True)
        self.loading_lbl.hide()

    def _add_bubble(self, role, content):
        bubble = MessageBubble(role, content)
        # Insert before the trailing stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        # Scroll to bottom
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    def _clear_chat(self):
        self.messages.clear()
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _open_config(self):
        dlg = ConfigDialog(self.configs, self)
        dlg.exec()
        self.configs = load_configs()
        self.agent_combo.clear()
        self.agent_combo.addItems(self.configs.keys())

    def _manage_prompts(self):
        """Open the prompts directory in file explorer."""
        if not os.path.exists(PROMPTS_DIR):
            os.makedirs(PROMPTS_DIR, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(PROMPTS_DIR))

    def _load_prompts_dropdown(self):
        if not os.path.exists(PROMPTS_DIR):
            return
            
        for file in os.listdir(PROMPTS_DIR):
            if file.endswith(".txt"):
                name = os.path.splitext(file)[0].replace("-", " ").title()
                filepath = os.path.join(PROMPTS_DIR, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            self.prompt_combo.addItem(name, content)
                except Exception as e:
                    print(f"Failed to load prompt {file}: {e}")

