# ⚡ Volt Code Editor

A fully professional, feature-rich desktop code editor built with **PyQt6** + **QScintilla**.

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install PyQt6 PyQt6-QScintilla
```

### 2. Run the editor
```bash
python main.py
```

---

## ✨ Features

| Feature | Details |
|---|---|
| **Syntax Highlighting** | Python, JS/TS, JSX/TSX, HTML, CSS/SCSS, C/C++, JSON, SQL, Markdown, YAML, XML, Shell |
| **File Explorer** | Tree view, new/rename/delete files & folders, search filter |
| **Multiple Tabs** | Drag-to-reorder, unsaved indicators (●), close confirmation |
| **Terminal** | Multi-tab integrated terminal, command history, Ctrl+C support |
| **Find & Replace** | Case-sensitive, whole word, regex, Replace All, highlight matches |
| **Line Numbers** | Always-on gutter, configurable edge column (80 chars) |
| **Code Folding** | Boxed-tree fold markers on margin |
| **Auto-Indent** | Smart indent, backspace unindent, indentation guides |
| **Brace Matching** | Matching `{}[]()` highlight |
| **Auto-Complete** | Built-in QScintilla autocomplete (threshold: 2 chars) |
| **Themes** | Dark, Light, Monokai — easily extendable |
| **Code Runner** | Run Python, JS, Shell, Go, Ruby, PHP, Rust directly (F5) |
| **Formatter** | black (Python), prettier (JS/HTML/CSS/JSON) |
| **Zen Mode** | F11 — fullscreen, hides all UI chrome |
| **Zoom** | Ctrl+= / Ctrl+- / Ctrl+0 |
| **AI Chat Panel** | Pluggable agent interface (see below) |
| **Multi-selection** | Multiple cursors via QScintilla |
| **Toggle Comment** | Ctrl+/ for all languages |
| **Duplicate/Move Line** | Ctrl+D, Alt+Up/Down |

---

## 🤖 AI Agent Setup

Open the AI Chat panel (`Ctrl+Shift+A`) and click **⚙** to configure agents.

### OpenAI
```
URL:   https://api.openai.com/v1/chat/completions
Model: gpt-4o
Key:   Set OPENAI_API_KEY environment variable, or paste directly
Type:  openai
```

### Anthropic Claude
```
URL:   https://api.anthropic.com/v1/messages
Model: claude-opus-4-5
Key:   Set ANTHROPIC_API_KEY environment variable, or paste directly
Type:  anthropic
```

### Ollama (local, free)
```bash
# Install Ollama first: https://ollama.ai
ollama pull llama3
```
```
URL:   http://localhost:11434/api/chat
Model: llama3
Key:   (none needed)
Type:  ollama
```

### Custom / Any OpenAI-compatible API
Point to any URL following the OpenAI chat completions format.

Configs are saved to `~/.volt_ai_config.json`.

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New file |
| `Ctrl+O` | Open file |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+Alt+S` | Save All |
| `Ctrl+W` | Close tab |
| `Ctrl+Z / Ctrl+Shift+Z` | Undo / Redo |
| `Ctrl+F` | Find |
| `Ctrl+H` | Find & Replace |
| `Ctrl+G` | Go to line |
| `Ctrl+/` | Toggle comment |
| `Ctrl+D` | Duplicate line |
| `Alt+Up/Down` | Move line up/down |
| `Shift+Alt+F` | Format document |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+\`` | Toggle terminal |
| `Ctrl+Shift+A` | Toggle AI chat |
| `F5` | Run file |
| `F11` | Zen mode |
| `Ctrl+= / -` | Zoom in/out |

---

## 🎨 Adding Custom Themes

Edit `editor/themes.py` and add a new entry to the `THEMES` dict:
```python
"mytheme": {
    "name": "My Theme",
    "bg": "#...",
    # ... (copy structure from existing theme)
}
```

---

## 📁 Project Structure

```
volt_editor/
├── main.py                  # Entry point
├── requirements.txt
├── README.md
└── editor/
    ├── __init__.py
    ├── main_window.py       # Main window + menus + toolbar
    ├── themes.py            # Theme definitions + stylesheet builder
    ├── code_editor.py       # QScintilla editor widget
    ├── tab_manager.py       # Multi-tab management
    ├── file_explorer.py     # File tree sidebar
    ├── terminal.py          # Integrated terminal
    ├── find_replace.py      # Find & Replace bar
    └── chat_panel.py        # AI agent chat interface
```
