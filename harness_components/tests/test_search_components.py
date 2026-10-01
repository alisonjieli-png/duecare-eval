"""Pure search conformance and mathematical fixtures, separate from model tests."""
from copy import deepcopy
import ast
import importlib
import json
import math
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DIRECTORY = ROOT / "harness_components/components/search"
NAMES = sorted(path.stem for path in DIRECTORY.glob("*.py") if not path.name.startswith("_"))
MODULES = {name: importlib.import_module("harness_components.components.search." + name) for name in NAMES}
C = importlib.import_module("harness_components.components.search._common")


def run(operation, **payload):
    return MODULES[operation].run(payload)


@pytest.mark.parametrize("name", NAMES)
def test_declared_examples_strict_contract_and_input_immutability(name):
    module = MODULES[name]; spec = module.SPEC
    assert spec["id"] == "search." + name and spec["version"] == "1.0.0"
    assert spec["effects"] == ["pure"] and spec["sources"] and spec["examples"]
    assert all(source.startswith("https://") for source in spec["sources"])
    json.dumps(spec, allow_nan=False)
    for example in spec["examples"]:
        original = deepcopy(example["input"])
        result = module.run(example["input"])
        assert result == example["output"] and example["input"] == original
        C.validate(result, spec["output_schema"], "result")
        json.dumps(result, allow_nan=False)
        with pytest.raises((TypeError, ValueError)):
            module.run({**example["input"], "unknown_argument": True})
    for invalid in (None, [], "request", 3, True):
        with pytest.raises((TypeError, ValueError)): module.run(invalid)


def test_catalogue_population_and_modules_have_no_external_execution_imports():
    assert len(NAMES) == 50 and len({module.SPEC["id"] for module in MODULES.values()}) == 50
    forbidden = {"os", "subprocess", "socket", "sqlite3", "pathlib", "urllib", "requests", "importlib"}
    for path in DIRECTORY.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert not {alias.name.split(".")[0] for alias in node.names} & forbidden
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden


def test_normalization_casefold_combining_marks_and_original_offsets():
    assert run("normalize_query", text=" Ａ  Straße\nCAFÉ ")["query"] == "a strasse café"
    text = "Cafe\u0301, STRASSE Straße"
    result = run("match_phrase", text=text, phrase="café strasse")
    assert result["matches"] == [{"start": 0, "end": 14}]
    for span in result["matches"]: assert text[span["start"]:span["end"]] == "Cafe\u0301, STRASSE"
    assert run("match_any_tokens", text="Straße", terms=["STRASSE"])["matched"]
    assert not run("match_any_tokens", text="redwood", terms=["red"])["matched"]


def test_query_empty_duplicate_phrase_exclusion_and_malformed_quote():
    assert run("match_any_tokens", text="red", terms=[])["matched"] is False
    assert run("match_all_tokens", text="", terms=[])["matched"] is True
    assert run("match_phrase", text="red", phrase="")["matches"] == []
    assert run("match_phrase", text="a a a", phrase="a a")["matches"] == [{"start": 0, "end": 3}, {"start": 2, "end": 5}]
    assert run("evaluate_simple_query", text="anything", query="")["accepted"] is True
    assert not run("evaluate_simple_query", text="red blue", query="+red -blue")["accepted"]
    assert run("evaluate_simple_query", text="red", query="+red blue")["accepted"]
    assert not run("evaluate_simple_query", text="red", query="blue green")["accepted"]
    assert run("parse_simple_query", query="+red +red 'blue sky' -green")["required"] == ["red"]
    with pytest.raises(ValueError): run("parse_simple_query", query='"unclosed')
    with pytest.raises(ValueError): run("parse_simple_query", query="-")
    assert run("expand_prefix", lexicon=["Ｂ", "b", "a"], prefix="")["terms"] == ["a", "b"]


def test_literal_grep_offsets_overlap_special_characters_and_context_merge():
    assert run("grep_records", records=[{"id": "x", "text": "banana"}], needle="ana")["records"][0]["count"] == 2
    assert run("grep_records", records=[{"id": "x", "text": ".*[x]"}], needle=".*")["records"][0]["matches"] == [{"start": 0, "end": 2}]
    assert run("grep_lines", text="a\r\nred\r\nb", needle="red")["lines"] == [{"line": 2, "start": 3, "end": 6, "text": "red"}]
    merged = run("grep_context", text="a\nhit\nb\nhit\nc", needle="hit", before=1, after=1)["contexts"]
    assert len(merged) == 1 and merged[0]["matched_lines"] == [2, 4] and merged[0]["text"] == "a\nhit\nb\nhit\nc"
    assert run("grep_lines", text="abc", needle="")["lines"] == []
    assert run("keyword_in_context", text="αβγ", needle="β", radius=1)["hits"][0] == {"start": 1, "end": 2, "left": "α", "match": "β", "right": "γ"}
    with pytest.raises(ValueError): run("grep_records", records=[{"id": "x", "text": "a"}, {"id": "x", "text": "b"}], needle="a")


def test_index_boolean_and_phrase_queries_preserve_positions():
    index = run("build_inverted_index", documents=[{"id": "b", "text": "a a a"}, {"id": "a", "text": "a b"}, {"id": "empty", "text": ""}])["index"]
    assert run("intersect_postings", index=index, terms=[])["document_ids"] == ["b", "a", "empty"]
    assert run("union_postings", index=index, terms=[])["document_ids"] == []
    assert run("union_postings", index=index, terms=["missing"])["document_ids"] == []
    assert run("positional_phrase", index=index, phrase="a a")["matches"] == [{"id": "b", "positions": [0, 1]}]
    assert run("document_frequencies", index=index)["frequencies"] == {"a": 2, "b": 1}
    corrupt = deepcopy(index); corrupt["postings"]["a"]["b"] = [0, 1, 99]
    with pytest.raises(ValueError): run("document_frequencies", index=corrupt)
    corrupt = deepcopy(index); corrupt["postings"]["a"]["b"] = [0, 0, 1]
    with pytest.raises(ValueError): run("union_postings", index=corrupt, terms=["a"])
    corrupt = deepcopy(index); corrupt["postings"]["a"].pop("a")
    with pytest.raises(ValueError): run("document_frequencies", index=corrupt)
    assert run("build_inverted_index", documents=[])["index"] == {"document_ids": [], "lengths": {}, "postings": {}}


def test_tfidf_raw_tf_idf_cosine_and_zero_vector_convention():
    docs = [{"id": "b", "text": "red red shared"}, {"id": "a", "text": "blue shared"}]
    vectors = run("tfidf_vectors", documents=docs)
    assert vectors["idf"]["shared"] == 0 and vectors["vectors"]["b"]["red"] == pytest.approx(2 * math.log(2))
    result = run("tfidf_rank", documents=docs, query="red", limit=10)["results"]
    assert result[0]["id"] == "b" and result[0]["score"] == 1
    zeros = run("tfidf_rank", documents=docs, query="absent", limit=10)["results"]
    assert [r["id"] for r in zeros] == ["a", "b"] and all(r["score"] == 0 for r in zeros)
    assert run("tfidf_vectors", documents=[]) == {"idf": {}, "vectors": {}}


def test_bm25_matches_independent_formula_and_length_normalization():
    docs = [{"id": "short", "text": "red"}, {"id": "long", "text": "red filler filler"}, {"id": "other", "text": "blue"}]
    k1, b = 1.2, 0.75; average = 5 / 3; idf = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))
    result = run("bm25_rank", documents=docs, query="red red", k1=k1, b=b, limit=3)["results"]
    scores = {row["id"]: row["score"] for row in result}
    expected = idf * (k1 + 1) / (1 + k1 * (1 - b + b / average))
    assert scores["short"] == pytest.approx(expected) and scores["short"] > scores["long"] > scores["other"]
    assert result == run("bm25_rank", documents=docs, query="red", k1=k1, b=b, limit=3)["results"]
    explanation = run("bm25_explain", documents=docs, document_id="short", query="red", k1=k1, b=b)
    assert explanation["score"] == scores["short"] and explanation["terms"][0]["document_frequency"] == 2
    assert run("bm25_rank", documents=[], query="red", k1=k1, b=b, limit=10)["results"] == []
    with pytest.raises(ValueError): run("bm25_rank", documents=docs, query="red", k1=0, b=b, limit=1)
    with pytest.raises(ValueError): run("bm25_rank", documents=docs, query="red", k1=k1, b=2, limit=1)


def test_chunks_cover_exact_offsets_without_redundant_final_chunk():
    text = "a\r\nb\r\n\r\nc"
    paragraphs = run("paragraph_spans", text=text)["paragraphs"]
    assert [p["text"] for p in paragraphs] == ["a\r\nb", "c"]
    for chunk in paragraphs: assert chunk["text"] == text[chunk["start"]:chunk["end"]]
    chars = run("chunk_characters", text="abcdef", size=4, overlap=2)["chunks"]
    assert len(chars) == 2 and chars[-1]["end"] == 6
    assert run("chunk_characters", text="", size=4, overlap=2)["chunks"] == []
    words = run("chunk_tokens", text="  Café, red blue  ", size=2, overlap=1)["chunks"]
    assert [c["text"] for c in words] == ["Café, red", "red blue"]
    for name in ("chunk_characters", "chunk_tokens"):
        with pytest.raises(ValueError): run(name, text="abc", size=2, overlap=2)
        with pytest.raises(ValueError): run(name, text="abc", size=True, overlap=0)


def test_context_union_budget_and_citations():
    passages = [{"id": "a", "text": "first"}, {"id": "b", "text": "too long for budget"}, {"id": "c", "text": "x"}]
    neighbours = run("retrieve_context", passages=passages, selected_ids=["a", "c"], before=1, after=1)["passages"]
    assert neighbours == passages
    result = run("assemble_context", passages=passages, max_characters=8)
    assert result["text"] == "first\n\nx" and result["included_ids"] == ["a", "c"] and result["omitted_ids"] == ["b"]
    for citation in result["citations"]:
        source = next(p["text"] for p in passages if p["id"] == citation["id"])
        assert result["text"][citation["start"]:citation["end"]] == source
    with pytest.raises(ValueError): run("retrieve_context", passages=passages, selected_ids=["unknown"], before=0, after=0)


def test_numeric_vectors_large_values_dimensions_empty_and_nonfinite():
    assert run("cosine_similarity", a=[1e308, 1e308, 1e308, 1e308], b=[1e308, 1e308, 1e308, 1e308])["similarity"] == pytest.approx(1)
    assert run("cosine_similarity", a=[0, 0], b=[2, 3])["similarity"] == 0
    assert run("cosine_similarity", a=[1, 0], b=[-1, 0])["similarity"] == -1
    assert run("l2_distance", a=[], b=[])["distance"] == 0
    assert run("dot_product", a=[], b=[])["dot_product"] == 0
    assert run("jaccard_similarity", a=[], b=[])["similarity"] == 1
    for name in ("cosine_similarity", "dot_product", "l2_distance"):
        with pytest.raises(ValueError): run(name, a=[1], b=[1, 2])
        with pytest.raises(ValueError): run(name, a=[float("nan")], b=[1])
        with pytest.raises(ValueError): run(name, a=[True], b=[1])


def test_rrf_missing_documents_duplicates_and_order_independent_ties():
    result = run("reciprocal_rank_fusion", rankings=[["a", "b"], ["b", "c"]], k=60, limit=3)["results"]
    scores = {row["id"]: row["score"] for row in result}
    assert scores["b"] == pytest.approx(1 / 62 + 1 / 61) and scores["c"] == pytest.approx(1 / 62)
    assert result == run("reciprocal_rank_fusion", rankings=[["b", "c"], ["a", "b"]], k=60, limit=3)["results"]
    with pytest.raises(ValueError): run("reciprocal_rank_fusion", rankings=[["a", "a"]], k=60, limit=3)
    assert run("reciprocal_rank_fusion", rankings=[], k=0, limit=3)["results"] == []
    rankings = [["a", "b", "c"], ["b", "c", "a"], ["c", "a", "b"]] * 13
    forward = run("reciprocal_rank_fusion", rankings=rankings, k=60, limit=3)["results"]
    assert forward == run("reciprocal_rank_fusion", rankings=list(reversed(rankings)), k=60, limit=3)["results"]
    assert [row["id"] for row in forward] == ["a", "b", "c"]


def test_mmr_diversity_and_relevance_endpoints_and_input_order_ties():
    documents = [{"id": "a", "vector": [1, 0]}, {"id": "b", "vector": [1, 0]}, {"id": "c", "vector": [0, 1]}]
    relevance = run("mmr_select", query_vector=[1, 0], documents=documents, lambda_weight=1, limit=3)["selected"]
    diverse = run("mmr_select", query_vector=[1, 0], documents=documents, lambda_weight=0.2, limit=3)["selected"]
    assert [r["id"] for r in relevance] == ["a", "b", "c"]
    assert [r["id"] for r in diverse] == ["a", "c", "b"]
    assert diverse == run("mmr_select", query_vector=[1, 0], documents=list(reversed(documents)), lambda_weight=0.2, limit=3)["selected"]
    with pytest.raises(ValueError): run("mmr_select", query_vector=[1, 0], documents=documents + [documents[0]], lambda_weight=0.5, limit=3)


def test_parameterized_sql_builders_round_trip_in_memory_without_injection():
    connection = sqlite3.connect(":memory:")
    connection.execute('CREATE TABLE docs (id INTEGER, text TEXT)')
    dangerous = "x'; DROP TABLE docs;--"
    query = run("build_insert", table="docs", record={"id": 1, "text": dangerous})
    connection.execute(query["sql"], query["params"])
    select = run("build_select", table="docs", columns=["id", "text"], filters=[{"column": "text", "operator": "=", "value": dangerous}], order_by=[], limit=10, offset=0)
    assert connection.execute(select["sql"], select["params"]).fetchall() == [(1, dangerous)]
    update = run("build_update", table="docs", values={"text": "safe"}, where={"id": 1}); connection.execute(update["sql"], update["params"])
    assert connection.execute('SELECT text FROM docs').fetchone() == ("safe",)
    delete = run("build_delete", table="docs", where={"id": 1}); connection.execute(delete["sql"], delete["params"])
    assert connection.execute('SELECT COUNT(*) FROM docs').fetchone() == (0,)
    connection.close()


def test_sql_null_membership_escape_and_unsafe_identifiers():
    connection = sqlite3.connect(":memory:")
    connection.execute('CREATE TABLE docs (id INTEGER, text TEXT)')
    connection.executemany('INSERT INTO docs VALUES (?, ?)', [(1, "100%_é\\x"), (None, "other"), (2, "100wildcard")])
    escaped = run("escape_like", value="100%_é\\x", escape="\\")
    assert connection.execute('SELECT id FROM docs WHERE text LIKE ? ESCAPE ?', (escaped["pattern"], escaped["escape"])).fetchall() == [(1,)]
    clause = run("build_in_clause", column="id", values=[1, None])
    assert connection.execute('SELECT text FROM docs WHERE ' + clause["sql"], clause["params"]).fetchall() == [("100%_é\\x",), ("other",)]
    assert run("build_in_clause", column="id", values=[])["sql"] == "0"
    query = run("build_select", table="docs", columns=["text"], filters=[{"column": "id", "operator": "=", "value": None}], order_by=[], limit=2, offset=0)
    assert connection.execute(query["sql"], query["params"]).fetchall() == [("other",)]
    for bad in ('docs; DROP TABLE docs', 'a.b', 'x"', '', 'x--', 'x y'):
        with pytest.raises(ValueError): run("quote_identifier", name=bad)
    with pytest.raises(ValueError): run("build_update", table="docs", values={"text": "bad"}, where={})
    with pytest.raises(ValueError): run("build_delete", table="docs", where={})
    with pytest.raises(ValueError): run("escape_like", value="x", escape="%")
    with pytest.raises(ValueError): run("escape_like", value="x\x00y", escape="\\")
    connection.close()


def test_sql_identifier_schema_and_component_agree_on_full_string_boundaries():
    from harness_components.library import validate
    component = MODULES["quote_identifier"]
    for name in ("docs", "order", "_private", "Column2"):
        payload = {"name": name}
        validate(payload, component.SPEC["input_schema"])
        assert component.run(payload)["identifier"] == '"' + name + '"'
    for name in ("docs; DROP TABLE docs", " docs", "docs ", "docs\n", "a.b", "x--", 'x"', "é", ""):
        with pytest.raises((TypeError, ValueError)):
            validate({"name": name}, component.SPEC["input_schema"])
        with pytest.raises((TypeError, ValueError)):
            component.run({"name": name})


def test_fts5_literal_builders_execute_only_in_test_memory():
    connection = sqlite3.connect(":memory:")
    try: connection.execute('CREATE VIRTUAL TABLE docs USING fts5(text)')
    except sqlite3.OperationalError: pytest.skip("SQLite build lacks optional FTS5")
    connection.executemany('INSERT INTO docs(text) VALUES (?)', [("red blue",), ("green",), ('red OR green',), ("café rouge",)])
    query = run("fts5_quote_phrase", text="red OR green")["query"]
    assert connection.execute('SELECT rowid FROM docs WHERE docs MATCH ?', (query,)).fetchall() == [(3,)]
    query = run("fts5_boolean_query", phrases=["red blue", "green"], operator="OR")["query"]
    assert connection.execute('SELECT rowid FROM docs WHERE docs MATCH ? ORDER BY rowid', (query,)).fetchall() == [(1,), (2,), (3,)]
    query = run("fts5_prefix_query", prefix="caf")["query"]
    assert connection.execute('SELECT rowid FROM docs WHERE docs MATCH ?', (query,)).fetchall() == [(4,)]
    query = run("fts5_near_query", phrases=["red", "blue"], distance=0)["query"]
    assert connection.execute('SELECT rowid FROM docs WHERE docs MATCH ?', (query,)).fetchall() == [(1,)]
    for bad in ("x OR y", 'x"*', "", "a_b"):
        with pytest.raises(ValueError): run("fts5_prefix_query", prefix=bad)
    with pytest.raises(ValueError): run("fts5_quote_phrase", text="x\x00y")
    connection.close()


def test_retrieval_metrics_use_explicit_population_and_known_formulas():
    retrieved, relevant = ["a", "b", "c"], ["b", "c", "d"]
    assert run("precision_at_k", retrieved=retrieved, relevant=relevant, k=5) == {"precision": 0.4, "hits": 2, "denominator": 5, "returned_at_k": 3}
    assert run("recall_at_k", retrieved=retrieved, relevant=relevant, k=5)["recall"] == pytest.approx(2 / 3)
    assert run("reciprocal_rank", retrieved=retrieved, relevant=relevant)["reciprocal_rank"] == 0.5
    assert run("average_precision", retrieved=retrieved, relevant=relevant)["average_precision"] == pytest.approx((1 / 2 + 2 / 3) / 3)
    assert run("dcg_at_k", gains=[3, 2, 1], k=3)["dcg"] == pytest.approx(3 + 2 / math.log2(3) + 1 / 2)
    ndcg = run("ndcg_at_k", retrieved=["b", "a"], relevance={"a": 3, "b": 0}, k=2)
    assert ndcg["ndcg"] == pytest.approx(1 / math.log2(3))
    assert run("ndcg_at_k", retrieved=["unjudged"], relevance={"a": 3}, k=1)["ndcg"] == 0
    for name in ("precision_at_k", "recall_at_k"):
        result = run(name, retrieved=[], relevant=[], k=0)
        assert result["denominator"] == 0
    assert run("average_precision", retrieved=[], relevant=[])["average_precision"] == 0
    assert run("mean_reciprocal_rank", queries=[]) == {"mrr": 0, "reciprocal_ranks": [], "query_count": 0}
    for name in ("precision_at_k", "recall_at_k", "reciprocal_rank", "average_precision"):
        kwargs = {"retrieved": ["a", "a"], "relevant": ["a"]}
        if name.endswith("at_k"): kwargs["k"] = 2
        with pytest.raises(ValueError): run(name, **kwargs)
