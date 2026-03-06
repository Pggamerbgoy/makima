"""
editor_bridge.py — Connects AI tool calls to the live code editor.
Exposes editor operations (read, edit, save, terminal, search) as
callable Python methods that the ChatPanel can invoke on behalf of the AI.
"""
import os
import glob
import subprocess
from typing import Optional


class EditorBridge:
    """
    Bridge between AI agent tool calls and the Volt/Makima editor.
    Holds a reference to the MainWindow and dispatches operations.
    """

    def __init__(self, main_window=None):
        self._win = main_window

    def set_window(self, main_window):
        self._win = main_window

    # ── File Reading ──────────────────────────────────────────────────────

    def read_file(self, path: str, start_line: int = None, end_line: int = None) -> str:
        """Read a file's contents. Optionally restrict to a line range."""
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            return f"Error: File not found — {path}"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if start_line is not None or end_line is not None:
                s = max((start_line or 1) - 1, 0)
                e = min(end_line or len(lines), len(lines))
                selected = lines[s:e]
                header = f"File: {path} (lines {s+1}–{e} of {len(lines)})\n"
                numbered = [f"{i+s+1}|{line}" for i, line in enumerate(selected)]
                return header + "".join(numbered)

            header = f"File: {path} ({len(lines)} lines)\n"
            numbered = [f"{i+1}|{line}" for i, line in enumerate(lines)]
            return header + "".join(numbered)
        except Exception as e:
            return f"Error reading {path}: {e}"

    # ── File Editing ──────────────────────────────────────────────────────

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        """
        Replace `old_text` with `new_text` in a file.
        If the editor has the file open, edits the live buffer.
        Otherwise edits on disk directly.
        """
        path = os.path.abspath(path)
        editor = self._find_open_editor(path)

        if editor:
            # Edit in the live editor buffer
            count = editor.replace_all(old_text, new_text)
            if count > 0:
                return f"✅ Replaced {count} occurrence(s) in the editor buffer for {os.path.basename(path)}."
            else:
                return f"⚠️ Text not found in {os.path.basename(path)}. No changes made."
        else:
            # Edit on disk
            if not os.path.isfile(path):
                return f"Error: File not found — {path}"
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if old_text not in content:
                    return f"⚠️ Text not found in {os.path.basename(path)}. No changes made."
                new_content = content.replace(old_text, new_text)
                count = content.count(old_text)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return f"✅ Replaced {count} occurrence(s) on disk in {os.path.basename(path)}."
            except Exception as e:
                return f"Error editing {path}: {e}"

    def create_file(self, path: str, content: str) -> str:
        """Create a new file with given content."""
        path = os.path.abspath(path)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ Created {path}"
        except Exception as e:
            return f"Error creating {path}: {e}"

    # ── Directory Listing ─────────────────────────────────────────────────

    def list_dir(self, path: str = ".", ignore_hidden: bool = True) -> str:
        """List files and directories at the given path."""
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            return f"Error: Not a directory — {path}"
        try:
            entries = sorted(os.listdir(path))
            if ignore_hidden:
                entries = [e for e in entries if not e.startswith(".")]
            lines = []
            for entry in entries:
                full = os.path.join(path, entry)
                if os.path.isdir(full):
                    lines.append(f"📁 {entry}/")
                else:
                    size = os.path.getsize(full)
                    if size < 1024:
                        sz = f"{size} B"
                    elif size < 1024 * 1024:
                        sz = f"{size // 1024} KB"
                    else:
                        sz = f"{size // (1024*1024)} MB"
                    lines.append(f"📄 {entry}  ({sz})")
            return f"Directory: {path}\n" + "\n".join(lines) if lines else f"Directory {path} is empty."
        except Exception as e:
            return f"Error listing {path}: {e}"

    # ── Terminal / Command Execution ──────────────────────────────────────

    def run_terminal(self, command: str, cwd: str = None, timeout: int = 30) -> str:
        """
        Execute a shell command.
        If editor terminal is available, runs there (visible to user).
        Otherwise runs via subprocess.
        """
        # Try editor's integrated terminal first
        if self._win and hasattr(self._win, "terminal"):
            try:
                self._win.terminal.run_command(command)
                return f"✅ Command sent to integrated terminal: `{command}`"
            except Exception:
                pass

        # Fallback: subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd or os.getcwd(),
                timeout=timeout,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            if result.returncode != 0:
                output += f"\n[exit code: {result.returncode}]"
            return output.strip() or "(no output)"
        except subprocess.TimeoutExpired:
            return f"⚠️ Command timed out after {timeout}s: `{command}`"
        except Exception as e:
            return f"Error running command: {e}"

    # ── Code Search ───────────────────────────────────────────────────────

    def search_in_files(self, query: str, path: str = ".", file_pattern: str = None) -> str:
        """
        Search for a text pattern across files using ripgrep or fallback to Python.
        """
        path = os.path.abspath(path)

        # Try ripgrep first (fast)
        try:
            cmd = ["rg", "--line-number", "--no-heading", "--color=never", query, path]
            if file_pattern:
                cmd.extend(["--glob", file_pattern])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 50:
                    lines = lines[:50]
                    lines.append(f"... (50 of {len(result.stdout.strip().split(chr(10)))} matches shown)")
                return "\n".join(lines)
            return f"No matches found for '{query}' in {path}"
        except FileNotFoundError:
            pass  # ripgrep not installed, fall through
        except Exception:
            pass

        # Fallback: Python search
        matches = []
        for root, _, files in os.walk(path):
            for fname in files:
                if file_pattern and not fname.endswith(file_pattern.replace("*", "")):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if query in line:
                                rel = os.path.relpath(fpath, path)
                                matches.append(f"{rel}:{i}:{line.rstrip()}")
                                if len(matches) >= 50:
                                    matches.append("... (capped at 50 matches)")
                                    return "\n".join(matches)
                except (PermissionError, OSError):
                    continue
        return "\n".join(matches) if matches else f"No matches found for '{query}' in {path}"

    # ── Editor State Queries ──────────────────────────────────────────────

    def get_open_files(self) -> str:
        """List all files currently open in editor tabs."""
        if not self._win or not hasattr(self._win, "tab_manager"):
            return "Editor not connected."
        try:
            qtabs = self._win.tab_manager.tabs  # QTabWidget
            files = []
            for i in range(qtabs.count()):
                tab = qtabs.widget(i)
                if hasattr(tab, "file_path") and tab.file_path:
                    files.append(tab.file_path)
                else:
                    files.append(f"(untitled tab {i})")
            return "Open files:\n" + "\n".join(f"  {f}" for f in files) if files else "No files open."
        except Exception as e:
            return f"Error: {e}"

    def get_active_file(self) -> dict:
        """Get info about the currently active editor tab."""
        if not self._win or not hasattr(self._win, "tab_manager"):
            return {"error": "Editor not connected"}
        try:
            tab = self._win.tab_manager.current_tab()
            if not tab:
                return {"error": "No active editor"}
            editor = tab.editor
            line, col = editor.getCursorPosition()
            return {
                "path": getattr(tab, "file_path", None) or "(untitled)",
                "cursor_line": line + 1,
                "cursor_col": col + 1,
                "total_lines": editor.lines(),
                "is_modified": getattr(tab, "is_modified", False),
            }
        except Exception as e:
            return {"error": str(e)}

    def goto_line(self, path: str, line: int) -> str:
        """Open a file and jump to a specific line."""
        if self._win and hasattr(self._win, "tab_manager"):
            try:
                self._win.tab_manager.open_file(path)
                tab = self._win.tab_manager.current_tab()
                if tab:
                    tab.editor.goto_line(line)
                    return f"Opened {os.path.basename(path)} at line {line}."
            except Exception as e:
                return f"Error: {e}"
        return "Editor not connected."

    # ── VS Code Bridge ────────────────────────────────────────────────────

    def vscode_open(self, path: str, line: int = None) -> str:
        """Open a file in VS Code using CLI."""
        path = os.path.abspath(path)
        try:
            if line:
                cmd = ["code", "--goto", f"{path}:{line}"]
            else:
                cmd = ["code", path]
            subprocess.Popen(cmd, shell=True)
            return f"✅ Opened in VS Code: {path}" + (f" at line {line}" if line else "")
        except FileNotFoundError:
            return "⚠️ VS Code CLI (`code`) not found. Make sure VS Code is installed and in PATH."
        except Exception as e:
            return f"Error opening in VS Code: {e}"

    def vscode_diff(self, file1: str, file2: str) -> str:
        """Open a diff view in VS Code."""
        try:
            subprocess.Popen(["code", "--diff", os.path.abspath(file1), os.path.abspath(file2)], shell=True)
            return f"✅ Opened diff in VS Code."
        except FileNotFoundError:
            return "⚠️ VS Code CLI not found."
        except Exception as e:
            return f"Error: {e}"

    # ── Helpers ────────────────────────────────────────────────────────────

    def _find_open_editor(self, path: str):
        """Find the QsciScintilla editor widget for a given file path."""
        if not self._win or not hasattr(self._win, "tab_manager"):
            return None
        path = os.path.abspath(path)
        qtabs = self._win.tab_manager.tabs  # QTabWidget
        for i in range(qtabs.count()):
            tab = qtabs.widget(i)
            if hasattr(tab, "file_path") and tab.file_path:
                if os.path.abspath(tab.file_path) == path:
                    return tab.editor  # Return the CodeEditor (QsciScintilla)
        return None

    # ── Tool Dispatcher ───────────────────────────────────────────────────

    # Maps tool names from Cursor/Claude prompts to bridge methods.
    TOOL_MAP = {
        "read_file":       "read_file",
        "edit_file":       "edit_file",
        "create_file":     "create_file",
        "list_dir":        "list_dir",
        "run_terminal_cmd": "run_terminal",
        "grep":            "search_in_files",
        "codebase_search": "search_in_files",
        "search_in_files": "search_in_files",
        "get_open_files":  "get_open_files",
        "get_active_file": "get_active_file",
        "goto_line":       "goto_line",
        "vscode_open":     "vscode_open",
        "vscode_diff":     "vscode_diff",
    }

    def dispatch(self, tool_name: str, arguments: dict) -> str:
        """
        Dispatch a tool call to the appropriate method.
        `arguments` is a dict of keyword arguments from the AI's function call.
        """
        method_name = self.TOOL_MAP.get(tool_name)
        if not method_name:
            return f"Unknown tool: {tool_name}"

        method = getattr(self, method_name, None)
        if not method:
            return f"Tool '{tool_name}' not implemented."

        # Map common argument names from Cursor/Claude format to our methods
        mapped_args = self._map_arguments(tool_name, arguments)

        try:
            result = method(**mapped_args)
            if isinstance(result, dict):
                import json
                return json.dumps(result, indent=2)
            return str(result)
        except TypeError as e:
            return f"Tool argument error for {tool_name}: {e}"
        except Exception as e:
            return f"Tool execution error ({tool_name}): {e}"

    def _map_arguments(self, tool_name: str, args: dict) -> dict:
        """Map Cursor/Claude argument names to our method parameter names."""
        mapped = {}

        if tool_name == "read_file":
            mapped["path"] = args.get("target_file", args.get("path", ""))
            if "start_line_one_indexed" in args:
                mapped["start_line"] = args["start_line_one_indexed"]
            elif "start_line" in args:
                mapped["start_line"] = args["start_line"]
            if "end_line_one_indexed_inclusive" in args:
                mapped["end_line"] = args["end_line_one_indexed_inclusive"]
            elif "end_line" in args:
                mapped["end_line"] = args["end_line"]

        elif tool_name == "edit_file":
            mapped["path"] = args.get("target_file", args.get("path", ""))
            mapped["old_text"] = args.get("old_string", args.get("old_text", ""))
            mapped["new_text"] = args.get("new_string", args.get("new_text", args.get("code_edit", "")))

        elif tool_name == "create_file":
            mapped["path"] = args.get("target_file", args.get("path", ""))
            mapped["content"] = args.get("content", args.get("code_edit", ""))

        elif tool_name == "list_dir":
            mapped["path"] = args.get("target_directory", args.get("relative_workspace_path", args.get("path", ".")))

        elif tool_name == "run_terminal_cmd":
            mapped["command"] = args.get("command", "")
            if "cwd" in args:
                mapped["cwd"] = args["cwd"]

        elif tool_name in ("grep", "codebase_search", "search_in_files"):
            mapped["query"] = args.get("query", args.get("pattern", ""))
            mapped["path"] = args.get("path", args.get("target_directories", ["."])[0] if isinstance(args.get("target_directories"), list) and args.get("target_directories") else ".")
            if "glob" in args:
                mapped["file_pattern"] = args["glob"]
            elif "include_pattern" in args:
                mapped["file_pattern"] = args["include_pattern"]

        elif tool_name == "goto_line":
            mapped["path"] = args.get("path", args.get("target_file", ""))
            mapped["line"] = args.get("line", 1)

        elif tool_name == "vscode_open":
            mapped["path"] = args.get("path", args.get("target_file", ""))
            if "line" in args:
                mapped["line"] = args["line"]

        elif tool_name == "vscode_diff":
            mapped["file1"] = args.get("file1", "")
            mapped["file2"] = args.get("file2", "")

        else:
            mapped = args

        return mapped
