"""Official-SDK protocol tests connect locally over stdio; model calls: zero."""
import json
import os
from pathlib import Path
import sys

import pytest

mcp = pytest.importorskip("mcp")
import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.shared.exceptions import MCPError

from duecare_eval.knowledge import KnowledgeLibrary, OPERATION_SCHEMAS
from duecare_eval.mcp_server import create_server

ROOT = Path(__file__).resolve().parents[1]


def result_data(result):
    assert not result.is_error
    return result.structured_content or json.loads(result.content[0].text)


@pytest.mark.parametrize("mode,version", [("auto", "2026-07-28"), ("legacy", "2025-11-25")])
def test_official_stdio_negotiation_tools_resources_and_blinding(mode, version):
    async def check():
        params = StdioServerParameters(command=sys.executable,
            args=[str(ROOT / "tools/run_duecare_mcp.py"), "--public-root", str(ROOT)],
            env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": os.defpath})
        with anyio.fail_after(30):
            async with Client(params, mode=mode, read_timeout_seconds=15) as client:
                assert client.protocol_version == version
                tools = (await client.list_tools()).tools
                assert {tool.name for tool in tools} == set(OPERATION_SCHEMAS)
                for tool in tools:
                    assert tool.annotations.read_only_hint and tool.annotations.idempotent_hint
                    assert tool.annotations.destructive_hint is False and tool.annotations.open_world_hint is False
                catalog = result_data(await client.call_tool("catalog", {}))
                pack_id = catalog["packs"][0]["pack_id"]
                cases = result_data(await client.call_tool("list_cases", {"pack_id": pack_id}))
                case_id = cases["cases"][0]["case_id"]
                payload = result_data(await client.call_tool("get_case_payload", {"pack_id": pack_id, "case_id": case_id}))
                assert payload == KnowledgeLibrary(ROOT).get_case_payload(pack_id, case_id)
                text = json.dumps(payload)
                for hidden in ('"evaluator"', '"reference"', '"source_labels"', '"group_id"', '"variant_id"'):
                    assert hidden not in text
                resources = await client.list_resources()
                assert "duecare://catalog" in [str(r.uri) for r in resources.resources]
                resource = await client.read_resource("duecare://catalog")
                assert json.loads(resource.contents[0].text) == catalog
                source = await client.read_resource("duecare://sources/PALERMO_PROTOCOL_2000")
                assert json.loads(source.contents[0].text)["source"]["id"] == "PALERMO_PROTOCOL_2000"
                rubric = await client.read_resource("duecare://rubrics/" + pack_id)
                assert len(json.loads(rubric.contents[0].text)["rubric"]["dimensions"]) == 6
                rejected = await client.call_tool("get_source", {"source_id": "../../private"})
                assert rejected.is_error
                with pytest.raises(MCPError):
                    await client.call_tool("read_file", {"path": "/etc/passwd"})
                for arguments in ({"pack_id": pack_id, "include_sources": "false"},
                                  {"pack_id": pack_id, "include_sources": 1},
                                  {"pack_id": pack_id, "path": "/etc/passwd"}):
                    with pytest.raises(MCPError):
                        await client.call_tool("prepare_benchmark", arguments)
    anyio.run(check)


def test_inprocess_all_operations_are_registered_and_schema_types_match():
    async def check():
        async with Client(create_server(ROOT)) as client:
            tools = (await client.list_tools()).tools
            for tool in tools:
                expected = OPERATION_SCHEMAS[tool.name]
                assert set(tool.input_schema["properties"]) == set(expected["properties"])
                assert set(tool.input_schema.get("required", [])) == set(expected["required"])
                for key, rule in expected["properties"].items():
                    assert tool.input_schema["properties"][key]["type"] == rule["type"]
            assert result_data(await client.call_tool("get_action_template", {"action_id": "private_safety_check"}))["action_id"] == "private_safety_check"
            assert result_data(await client.call_tool("get_followup_template", {"question_id": "exit"}))["question_id"] == "exit"
            assert result_data(await client.call_tool("get_indicator", {"indicator_id": "debt_bondage"}))["indicator_id"] == "debt_bondage"
            prepared = result_data(await client.call_tool("prepare_benchmark", {"pack_id": "duecare-agriculture-starter", "profile": "jev-typed", "include_sources": True}))
            assert prepared["prepared_requests"] == 2 and prepared["model_calls_executed"] == 0
    anyio.run(check)
