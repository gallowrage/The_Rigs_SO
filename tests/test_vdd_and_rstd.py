from __future__ import annotations

import importlib.util
from pathlib import Path

import vdd_v3_gate


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_vdd_v3_gate_complexity_audit(tmp_path: Path) -> None:
    clean_file = tmp_path / "clean.py"
    clean_file.write_text(
        "def simple(x: int) -> int:\n"
        "    if x > 0:\n"
        "        return x\n"
        "    return 0\n",
        encoding="utf-8",
    )
    assert vdd_v3_gate.audit_file_complexity(clean_file, max_cc=9) == []
    assert vdd_v3_gate.audit_target(clean_file, max_cc=9) == 0
    assert vdd_v3_gate.main([str(clean_file)]) == 0

    complex_file = tmp_path / "complex.py"
    branches = "\n".join(f"    if x == {i}:\n        return {i}" for i in range(12))
    complex_file.write_text(f"def too_complex(x: int) -> int:\n{branches}\n    return -1\n", encoding="utf-8")

    violations = vdd_v3_gate.audit_file_complexity(complex_file, max_cc=9)
    assert len(violations) == 1
    assert violations[0].function_name == "too_complex"
    assert violations[0].score > 9
    assert vdd_v3_gate.audit_target(complex_file, max_cc=9) == 1


def test_vdd_pre_commit_v3_rules(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    pre_commit = _load_module("vdd_pre_commit_v3", root / "vdd_pre_commit-v3.py")

    bad_py = tmp_path / "bad_code.py"
    bad_py.write_text(
        "from math import *\n"
        "import langchain_core_tools\n"
        "def risky():\n"
        "    while True:\n"
        "        pass\n"
        "    try:\n"
        "        eval('1+1')\n"
        "    except:\n"
        "        pass\n",
        encoding="utf-8",
    )

    record, violations = pre_commit.evaluate_single_file(bad_py, max_complexity=10)
    assert record["passed"] is False
    rule_ids = {v.rule_id for v in violations}
    assert "AST001" in rule_ids
    assert "AST002" in rule_ids
    assert "AST004" in rule_ids
    assert "AST006" in rule_ids
    assert "AST007" in rule_ids
    assert record["rstd_repair_context"] is not None

    req_file = tmp_path / "requirements.txt"
    req_file.write_text("pytest>=8.0.0\nrequests==2.31.0\n", encoding="utf-8")
    dep_violations = pre_commit.check_manifest_dependencies(req_file)
    assert len(dep_violations) == 1
    assert dep_violations[0].rule_id == "DEP001"


def test_rstd_repair_runner_remediations(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    rstd_mod = _load_module("rstd_repair_runner_v3", root / "rstd_repair_runner-v3.py")

    RunnerCls = rstd_mod.RSTDRepairRunner
    assert RunnerCls._remediate_single_line("AST001", "from os import *") == "import os"
    assert "pass" in (RunnerCls._remediate_single_line("AST002", "    eval(x)") or "")
    assert "break" in (RunnerCls._remediate_single_line("AST004", "    while True:") or "")
    assert RunnerCls._remediate_single_line("AST006", "    except:") == "    except Exception:"
    sample_sec_line = "MY_VAR = 'val'"
    assert "os.environ.get" in (RunnerCls._remediate_single_line("SEC001", sample_sec_line) or "")

    target_file = tmp_path / "fixme.py"
    target_file.write_text("from sys import *\nx = 1\n", encoding="utf-8")

    runner = RunnerCls(gate_script=root / "vdd_pre_commit-v3.py", dry_run=False)
    ok = runner._apply_deterministic_remediation(target_file, "AST001", 1)
    assert ok is True
    assert "import sys" in target_file.read_text(encoding="utf-8")

    # Test isolated patch splicing
    window = {"start_line": 2, "end_line": 2}
    assert runner._apply_isolated_patch(target_file, window, "x = 42") is True
    assert "x = 42" in target_file.read_text(encoding="utf-8")
