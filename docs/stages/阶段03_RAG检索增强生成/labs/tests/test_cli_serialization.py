"""CLI and JSON serialization behavior tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag_lab.cli import build_parser, main
from rag_lab.config import LabConfig
from rag_lab.serialization import dumps, to_jsonable, write_jsonl


def test_cli_demo_and_failures(config: LabConfig, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = config.project_root / "configs/offline.json"
    assert main(["demo", "--config", str(config_path)]) == 0
    demo = json.loads(capsys.readouterr().out)
    assert demo["shape"]["answer_outcome"] == "answered"

    assert main(["failures", "--config", str(config_path), "--scenario", "dimension_mismatch"]) == 0
    failures = json.loads(capsys.readouterr().out)
    assert failures["all_observed"] is True

    assert main(["benchmark", "--config", str(config_path), "--iterations", "1"]) == 0
    measured = json.loads(capsys.readouterr().out)
    assert measured["iterations"] == 1


def test_cli_reports_input_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demo", "--config", "missing.json"]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error["code"] == "CLI_INPUT_ERROR"
    parser = build_parser()
    assert parser.prog == "rag-lab"


def test_serialization_rejects_unknown_values(tmp_path: Path) -> None:
    assert to_jsonable((1, "two")) == [1, "two"]
    assert json.loads(dumps({"value": float(1)})) == {"value": 1.0}
    with pytest.raises(TypeError, match="unsupported"):
        to_jsonable(object())
    with pytest.raises(TypeError, match="keys"):
        to_jsonable({1: "invalid"})
    empty = tmp_path / "empty.jsonl"
    write_jsonl(empty, ())
    assert empty.read_text(encoding="utf-8") == ""
