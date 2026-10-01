"""Optional offline probe using the actual installed Baltor contract readers.

Run with the trusted Baltor environment and its source on PYTHONPATH. This
script writes only a temporary tool-output capture outside either checkout.
It performs no admission, catalogue mutation, provider call or network access.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from duecare_eval.baltor_bridge import PreloadedOperations, REQUEST_VERSION, RECEIVING_CONSTRAINTS, validate_candidate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--baltor-root", required=True, type=Path)
    args = parser.parse_args(argv)
    trusted = args.baltor_root.resolve()
    import loop_engine.core.code_intelligence_assets as C
    import loop_engine.core.mcp_adapter as M
    import loop_engine.core.service_runtime.catalogue_packages as P
    from loop_engine.core.context_artifacts import ContextArtifactManager, ContextArtifactStore, ContextArtifactStoreSpec
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, parse_package_document
    from jsonschema import validate
    if not Path(C.__file__).resolve().is_relative_to(trusted / "src"):
        raise ValueError("imported_baltor_is_not_the_declared_checkout")
    revision = subprocess.run(["git", "-C", str(trusted), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "-C", str(trusted), "status", "--porcelain=v1", "--untracked-files=all"],
                            check=True, capture_output=True, text=True).stdout
    receipt = validate_candidate(args.candidate)
    assert all(getattr(P, name) == value for name, value in RECEIVING_CONSTRAINTS["symbols"].items())
    package = CataloguePackage.from_dict(json.loads((args.candidate / "package.json").read_text()))
    assert parse_package_document(package.document()).package_digest == receipt["package_sha256"]
    specs = [C.CodeAssetSpec.from_dict(value) for value in json.loads((args.candidate / "code-assets.json").read_text())]
    for spec in specs:
        assert C.CodeAssetSpec.from_dict(spec.to_dict()).to_dict() == spec.to_dict()
        assert C.code_asset_record(spec).body["maturity"] == "candidate"
        attempted = []
        try:
            C.execute_code_ref(C.CodeRefExecutionRequest(C.code_asset_capsule(spec).to_ref(),
                lambda reference: attempted.append(reference)))
        except C.CodeAssetAdmissionError:
            pass
        else:
            raise AssertionError("candidate_was_executable")
        assert not attempted
        changed = deepcopy(spec.to_dict())
        changed["output_contract"] += "-changed"
        try:
            C.CodeAssetSpec.from_dict(changed)
        except ValueError:
            pass
        else:
            raise AssertionError("changed_card_digest_accepted")

    operations = PreloadedOperations.from_public_root(args.candidate / "files")
    contracts = json.loads((args.candidate / "operation-contracts.json").read_text())["operations"]
    by_name = {entry["name"]: entry for entry in contracts}
    calls = []
    async def handler(request):
        calls.append(request.tool_name)
        return operations.invoke(request.transport_arguments())

    server = M.McpServerSpec("duecare-candidate", "in_process", tool_allowlist=tuple(by_name))
    transport = M.InjectedMcpTransport([
        M.McpToolSpec(server.server_id, entry["name"], "Offline DueCare " + entry["name"],
                      entry["input_schema"], "pure") for entry in contracts], handler)
    registry = M.McpRegistry()
    registry.register(server, transport)
    socket_attempts = []
    original_socket = socket.socket
    # asyncio uses a local self-pipe socketpair. Internet sockets are refused;
    # permit only its AF_UNIX bookkeeping, with no listening endpoint.
    def guarded_socket(family=socket.AF_INET, *args, **kwargs):
        if family != socket.AF_UNIX:
            socket_attempts.append(family)
            raise AssertionError("network_socket_refused")
        return original_socket(family, *args, **kwargs)

    with tempfile.TemporaryDirectory(prefix="duecare-baltor-contract-") as temporary, patch.object(socket, "socket", guarded_socket):
        services = M.McpInvocationServices(artifact_manager=ContextArtifactManager(
            ContextArtifactStore(ContextArtifactStoreSpec(temporary))))
        assert len(registry.discover(server.server_id)) == len(contracts)
        def invoke(name, **arguments):
            envelope = {"schema": REQUEST_VERSION, "operation": name, "arguments": arguments}
            result = registry.invoke(M.McpCallRequest(server.server_id, name, envelope), services=services)
            assert result.status == "completed", (name, result.error_code, result.error)
            if result.output is None:
                digest = result.output_ref.rsplit("/", 1)[-1]
                raw = (Path(temporary) / "context" / "objects" / digest[:2] / digest).read_bytes()
                assert sha256(raw).hexdigest() == digest
                payload = json.loads(raw)
            else:
                payload = result.output
            validate(payload, by_name[name]["output_schema"])
            return payload["result"]
        catalog = invoke("catalog")
        pack = catalog["packs"][0]["pack_id"]
        case = invoke("list_cases", pack_id=pack)["cases"][0]["case_id"]
        invoke("get_case_payload", pack_id=pack, case_id=case)
        invoke("prepare_benchmark", pack_id=pack)
        invoke("get_source", source_id=catalog["sources"][0]["id"])
        invoke("get_rubric", pack_id=pack)
        invoke("get_indicator", indicator_id=catalog["indicator_ids"][0])
        invoke("get_action_template", action_id=catalog["action_ids"][0])
        invoke("get_followup_template", question_id=catalog["followup_ids"][0])
        count = len(calls)
        for name, arguments in (("catalog", {"schema": "old", "operation": "catalog", "arguments": {}}),
                                ("catalog", {"schema": REQUEST_VERSION, "operation": "catalog", "arguments": {"path": "/private"}}),
                                ("missing", {})):
            result = registry.invoke(M.McpCallRequest(server.server_id, name, arguments), services=services)
            assert result.status == "refused"
        assert len(calls) == count and not socket_attempts
    result = {"schema": "duecare-baltor-contract-probe/1.0.0", "baltor_commit": revision,
        "baltor_worktree_dirty": bool(status.strip()), "baltor_status_sha256": sha256(status.encode()).hexdigest(),
        "baltor_contract_files": {name: sha256((trusted / name).read_bytes()).hexdigest() for name in (
            "src/loop_engine/core/code_intelligence_assets.py", "src/loop_engine/core/mcp_adapter.py",
            "src/loop_engine/core/service_runtime/catalogue_packages.py")},
        "candidate_package_sha256": receipt["package_sha256"], "code_cards_parsed": len(specs),
        "operation_calls_completed": len(calls), "malformed_calls_refused": 3,
        "network_socket_attempts": len(socket_attempts), "model_calls_executed": 0,
        "admitted": False, "served": False, "scope": "Offline installed-contract compatibility, not independent admission or benchmark quality."}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
