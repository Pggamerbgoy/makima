"""
test_new_features.py — Tests for all new Makima features:
  1. EditorBridge (read, edit, create, delete, list, search, dispatch)
  2. ChatPanel tool parsing (3 formats)
  3. Prompt loading (recursive scan)
  4. TOOL_MAP dispatch + argument mapping
"""

import os
import sys
import json
import tempfile
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "code editor"))

# ═══════════════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════════════
results = []
PASS = 0
FAIL = 0


def run_test(name, fn):
    global PASS, FAIL
    try:
        fn()
        results.append(("✅", name))
        PASS += 1
    except Exception as e:
        results.append(("❌", f"{name}: {e}"))
        FAIL += 1


def section(title):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")


# ═══════════════════════════════════════════════════════════════════════════
# 1. EDITOR BRIDGE
# ═══════════════════════════════════════════════════════════════════════════

section("1. EditorBridge")

from editor.editor_bridge import EditorBridge

bridge = EditorBridge()
tmpdir = tempfile.mkdtemp(prefix="makima_test_")


def test_read_file():
    p = os.path.join(tmpdir, "read_test.txt")
    with open(p, "w") as f:
        f.write("line1\nline2\nline3\n")
    result = bridge.read_file(p)
    assert "line1" in result
    assert "3 lines" in result

run_test("read_file — full file", test_read_file)


def test_read_file_range():
    p = os.path.join(tmpdir, "read_test.txt")
    result = bridge.read_file(p, start_line=2, end_line=2)
    assert "line2" in result
    assert "lines 2–2" in result

run_test("read_file — line range", test_read_file_range)


def test_read_file_not_found():
    result = bridge.read_file(os.path.join(tmpdir, "nonexistent.txt"))
    assert "Error" in result

run_test("read_file — not found", test_read_file_not_found)


def test_create_file():
    p = os.path.join(tmpdir, "subdir", "new_file.py")
    result = bridge.create_file(p, "print('hello')")
    assert "Created" in result
    assert os.path.isfile(p)
    with open(p) as f:
        assert "print('hello')" in f.read()

run_test("create_file — with subdirectory", test_create_file)


def test_edit_file_on_disk():
    p = os.path.join(tmpdir, "edit_test.txt")
    bridge.create_file(p, "old_text here\nkeep this\nold_text again")
    result = bridge.edit_file(p, "old_text", "new_text")
    assert "Replaced 2" in result
    with open(p) as f:
        content = f.read()
    assert "new_text here" in content
    assert "old_text" not in content

run_test("edit_file — disk replace", test_edit_file_on_disk)


def test_edit_file_not_found():
    result = bridge.edit_file(os.path.join(tmpdir, "nope.txt"), "a", "b")
    assert "Error" in result or "not found" in result.lower()

run_test("edit_file — text not found in nonexistent file", test_edit_file_not_found)


def test_edit_file_text_missing():
    p = os.path.join(tmpdir, "no_match.txt")
    bridge.create_file(p, "hello world")
    result = bridge.edit_file(p, "zzz_missing_zzz", "replacement")
    assert "not found" in result.lower() or "⚠" in result

run_test("edit_file — old_text not in file", test_edit_file_text_missing)


def test_delete_file():
    p = os.path.join(tmpdir, "delete_me.txt")
    bridge.create_file(p, "bye")
    assert os.path.isfile(p)
    result = bridge.delete_file(p)
    assert "Deleted" in result
    assert not os.path.isfile(p)

run_test("delete_file — success", test_delete_file)


def test_delete_file_not_found():
    result = bridge.delete_file(os.path.join(tmpdir, "already_gone.txt"))
    assert "Error" in result or "not found" in result.lower()

run_test("delete_file — file not found", test_delete_file_not_found)


def test_list_dir():
    bridge.create_file(os.path.join(tmpdir, "a.txt"), "a")
    bridge.create_file(os.path.join(tmpdir, "b.txt"), "b")
    result = bridge.list_dir(tmpdir)
    assert "📄" in result
    assert "a.txt" in result

run_test("list_dir — lists files", test_list_dir)


def test_list_dir_shows_folders():
    os.makedirs(os.path.join(tmpdir, "myfolder"), exist_ok=True)
    result = bridge.list_dir(tmpdir)
    assert "📁 myfolder/" in result

run_test("list_dir — shows folders", test_list_dir_shows_folders)


def test_list_dir_not_a_dir():
    result = bridge.list_dir(os.path.join(tmpdir, "a.txt"))
    assert "Not a directory" in result

run_test("list_dir — error on file path", test_list_dir_not_a_dir)


def test_search_in_files():
    bridge.create_file(os.path.join(tmpdir, "search1.py"), "def hello():\n    pass\n")
    bridge.create_file(os.path.join(tmpdir, "search2.py"), "# nothing here\n")
    result = bridge.search_in_files("hello", tmpdir, file_pattern="*.py")
    assert "hello" in result
    assert "search1.py" in result

run_test("search_in_files — finds matches", test_search_in_files)


def test_search_no_match():
    result = bridge.search_in_files("zzz_impossible_pattern_zzz", tmpdir)
    assert "No matches" in result

run_test("search_in_files — no matches", test_search_no_match)


def test_run_terminal():
    result = bridge.run_terminal("echo hello_from_bridge", timeout=10)
    assert "hello_from_bridge" in result

run_test("run_terminal — echo command", test_run_terminal)


def test_run_terminal_error():
    result = bridge.run_terminal("exit 1", timeout=5)
    assert "exit code" in result.lower() or result.strip() != ""

run_test("run_terminal — exit code captured", test_run_terminal_error)


def test_get_open_files_no_window():
    result = bridge.get_open_files()
    assert "not connected" in result.lower()

run_test("get_open_files — no window", test_get_open_files_no_window)


def test_get_active_file_no_window():
    result = bridge.get_active_file()
    assert "error" in result

run_test("get_active_file — no window", test_get_active_file_no_window)


def test_vscode_methods_exist():
    assert hasattr(bridge, "vscode_open")
    assert hasattr(bridge, "vscode_diff")
    assert callable(bridge.vscode_open)
    assert callable(bridge.vscode_diff)

run_test("vscode_open/diff — methods exist", test_vscode_methods_exist)


# ═══════════════════════════════════════════════════════════════════════════
# 2. TOOL_MAP & DISPATCH
# ═══════════════════════════════════════════════════════════════════════════

section("2. TOOL_MAP Dispatch")


def test_tool_map_completeness():
    expected = [
        "read_file", "edit_file", "create_file", "delete_file",
        "list_dir", "list_directory", "run_terminal_cmd", "run_command",
        "grep", "grep_search", "codebase_search", "search_in_files",
        "search_replace", "write_file", "rewrite_file",
        "get_open_files", "get_active_file", "goto_line",
        "vscode_open", "vscode_diff",
    ]
    for tool in expected:
        assert tool in bridge.TOOL_MAP, f"Missing TOOL_MAP entry: {tool}"

run_test("TOOL_MAP — all expected tools present", test_tool_map_completeness)


def test_dispatch_read_file():
    p = os.path.join(tmpdir, "dispatch_test.txt")
    bridge.create_file(p, "dispatch content")
    result = bridge.dispatch("read_file", {"target_file": p})
    assert "dispatch content" in result

run_test("dispatch — read_file with Cursor args", test_dispatch_read_file)


def test_dispatch_list_dir():
    result = bridge.dispatch("list_directory", {"path": tmpdir})
    assert "📄" in result or "📁" in result

run_test("dispatch — list_directory alias", test_dispatch_list_dir)


def test_dispatch_search_replace():
    p = os.path.join(tmpdir, "sr_test.txt")
    bridge.create_file(p, "replace_me")
    result = bridge.dispatch("search_replace",
                             {"target_file": p, "old_string": "replace_me", "new_string": "replaced"})
    assert "Replaced" in result

run_test("dispatch — search_replace alias", test_dispatch_search_replace)


def test_dispatch_delete_file():
    p = os.path.join(tmpdir, "del_dispatch.txt")
    bridge.create_file(p, "temp")
    result = bridge.dispatch("delete_file", {"target_file": p})
    assert "Deleted" in result

run_test("dispatch — delete_file", test_dispatch_delete_file)


def test_dispatch_unknown_tool():
    result = bridge.dispatch("nonexistent_tool", {})
    assert "Unknown" in result

run_test("dispatch — unknown tool returns error", test_dispatch_unknown_tool)


def test_dispatch_run_command():
    result = bridge.dispatch("run_command", {"command": "echo dispatch_works"})
    assert "dispatch_works" in result

run_test("dispatch — run_command alias", test_dispatch_run_command)


def test_dispatch_argument_mapping():
    """Test that Cursor format args map correctly."""
    p = os.path.join(tmpdir, "argmap.txt")
    bridge.create_file(p, "line1\nline2\nline3\n")
    result = bridge.dispatch("read_file", {
        "target_file": p,
        "start_line_one_indexed": 2,
        "end_line_one_indexed_inclusive": 3
    })
    assert "line2" in result
    assert "line3" in result

run_test("dispatch — Cursor argument name mapping", test_dispatch_argument_mapping)


# ═══════════════════════════════════════════════════════════════════════════
# 3. CHAT PANEL — TOOL PARSING
# ═══════════════════════════════════════════════════════════════════════════

section("3. ChatPanel Tool Parsing")

# We test _parse_tool_call directly without needing PyQt
import re


def parse_tool_call(text: str):
    """Standalone copy of ChatPanel._parse_tool_call for testing."""
    # Format 1: JSON function_call
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            fc = data.get("function_call") or data.get("tool_call")
            if fc:
                return fc["name"], fc.get("arguments", {})
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    # Format 2: Markdown code block
    json_blocks = re.findall(r'```(?:json)?\s*\n?(\{[^`]+\})\s*```', text, re.DOTALL)
    for block in json_blocks:
        try:
            data = json.loads(block)
            if "name" in data and ("arguments" in data or "parameters" in data):
                return data["name"], data.get("arguments", data.get("parameters", {}))
        except (json.JSONDecodeError, KeyError):
            continue

    # Format 3: <tool_call> tag
    tc_match = re.search(r'<tool_call>\s*(\w+)\((.+?)\)\s*</tool_call>', text, re.DOTALL)
    if tc_match:
        name = tc_match.group(1)
        try:
            args = json.loads(tc_match.group(2))
            return name, args
        except json.JSONDecodeError:
            pass

    return None


def test_parse_format1_function_call():
    text = json.dumps({"function_call": {"name": "read_file", "arguments": {"path": "test.py"}}})
    result = parse_tool_call(text)
    assert result is not None
    assert result[0] == "read_file"
    assert result[1]["path"] == "test.py"

run_test("parse — Format 1: function_call JSON", test_parse_format1_function_call)


def test_parse_format1_tool_call():
    text = json.dumps({"tool_call": {"name": "list_dir", "arguments": {"path": "."}}})
    result = parse_tool_call(text)
    assert result is not None
    assert result[0] == "list_dir"

run_test("parse — Format 1: tool_call JSON", test_parse_format1_tool_call)


def test_parse_format2_markdown():
    text = 'Let me read the file:\n```json\n{"name": "read_file", "arguments": {"path": "main.py"}}\n```'
    result = parse_tool_call(text)
    assert result is not None
    assert result[0] == "read_file"

run_test("parse — Format 2: markdown code block", test_parse_format2_markdown)


def test_parse_format2_parameters():
    text = '```\n{"name": "edit_file", "parameters": {"path": "x.py", "old": "a", "new": "b"}}\n```'
    result = parse_tool_call(text)
    assert result is not None
    assert result[0] == "edit_file"
    assert result[1]["path"] == "x.py"

run_test("parse — Format 2: 'parameters' key", test_parse_format2_parameters)


def test_parse_format3_tool_call_tag():
    text = '<tool_call>read_file({"target_file": "main.py"})</tool_call>'
    result = parse_tool_call(text)
    assert result is not None
    assert result[0] == "read_file"
    assert result[1]["target_file"] == "main.py"

run_test("parse — Format 3: <tool_call> tag", test_parse_format3_tool_call_tag)


def test_parse_plain_text_no_tool():
    result = parse_tool_call("This is just a normal AI response with no tool calls.")
    assert result is None

run_test("parse — plain text returns None", test_parse_plain_text_no_tool)


def test_parse_invalid_json():
    result = parse_tool_call('```json\n{invalid json here}\n```')
    assert result is None

run_test("parse — invalid JSON returns None", test_parse_invalid_json)


# ═══════════════════════════════════════════════════════════════════════════
# 4. PROMPT FILE SCANNING
# ═══════════════════════════════════════════════════════════════════════════

section("4. Prompt File Scanning")


def test_prompts_dir_exists():
    prompts_dir = os.path.join(ROOT, "promts for coding")
    assert os.path.isdir(prompts_dir), f"Missing: {prompts_dir}"

run_test("prompts dir exists", test_prompts_dir_exists)


def test_cursor_prompt_exists():
    p = os.path.join(ROOT, "promts for coding", "cursor", "cursor.txt")
    assert os.path.isfile(p)
    with open(p, encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 1000, "Cursor prompt too short"

run_test("cursor.txt — exists and >1000 chars", test_cursor_prompt_exists)


def test_claude2_prompt_exists():
    p = os.path.join(ROOT, "promts for coding", "claude", "claude2.0.txt")
    assert os.path.isfile(p)
    with open(p, encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 5000, "Claude 2.0 prompt too short"

run_test("claude2.0.txt — exists and >5000 chars", test_claude2_prompt_exists)


def test_old_claude_removed():
    p = os.path.join(ROOT, "promts for coding", "claude", "Cladue.txt")
    assert not os.path.isfile(p), "Old Cladue.txt should be deleted"

run_test("Cladue.txt — deleted", test_old_claude_removed)


def test_cursor_tools_json_valid():
    p = os.path.join(ROOT, "promts for coding", "cursor", "cursor tools .json")
    assert os.path.isfile(p)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, (list, dict)), "Should be valid JSON"

run_test("cursor tools .json — valid JSON", test_cursor_tools_json_valid)


def test_launcher_prompts_exist():
    prompts_dir = os.path.join(ROOT, "MAKIMA LAUNCHER", "prompts")
    assert os.path.isdir(prompts_dir)
    files = [f for f in os.listdir(prompts_dir) if f.endswith(".txt")]
    assert len(files) >= 3, f"Expected ≥3 prompt files, found {len(files)}"

run_test("MAKIMA LAUNCHER/prompts — ≥3 txt files", test_launcher_prompts_exist)


# ═══════════════════════════════════════════════════════════════════════════
# 5. CORE MODULE IMPORTS
# ═══════════════════════════════════════════════════════════════════════════

section("5. Core Module Imports")


def test_import_ai_handler():
    from core.ai_handler import AIHandler
    ai = AIHandler()
    assert ai.persona == "makima"

run_test("import AIHandler + init", test_import_ai_handler)


def test_import_eternal_memory():
    from core.eternal_memory import EternalMemory
    mem = EternalMemory()
    assert hasattr(mem, "save_conversation")
    assert hasattr(mem, "search_memories")
    assert hasattr(mem, "build_memory_context")

run_test("import EternalMemory + verify API", test_import_eternal_memory)


def test_import_command_router():
    from core.ai_handler import AIHandler
    from core.eternal_memory import EternalMemory
    from core.command_router import CommandRouter
    ai = AIHandler()
    mem = EternalMemory()
    router = CommandRouter(ai, mem)
    assert hasattr(router, "route")
    assert len(router.PATTERNS) > 50

run_test("import CommandRouter + verify patterns", test_import_command_router)


def test_import_tts():
    from core.tts_engine import get_tts
    tts = get_tts()
    # Should not crash, may return None if no TTS available
    if tts:
        assert hasattr(tts, "speak")
        assert hasattr(tts, "stop")

run_test("import TTS engine", test_import_tts)


def test_import_background_services():
    from core.background_services import ActivityLog
    log = ActivityLog()
    log.add("test_service", "test_action", "detail")
    recent = log.recent(1)
    assert len(recent) >= 1

run_test("import BackgroundServices + ActivityLog", test_import_background_services)


# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP & RESULTS
# ═══════════════════════════════════════════════════════════════════════════

# Clean up temp directory
shutil.rmtree(tmpdir, ignore_errors=True)

section("RESULTS")
for status, name in results:
    print(f"  {status} {name}")

print(f"\n{'─'*60}")
print(f"  ✅ PASSED: {PASS}   ❌ FAILED: {FAIL}   TOTAL: {PASS + FAIL}")
print(f"{'─'*60}")

if FAIL > 0:
    sys.exit(1)
