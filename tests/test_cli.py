import json
from pathlib import Path
import pytest
from duecare_eval import public_cli


def run(monkeypatch, *arguments):
    monkeypatch.setattr("sys.argv", ["duecare-eval", *arguments])
    public_cli.main()


def test_verify_explains_the_result(monkeypatch, capsys):
    run(monkeypatch, "verify")
    output = capsys.readouterr().out
    assert "937" in output and "Answer keys stay in local reference files" in output


def test_verify_json_remains_available(monkeypatch, capsys):
    run(monkeypatch, "verify", "--json")
    value = json.loads(capsys.readouterr().out)
    assert value["fixture_validation"]["tasks"] == 937 and value["hidden_fields_removed"]


def test_findings_explains_coverage_without_calling_it_accuracy(monkeypatch, capsys):
    run(monkeypatch, "findings")
    output = capsys.readouterr().out
    assert "27,908" not in output  # Keep the two requested denominators visible.
    assert "16,637 of 56,358" in output and "11,271 of 16,800" in output
    assert "Some question variants change meaning" in output


def test_findings_json_matches_released_analysis(monkeypatch, capsys):
    run(monkeypatch, "findings", "--json")
    assert json.loads(capsys.readouterr().out) == json.loads((public_cli.ROOT / "results/release_findings.json").read_text())


def test_missing_file_has_an_actionable_message(monkeypatch, capsys, tmp_path):
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "verify", "--references", str(tmp_path / "missing.jsonl"))
    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "file is missing" in error and "Traceback" not in error


def test_score_requires_both_paths(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "score")
    assert exc.value.code == 2
    assert "--responses" in capsys.readouterr().err


def test_score_rejects_unknown_ids_with_a_clear_message(monkeypatch, capsys, tmp_path):
    response = tmp_path / "response.jsonl"
    response.write_text(json.dumps({"task_id": "not-a-released-task", "decision": {"probability": .5}}) + "\n")
    with pytest.raises(SystemExit):
        run(monkeypatch, "score", "--responses", str(response), "--out", str(tmp_path / "out.json"))
    assert "unique task ID in the selected answer keys" in capsys.readouterr().err


def test_doctor_checks_the_checkout_without_network(monkeypatch, capsys):
    run(monkeypatch, "doctor", "--json")
    value = json.loads(capsys.readouterr().out)
    assert value["ready"] and value["network_used"] is False


def test_doctor_reports_an_incomplete_checkout(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(public_cli, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "doctor")
    assert exc.value.code == 2 and "missing" in capsys.readouterr().out


def test_malformed_json_names_the_file_and_line(monkeypatch, capsys, tmp_path):
    references = tmp_path / "references.jsonl"
    references.write_text('\n{"unfinished":\n')
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, "verify", "--references", str(references))
    error = capsys.readouterr().err
    assert exc.value.code == 2
    assert str(references) in error and "line 2" in error
    assert "JSON object" in error and "Traceback" not in error


def test_score_json_preserves_missing_coverage(monkeypatch, capsys, tmp_path):
    responses = tmp_path / "responses.jsonl"
    responses.write_text("")
    output = tmp_path / "scores.json"
    run(monkeypatch, "score", "--responses", str(responses), "--out", str(output), "--json")
    receipt = json.loads(capsys.readouterr().out)
    result = json.loads(output.read_text())
    assert receipt == {"out": str(output), "requested": 937, "completed": 0}
    assert result["tasks"] == 937 and result["coverage"] == 0


def test_self_check_json_retains_its_software_check_label(monkeypatch, capsys):
    run(monkeypatch, "self-check", "--json")
    result = json.loads(capsys.readouterr().out)
    assert result["kind"] == "SIMULATED_ORACLE_NOT_MODEL_PERFORMANCE"
    assert result["completed"] == result["requested"] == 937
    assert result["invalid"] == 0 and result["coverage"] == 1


@pytest.fixture
def captured_comparisons(monkeypatch):
    from duecare_eval import comparison_analysis
    path = public_cli.ROOT / "results/comparison_2026-09-30"
    value = json.loads((path / "findings.json").read_text())

    def reproduce(selected):
        assert selected == path
        return value

    monkeypatch.setattr(comparison_analysis, "reproduce", reproduce)
    return value


def test_comparisons_shows_exact_shared_counts(monkeypatch, capsys, captured_comparisons):
    run(monkeypatch, "comparisons")
    output = capsys.readouterr().out
    for suite, value in captured_comparisons["suites"].items():
        assert f"{suite}: {value['requested_per_model']:,} requested" in output
        assert f"{value['all_model_intersection']['tasks']:,} usable tasks" in output
        for model, result in value["models"].items():
            name = captured_comparisons["models"][model]["model"]
            assert f"{name}: {result['correct']:,}/{result['usable']:,} correct on usable outputs" in output
        for pair in value["pairwise"]:
            left = captured_comparisons["models"][pair["left"]]["model"]
            right = captured_comparisons["models"][pair["right"]]["model"]
            assert f"{left} / {right}: {pair['matched_tasks']:,}" in output


def test_comparisons_json_keeps_full_analysis(monkeypatch, capsys, captured_comparisons):
    run(monkeypatch, "comparisons", "--json")
    assert json.loads(capsys.readouterr().out) == captured_comparisons
