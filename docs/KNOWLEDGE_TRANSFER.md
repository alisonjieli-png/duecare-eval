# Use DueCare knowledge in another harness

DueCare supplies source-backed indicator definitions, complete research cases, response rubrics and concrete follow-up wording through one typed library. A harness can read those materials in Python or through MCP, prepare the same blind benchmark inputs, and keep the exact versions it used. The Baltor exporter packages those interfaces and their files as a candidate for the receiving catalogue.

The transferable knowledge comes from the research: distinguish indicators from legal conclusions, examine how debt and control affect a worker's choices, keep uncertainty visible, and assess useful protection separately from harmful facilitation. Every source retains its scope and date. Model responses, provisional references and independent validation keep their own evidence status.

## What the package provides

| Interface | Useful work |
| --- | --- |
| Python knowledge library | Discover six industry packs; retrieve full visible records, sources, rubrics and templates; prepare chat, Jev-typed or batch inputs. |
| Read-only MCP server | Expose the same nine operations through stdio, plus catalogue, source and rubric resources. |
| Typed Baltor candidate export | Carry exact file hashes, package roles, operation contracts, source identity and explicit candidate status. |
| Five portable skills | Author an industry pack, connect a harness, review evidence, package knowledge and design staged agent evaluations. |

The source catalogue contains nine publications, eleven indicator definitions, eight action templates and eleven follow-up templates. The industry packs contain twelve authored case variants. These counts describe materials available for research; measurements of model performance belong to the dated benchmark records.

## Run the MCP server

From the released checkout, create a Python 3.11+ environment and install the optional MCP dependency:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[mcp]'
duecare-mcp --public-root "$PWD"
```

The command waits for an MCP client on standard input. A host can launch it with this server entry after replacing the path with its reviewed checkout:

```json
{
  "mcpServers": {
    "duecare": {
      "command": "duecare-mcp",
      "args": ["--public-root", "/absolute/path/to/duecare-eval"]
    }
  }
}
```

The adapter uses the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), pinned to 2.2.0. The SDK owns transport and protocol negotiation. The server exposes local, read-only knowledge operations; the harness retains model access, external-action authority and any account integration. This release supplies a server and configuration example. Each host's installed connection has its own verification step.

## Retrieve only what a task needs

The operations are `catalog`, `list_cases`, `get_case_payload`, `prepare_benchmark`, `get_source`, `get_rubric`, `get_indicator`, `get_action_template` and `get_followup_template`.

Start with `catalog`, select a pack, then use `list_cases` to obtain its opaque case handles. A returned case includes the complete visible narrative and user question. Expected answers, intended tiers, group labels and evaluator metadata remain outside target-visible payloads. Generic rubrics are available separately; supplying them to the target model creates an explicit experimental condition.

```python
from duecare_eval.knowledge import KnowledgeLibrary

library = KnowledgeLibrary(".")
pack_id = library.catalog()["packs"][0]["pack_id"]
case_id = library.list_cases(pack_id)["cases"][0]["case_id"]
record = library.get_case_payload(
    pack_id, case_id, profile="chat-messages", include_sources=True
)
print(record["payload_sha256"])
```

Save `payload` and its hash before a benchmark call. Coordinator metadata stays separate from the model's messages. `include_sources` controls whether the prepared input carries its source briefing. Keep that choice separate from a harness instruction, history depth and serving settings when comparing conditions.

The full source archive includes analyst reference answers in its case-pack files. Keep those files in the coordinator's storage during a blind evaluation, outside the target model's filesystem and context. The knowledge API supplies the target-visible projection; an unrestricted copy of the entire archive has a different disclosure scope.

For a worker-help workflow, the harness can retrieve relevant indicator definitions, inspect the source scope, ask a concrete follow-up and select suitable protective wording. An action template supplies language; actual contact, disclosure or reporting still needs the person's circumstances, consent and the host's effect controls. Legal material needs current authoritative verification before consequential use.

## Prepare a Baltor candidate

```bash
python3 tools/export_baltor_candidate.py ../duecare-baltor-candidate
python3 tools/export_baltor_candidate.py ../duecare-baltor-candidate --verify
```

Use a new directory outside the checkout. The exporter preserves existing destinations and selects an explicit public dependency set. The bundle includes candidate metadata, a package file inventory, code-asset cards, operation contracts and the selected files. Source revision, dirty-state information and exact file digests distinguish a working-tree preview from a commit-pinned export.

The extracted candidate carries its own source files and skills. From the candidate root, its MCP entrypoint runs directly:

```bash
python3 -m pip install 'mcp==2.2.0'
python3 files/tools/run_duecare_mcp.py --public-root files
```

For the dependency-free Python library, put `files/src` on the Python import path and construct `KnowledgeLibrary("files")`. The editable-install instructions above apply to the complete Git checkout. The candidate manifest records the receiving catalogue's file and package byte limits separately from the uncapped research service's operating policy.

Baltor's existing `CodeAssetSpec` and `CataloguePackage` contracts own the receiving shape. The candidate has small discovery cards and separately addressable implementation files. A host preloads the verified knowledge snapshot, then selects operations through the same typed edge; SDK and MCP routes reuse that implementation. Discovery, import, execution, assessment and admission each have separate receipts.

The [dated compatibility record](https://github.com/alisonjieli-png/duecare-eval/blob/v0.1.0-rc.8/results/knowledge_transfer_verification_2026-10-01_rc8.json) identifies the tested modules, operation calls and refusal checks. It records local contract compatibility. The downloadable release candidate has its own exact source and file identities.

The exporter preserves the [rights notice](../NOTICE.md) and records unresolved general redistribution rights explicitly. It creates candidate material for Baltor's review path. Live catalogue admission and serving require the receiving system's exact-byte evidence and applicable rights. Compatibility tests and a generated package establish their tested interface behavior, while domain and worker-informed validation remain separate.

## Skills and further work

The [knowledge-packaging skill](../skills/duecare-package-knowledge/SKILL.md) guides cross-project transfer. The [agent-evaluation skill](../skills/duecare-design-agent-evaluation/SKILL.md) designs staged first-person and social-post tests, context/harness comparisons and tool-outcome traces. They join the three [industry, harness and evidence skills](EXTENDING_DUECARE.md#build-a-new-industry-pack).

Staged evaluations need two distinct records: the evidence visible at each turn, and the tool actions and postconditions observed afterwards. The extension chat profile requests categorical answers; spontaneous worker-help prose needs its own response condition. The protection-response validator checks response structure. An action-success claim needs a separate execution and observation record. A versioned study sidecar can preserve those traces without changing existing response schemas or exposing later facts early.

Useful next components have concrete jobs:

- Source refresh: compare primary-source editions, preserve prior text and flag changed legal scope before reuse.
- Staged outcome replay: record what an agent proposed, what a tool executed and what a later observation verified.
- Broader language and industry packs: preserve original text, translations, adaptations and matched counterevidence as distinct records.
- Retrieval-benefit trials: hold the case, model and harness settings fixed while comparing work with and without the supplied DueCare material.
- Catalogue handoff: attach independent review to an exact candidate digest, then verify discovery and delivery through the receiving system.

These are follow-up development and assessment tasks. The current release provides the knowledge interface, read-only transport, candidate packaging and skills needed to start them. The continuous private benchmark service keeps its own journals; this interface transfers reviewed materials and prepared tests without launching model calls.
