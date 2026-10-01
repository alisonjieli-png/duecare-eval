"""Strict MCP edge validation and actual offline official-SDK stdio trials."""

import builtins
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import pytest

from harness_components.library import Library, build_catalog
from harness_components.mcp_server import TOOL_SCHEMAS, ToolArgumentError, create_server, validate_tool


PACKAGE = Path(__file__).parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture
def component_library(tmp_path):
    root = tmp_path / "component-library"
    for relative in ("__init__.py", "library.py", "components/__init__.py",
                     "components/text/__init__.py", "components/text/_shared.py", "components/text/email_normalize.py",
                     "components/search/__init__.py", "components/search/_common.py", "components/search/bm25_rank.py"):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PACKAGE / relative, destination)
    query = {"id": "query-example", "type": "query_preset", "title": "Example email query",
             "query": 'site:example.org "email"', "scope": "Unexecuted search query preset.", "tags": ["mailbox"]}
    payload = root / "search_queries/items/ex/example.json"
    write_json(payload, query)
    write_json(root / "search_queries/catalog.jsonl", {**query, "payload_path": "items/ex/example.json",
               "payload_sha256": hashlib.sha256(payload.read_bytes()).hexdigest()})
    skill = root / "skills/example/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: example\ndescription: Example offline instructions.\n---\n\nRead the supplied text.\n", encoding="utf-8")
    upstream = {"id": "upstream.example", "type": "upstream_reference", "title": "Example reference",
                "repository": "example/repository", "upstream_kind": "skill", "path": "skills/example/SKILL.md",
                "source_url": "https://github.com/example/repository/blob/0000000000000000000000000000000000000000/skills/example/SKILL.md",
                "status": "discovered_unreviewed", "installed": False, "verified": False, "license_scope": "unreviewed"}
    upstream_payload = root / "discovery/upstream/items/example.json"
    write_json(upstream_payload, upstream)
    write_json(root / "discovery/upstream/catalog.jsonl", {**upstream, "payload_path": "items/example.json",
               "payload_sha256": hashlib.sha256(upstream_payload.read_bytes()).hexdigest()})
    build_catalog(root)
    return root


@pytest.mark.parametrize("name,arguments", [
    ("harness_summary", {}),
    ("harness_search", {"query": "email"}),
    ("harness_search", {"query": "", "kind": None, "limit": 100000, "offset": 0}),
    ("harness_search", {"query": "", "kind": "upstream_reference", "limit": 1, "offset": 1}),
    ("harness_get", {"id": "text.email_normalize"}),
    ("harness_run", {"id": "text.email_normalize", "payload": {"email": "A@example.org"}}),
])
def test_valid_tool_arguments_do_not_require_sdk(name, arguments):
    assert validate_tool(name, arguments) is None


@pytest.mark.parametrize("name,arguments", [
    ("read_file", {"path": "/etc/passwd"}),
    (None, {}),
    ("harness_summary", None),
    ("harness_summary", {"library_root": "/tmp"}),
    ("harness_search", {"query": 1}),
    ("harness_search", {"query": "email", "limit": "1"}),
    ("harness_search", {"query": "email", "limit": True}),
    ("harness_search", {"query": "email", "limit": 1.0}),
    ("harness_search", {"query": "email", "limit": 0}),
    ("harness_search", {"query": "email", "offset": False}),
    ("harness_search", {"query": "email", "offset": -1}),
    ("harness_search", {"query": "email", "kind": "installed_tool"}),
    ("harness_search", {"query": "email", "path": "/tmp/catalog.json"}),
    ("harness_get", {"id": 1}),
    ("harness_get", {"id": ""}),
    ("harness_get", {"id": "text.email_normalize", "root": "/tmp"}),
    ("harness_run", {"id": "text.email_normalize"}),
    ("harness_run", {"id": "text.email_normalize", "payload": []}),
    ("harness_run", {"id": "text.email_normalize", "payload": None}),
    ("harness_run", {"id": "text.email_normalize", "payload": {"email": float("nan")}}),
    ("harness_run", {"id": "text.email_normalize", "payload": {"email": b"bytes"}}),
    ("harness_run", {"id": "text.email_normalize", "payload": {1: "value"}}),
    ("harness_run", {"id": "text.email_normalize", "payload": {}, "module": "os"}),
])
def test_raw_args_reject_coercion_unknowns_extras_and_non_json(name, arguments):
    with pytest.raises(ToolArgumentError):
        validate_tool(name, arguments)


def test_optional_sdk_failure_is_clear_and_import_is_not_mandatory(component_library, monkeypatch):
    original = builtins.__import__
    def no_sdk(name, *args, **kwargs):
        if name == "mcp.server":
            raise ImportError("optional SDK absent")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_sdk)
    with pytest.raises(RuntimeError, match="optional mcp extra"):
        create_server(component_library)


def result_data(result):
    assert not result.is_error
    return result.structured_content or json.loads(result.content[0].text)


def require_sdk_v2():
    sdk = pytest.importorskip("mcp")
    if not hasattr(sdk, "Client"):
        pytest.skip("protocol tests require the optional official MCP SDK 2.2.0; an older SDK is installed")


@pytest.mark.parametrize("mode,version", [("auto", "2026-07-28"), ("legacy", "2025-11-25")])
def test_actual_stdio_all_tools_strict_args_data_and_hash_boundary(component_library, mode, version):
    require_sdk_v2()
    import anyio
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    from mcp.shared.exceptions import MCPError
    from mcp_types import INVALID_PARAMS

    async def exercise():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "harness_components.mcp_server", "--library-root", str(component_library)],
            cwd=PACKAGE.parent,
            env={"PYTHONPATH": str(PACKAGE.parent), "PYTHONDONTWRITEBYTECODE": "1", "PATH": os.defpath},
        )
        with anyio.fail_after(30):
            async with Client(params, mode=mode, read_timeout_seconds=15) as client:
                assert client.protocol_version == version
                tools = (await client.list_tools()).tools
                assert {tool.name for tool in tools} == set(TOOL_SCHEMAS)
                for tool in tools:
                    assert tool.annotations.read_only_hint is True
                    assert tool.annotations.idempotent_hint is True
                    assert tool.annotations.destructive_hint is False
                    assert tool.annotations.open_world_hint is False
                    assert set(tool.input_schema["properties"]) == set(TOOL_SCHEMAS[tool.name]["properties"])
                    assert set(tool.input_schema.get("required", [])) == set(TOOL_SCHEMAS[tool.name]["required"])
                summary = result_data(await client.call_tool("harness_summary", {}))
                assert summary == Library(component_library).summary()
                assert summary["counts"] == {"function": 2, "query_preset": 1, "skill": 1, "upstream_reference": 1}
                page = result_data(await client.call_tool("harness_search", {"query": "", "limit": 1, "offset": 1}))
                assert page["total_matches"] == 5 and page["next_offset"] == 2
                assert "input_schema" not in page["results"][0]
                descriptor = result_data(await client.call_tool("harness_get", {"id": "text.email_normalize"}))
                assert "input_schema" in descriptor
                query = result_data(await client.call_tool("harness_get", {"id": "query-example"}))
                assert query["payload"]["query"] == 'site:example.org "email"'
                upstream = result_data(await client.call_tool("harness_get", {"id": "upstream.example"}))
                assert upstream["payload"]["installed"] is False and upstream["payload"]["verified"] is False
                result = result_data(await client.call_tool("harness_run", {"id": "text.email_normalize", "payload": {"email": "Case+Tag@EXAMPLE.ORG"}}))
                assert result["result"]["normalized"] == "Case+Tag@example.org"
                example = Library(component_library).get("search.bm25_rank")["examples"][0]
                ranked = result_data(await client.call_tool("harness_run", {"id": "search.bm25_rank", "payload": example["input"]}))
                assert ranked["result"] == example["output"]
                for identifier in ("query-example", "upstream.example", "skill.example", "os.system", "../../private"):
                    assert (await client.call_tool("harness_run", {"id": identifier, "payload": {}})).is_error
                for tool, arguments in (
                    ("read_file", {"path": "/etc/passwd"}),
                    ("harness_summary", {"library_root": "/tmp"}),
                    ("harness_search", {"query": "email", "limit": "1"}),
                    ("harness_search", {"query": "email", "limit": True}),
                    ("harness_search", {"query": "email", "limit": 1.0}),
                    ("harness_search", {"query": "email", "offset": False}),
                    ("harness_get", {"id": 123}),
                    ("harness_run", {"id": "text.email_normalize", "payload": []}),
                    ("harness_run", {"id": "text.email_normalize", "payload": {}, "path": "/tmp"}),
                ):
                    with pytest.raises(MCPError) as rejected:
                        await client.call_tool(tool, arguments)
                    assert rejected.value.code == INVALID_PARAMS
                assert (await client.call_tool("harness_run", {"id": "text.email_normalize", "payload": {"email": 1}})).is_error
                helper = component_library / "components/text/_shared.py"
                helper.write_bytes(helper.read_bytes() + b"\nraise RuntimeError('must never run')\n")
                refused = await client.call_tool("harness_run", {"id": "text.email_normalize", "payload": {"email": "a@example.org"}})
                assert refused.is_error
                assert "changed source dependency" in json.dumps(refused.model_dump(mode="json"))

    anyio.run(exercise)


def test_inprocess_calls_do_not_open_network_or_child_processes(component_library, monkeypatch):
    require_sdk_v2()
    import anyio
    from mcp import Client

    def forbidden(*args, **kwargs):
        raise AssertionError("component tool attempted a network or child-process action")

    async def exercise():
        async with Client(create_server(component_library)) as client:
            monkeypatch.setattr(socket, "create_connection", forbidden)
            monkeypatch.setattr(socket.socket, "connect", forbidden)
            monkeypatch.setattr(subprocess, "Popen", forbidden)
            monkeypatch.setattr(subprocess, "run", forbidden)
            assert result_data(await client.call_tool("harness_summary", {}))["counts"]["function"] == 2
            assert result_data(await client.call_tool("harness_search", {"query": "email"}))["total_matches"] >= 1
            assert result_data(await client.call_tool("harness_get", {"id": "upstream.example"}))["installed"] is False
            result = result_data(await client.call_tool("harness_run", {"id": "text.email_normalize", "payload": {"email": "A@EXAMPLE.ORG"}}))
            assert result["result"]["normalized"] == "A@example.org"

    anyio.run(exercise)
