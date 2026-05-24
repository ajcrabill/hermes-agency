"""Seam tests for the Hermes plugin.

These verify the plugin's surface — register() function, hook
signatures, context resolver, slash-command dispatch — without
needing a running Hermes. Full integration testing happens against
a real Hermes install (manual: install the plugin, run `hermes chat`,
confirm hooks fire).
"""

from __future__ import annotations

import pytest


def test_plugin_module_imports():
    """The plugin package imports cleanly (no eager side effects)."""
    import hermes_agency_plugin
    assert hasattr(hermes_agency_plugin, "register")


def test_register_function_signature():
    """register(ctx) is the documented entry point."""
    from hermes_agency_plugin import register
    import inspect
    sig = inspect.signature(register)
    assert len(sig.parameters) == 1, "register() takes exactly one arg: ctx"


def test_register_wires_expected_hooks():
    """register(ctx) calls ctx.register_hook for each of the 6 lifecycle hooks."""
    from hermes_agency_plugin import register

    class FakeCtx:
        def __init__(self):
            self.hooks_registered = []
            self.commands_registered = []
        def register_hook(self, name, fn):
            self.hooks_registered.append((name, fn.__name__))
        def register_command(self, name, handler, description=""):
            self.commands_registered.append((name, handler.__name__))

    ctx = FakeCtx()
    register(ctx)
    hook_names = [name for name, _ in ctx.hooks_registered]
    assert "pre_llm_call" in hook_names
    assert "pre_tool_call" in hook_names
    assert "post_tool_call" in hook_names
    assert "transform_tool_result" in hook_names    # v0.18
    assert "on_session_start" in hook_names
    assert "on_session_end" in hook_names

    assert any(name == "agency" for name, _ in ctx.commands_registered)


def test_transform_tool_result_passes_write_when_file_exists(tmp_path, monkeypatch):
    """write_file → file exists → no rewrite (returns None)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.hooks import on_transform_tool_result

    target = tmp_path / "output.txt"
    target.write_text("hello")
    result = on_transform_tool_result(
        tool_name="write_file",
        args={"path": str(target)},
        result='{"ok": true, "bytes": 5}',
    )
    assert result is None   # No rewrite — file exists, verifier passes


def test_transform_tool_result_rewrites_when_file_missing(tmp_path, monkeypatch):
    """write_file → file doesn't exist → rewrite with verifier error."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.hooks import on_transform_tool_result

    missing = tmp_path / "does-not-exist.txt"
    result = on_transform_tool_result(
        tool_name="write_file",
        args={"path": str(missing)},
        result='{"ok": true}',
    )
    assert result is not None
    assert "verifier" in result.lower()
    assert "file_exists" in result.lower()


def test_transform_tool_result_patch_checks_contains(tmp_path, monkeypatch):
    """patch → file exists but doesn't contain expected content → rewrite."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.hooks import on_transform_tool_result

    target = tmp_path / "code.py"
    target.write_text("def foo(): pass\n")   # doesn't contain the new content

    result = on_transform_tool_result(
        tool_name="patch",
        args={"path": str(target), "new_string": "def bar(): pass"},
        result='{"ok": true}',
    )
    assert result is not None
    assert "verifier" in result.lower()
    assert "file_contains" in result.lower()


def test_transform_tool_result_passthrough_for_read_tools(tmp_path, monkeypatch):
    """Read-only tools (read_file, search, etc.) get no enforcement."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.hooks import on_transform_tool_result

    # No matter the args or result, read tools pass through
    assert on_transform_tool_result(tool_name="read_file", args={"path": "/whatever"}, result="anything") is None
    assert on_transform_tool_result(tool_name="search", args={"query": "x"}, result="matches") is None
    assert on_transform_tool_result(tool_name="terminal", args={"command": "ls"}, result="files") is None


def test_pre_llm_call_returns_none_when_no_deployment(tmp_path, monkeypatch):
    """No ~/.agency → hook returns None silently (fail-open)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    # Re-import after env change
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.hooks import on_pre_llm_call
    result = on_pre_llm_call(session_id="test", user_message="hi", is_first_turn=True)
    assert result is None


def test_pre_tool_call_allows_read_tools(tmp_path, monkeypatch):
    """Read-only tools are never gated."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.hooks import on_pre_tool_call
    assert on_pre_tool_call(tool_name="read_file", args={"path": "/tmp/foo"}) is None
    assert on_pre_tool_call(tool_name="search", args={"query": "x"}) is None


def test_pre_tool_call_returns_none_when_no_profile(tmp_path, monkeypatch):
    """No configured profile → hook fails open (returns None)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.hooks import on_pre_tool_call
    # write_file would normally be gated, but with no profile we let it through
    result = on_pre_tool_call(tool_name="write_file", args={"path": "x", "content": "y"})
    assert result is None


def test_session_hooks_do_not_raise(tmp_path, monkeypatch):
    """Session start/end hooks never raise — they're observational and fail-open."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.hooks import on_session_start, on_session_end
    # No assertion needed — just that these don't raise
    on_session_start(session_id="test-session", model="test-model", platform="cli")
    on_session_end(session_id="test-session", completed=True, interrupted=False)


def test_agency_slash_command_help():
    """`/agency` (no args) returns help text."""
    from hermes_agency_plugin.commands import handle_agency_command
    help_text = handle_agency_command("")
    assert "agency" in help_text.lower()
    assert "status" in help_text
    assert "capture" in help_text


def test_agency_slash_command_unknown():
    """Unknown subcommand returns an error message + help."""
    from hermes_agency_plugin.commands import handle_agency_command
    response = handle_agency_command("nonexistent-subcommand")
    assert "Unknown" in response or "unknown" in response


def test_context_resolver_returns_none_when_no_yaml(tmp_path, monkeypatch):
    """When deployment.yaml doesn't exist, the resolver returns (None, None)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENCY_HOME", str(tmp_path / ".agency"))
    for mod in [m for m in list(__import__("sys").modules) if "hermes_agency_plugin" in m]:
        del __import__("sys").modules[mod]
    from hermes_agency_plugin.context import current_profile_and_role
    profile, role = current_profile_and_role()
    assert profile is None
    assert role is None
