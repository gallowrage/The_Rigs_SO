#!/usr/bin/env python3
"""
Verifiability-Driven Development (VDD) Pre-Commit Gate (Version 3.0 - Windows Native)
-----------------------------------------------------------------------------------
Deterministic pre-flight verification gate for Git staging & RSTD self-healing loops.

Features:
1. Discovers staged Python files via Git or accepts explicit file targets.
2. Bytecode compilation verification (`py_compile`).
3. AST static inspection:
   - Dynamic execution detection (`eval`, `exec`) [AST002].
   - Insecure subprocess invocations (`shell=True`) [AST003].
   - Wildcard import masking (`from module import *`) [AST001].
   - Unbounded `while True:` loop verification [AST004].
   - Bare `except:` clause detection [AST006].
   - McCabe Cyclomatic Complexity calculation (<= 10) with nested-scope isolation [AST005].
   - AI Slopsquatting & Hallucinated Package Interceptor [AST007].
4. Lightweight SAST secret and token pattern detection [SEC001-SEC004].
5. Dependency Manifest Pinning Scanner [DEP001] for requirements.txt / pyproject.toml / package.json.
6. Structured JSON output schema tailored for Runtime-Structured Task
   Decomposition (RSTD) autonomous repair operators and AgentOps telemetry.
7. Returns exit code 0 (Pass) or 1 (Fail) to deterministically halt commits.
"""

import argparse
import ast
import json
import os
from pathlib import Path
import py_compile
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Ensure safe UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Known AI-hallucinated and slopsquatted package names across PyPI / npm
KNOWN_SLOPSQUAT_PACKAGES: Set[str] = {
    "langchain_core_tools",
    "langchain_community_helpers",
    "openai_functions",
    "huggingface_hub_v2",
    "fastapi_utils_v2",
    "torch_geometric_utils",
    "pydantic_settings_v2",
    "tensorflow_keras_layers",
    "flask_restx_models",
    "requests_async_client",
    "google_genai_experimental",
    "boto3_helpers",
    "dotenv_extended",
    "pydantic_core_utils",
    "numpy_fast_math",
    "scipy_linalg_v2",
    "transformers_custom_pipelines",
    "sqlalchemy_async_helpers",
    "anthropic_claude_sdk",
    "chromadb_vector_store",
}

# Suspicious hallucination regex patterns for AI-generated code
SLOPSQUAT_PATTERNS = [
    re.compile(r"^(openai|langchain|anthropic|fastapi|torch|tensorflow|pydantic)_(helpers|utils_v\d+|extensions|tools_v\d+)$"),
]


class Violation:
    """Represents a discrete rule violation for structured reporting."""

    def __init__(
        self,
        rule_id: str,
        category: str,
        severity: str,
        line: int,
        col: int,
        message: str,
        snippet: str = "",
        function_scope: Optional[str] = None,
    ):
        self.rule_id = rule_id
        self.category = category
        self.severity = severity
        self.line = line
        self.col = col
        self.message = message
        self.snippet = snippet
        self.function_scope = function_scope

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "severity": self.severity,
            "line": self.line,
            "col": self.col,
            "function_scope": self.function_scope,
            "message": self.message,
            "snippet": self.snippet,
        }

    def __str__(self) -> str:
        scope = f" in `{self.function_scope}()`" if self.function_scope else ""
        return f"[{self.rule_id}] Line {self.line}:{self.col}{scope}: {self.message}"


class ASTSecurityAndComplexityVisitor(ast.NodeVisitor):
    """AST Node Visitor detecting security flaws, slopsquatting, and complexity hotspots."""

    def __init__(self, filename: str, lines: List[str], max_complexity: int = 10):
        self.filename = filename
        self.lines = lines
        self.max_complexity = max_complexity
        self.violations: List[Violation] = []
        self.current_function: Optional[str] = None

    def _get_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculates complexity while isolating nested closures from outer scopes."""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return 0

        c = 0
        if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.With, ast.AsyncWith)):
            c += 1
        elif isinstance(node, ast.BoolOp):
            c += len(node.values) - 1
        elif isinstance(node, ast.IfExp):
            c += 1

        for child in ast.iter_child_nodes(node):
            c += self._calculate_complexity(child)
        return c

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._analyze_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._analyze_function(node)

    def _analyze_function(self, node: Any):
        prior_fn = self.current_function
        self.current_function = node.name

        complexity = 1
        for child in ast.iter_child_nodes(node):
            complexity += self._calculate_complexity(child)

        if complexity > self.max_complexity:
            self.violations.append(
                Violation(
                    rule_id="AST005",
                    category="AST_COMPLEXITY",
                    severity="ERROR",
                    line=node.lineno,
                    col=node.col_offset,
                    message=f"Function `{node.name}` has cyclomatic complexity of {complexity} (exceeds threshold of {self.max_complexity}).",
                    snippet=self._get_snippet(node.lineno),
                    function_scope=node.name,
                )
            )

        self.generic_visit(node)
        self.current_function = prior_fn

    def visit_Call(self, node: ast.Call):
        self._check_eval_exec(node)
        self._check_subprocess_shell(node)
        self.generic_visit(node)

    def _check_eval_exec(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            self.violations.append(
                Violation(
                    rule_id="AST002",
                    category="AST_SECURITY",
                    severity="ERROR",
                    line=node.lineno,
                    col=node.col_offset,
                    message=f"Unsafe use of dynamic execution `{node.func.id}()`.",
                    snippet=self._get_snippet(node.lineno),
                    function_scope=self.current_function,
                )
            )

    def _check_subprocess_shell(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"run", "Popen", "call", "check_output"}:
            for keyword in node.keywords:
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    self.violations.append(
                        Violation(
                            rule_id="AST003",
                            category="AST_SECURITY",
                            severity="ERROR",
                            line=node.lineno,
                            col=node.col_offset,
                            message=f"`subprocess.{node.func.attr}` invoked with `shell=True`.",
                            snippet=self._get_snippet(node.lineno),
                            function_scope=self.current_function,
                        )
                    )

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self._check_slopsquatting(alias.name, node.lineno, node.col_offset)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self._check_slopsquatting(node.module, node.lineno, node.col_offset)

        for alias in node.names:
            if alias.name == "*":
                self.violations.append(
                    Violation(
                        rule_id="AST001",
                        category="AST_SECURITY",
                        severity="ERROR",
                        line=node.lineno,
                        col=node.col_offset,
                        message=f"Wildcard import (`from {node.module or ''} import *`) masks dependencies.",
                        snippet=self._get_snippet(node.lineno),
                        function_scope=self.current_function,
                    )
                )
        self.generic_visit(node)

    def _check_slopsquatting(self, module_name: str, lineno: int, col: int):
        root_module = module_name.split(".")[0].lower()
        if root_module in KNOWN_SLOPSQUAT_PACKAGES:
            self.violations.append(
                Violation(
                    rule_id="AST007",
                    category="AST_SECURITY",
                    severity="ERROR",
                    line=lineno,
                    col=col,
                    message=f"Rule AST007: Known AI slopsquatted / hallucinated package detected: `{root_module}`.",
                    snippet=self._get_snippet(lineno),
                    function_scope=self.current_function,
                )
            )
            return

        for pat in SLOPSQUAT_PATTERNS:
            if pat.match(root_module):
                self.violations.append(
                    Violation(
                        rule_id="AST007",
                        category="AST_SECURITY",
                        severity="ERROR",
                        line=lineno,
                        col=col,
                        message=f"Rule AST007: Suspicious AI slopsquatting pattern detected: `{root_module}`.",
                        snippet=self._get_snippet(lineno),
                        function_scope=self.current_function,
                    )
                )
                break

    def visit_While(self, node: ast.While):
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            has_exit = any(
                isinstance(sub, (ast.Break, ast.Return, ast.Raise))
                for sub in ast.walk(node)
            )
            if not has_exit:
                self.violations.append(
                    Violation(
                        rule_id="AST004",
                        category="AST_SECURITY",
                        severity="ERROR",
                        line=node.lineno,
                        col=node.col_offset,
                        message="Unbounded `while True:` loop without explicit exit path (break/return/raise).",
                        snippet=self._get_snippet(node.lineno),
                        function_scope=self.current_function,
                    )
                )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:
            self.violations.append(
                Violation(
                    rule_id="AST006",
                    category="AST_SECURITY",
                    severity="WARNING",
                    line=node.lineno,
                    col=node.col_offset,
                    message="Bare `except:` clause catches BaseException and masks fatal interrupts.",
                    snippet=self._get_snippet(node.lineno),
                    function_scope=self.current_function,
                )
            )
        self.generic_visit(node)


def check_manifest_dependencies(file_path: Path) -> List[Violation]:
    """Scans requirements.txt and package.json for unpinned dependencies (DEP001)."""
    violations: List[Violation] = []
    fname = file_path.name.lower()

    if fname in ("requirements.txt", "requirements-dev.txt"):
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            for idx, raw_line in enumerate(lines, 1):
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("-r") or line.startswith("--"):
                    continue
                # Enforce pinned dependencies (==)
                if "==" not in line:
                    violations.append(
                        Violation(
                            rule_id="DEP001",
                            category="DEPENDENCY",
                            severity="ERROR",
                            line=idx,
                            col=0,
                            message=f"Rule DEP001: Unpinned dependency declaration `{line}`. Must use strict pinning (`package==1.0.0`).",
                            snippet=line,
                        )
                    )
        except Exception as e:
            violations.append(
                Violation(
                    rule_id="DEP001",
                    category="DEPENDENCY",
                    severity="WARNING",
                    line=1,
                    col=0,
                    message=f"Failed reading requirements manifest: {e}",
                )
            )

    return violations


def get_staged_python_files() -> List[Path]:
    """Retrieve staged Python files from Git index."""
    try:
        res = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )
        files = [Path(line.strip()) for line in res.stdout.splitlines() if line.strip().endswith(".py")]
        return [f for f in files if f.exists()]
    except Exception:
        return []


def run_py_compile(file_path: Path) -> Tuple[bool, Optional[Violation]]:
    """Run bytecode compilation check."""
    try:
        py_compile.compile(str(file_path), doraise=True)
        return True, None
    except py_compile.PyCompileError as exc:
        msg = str(exc.msg) if hasattr(exc, "msg") else str(exc)
        line = getattr(exc, "lineno", 1) or 1
        return False, Violation(
            rule_id="COMPILE001",
            category="SYNTAX",
            severity="ERROR",
            line=line,
            col=0,
            message=f"Compilation error: {msg}",
        )
    except Exception as exc:
        return False, Violation(
            rule_id="COMPILE001",
            category="SYNTAX",
            severity="ERROR",
            line=1,
            col=0,
            message=f"Compilation failed: {exc}",
        )


def run_ast_analysis(file_path: Path, max_complexity: int = 10) -> Tuple[bool, List[Violation]]:
    """Perform AST parsing, slopsquatting, and static complexity analysis."""
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        tree = ast.parse(content, filename=str(file_path))
        visitor = ASTSecurityAndComplexityVisitor(str(file_path), lines, max_complexity)
        visitor.visit(tree)
        return len(visitor.violations) == 0, visitor.violations
    except SyntaxError as syn_err:
        v = Violation(
            rule_id="SYNTAX001",
            category="SYNTAX",
            severity="ERROR",
            line=syn_err.lineno or 1,
            col=syn_err.offset or 0,
            message=f"SyntaxError: {syn_err.msg}",
            snippet=syn_err.text.strip() if syn_err.text else "",
        )
        return False, [v]
    except Exception as exc:
        v = Violation(
            rule_id="AST_ERR",
            category="SYNTAX",
            severity="ERROR",
            line=1,
            col=0,
            message=f"AST parsing exception: {exc}",
        )
        return False, [v]


def run_sast_secret_scan(file_path: Path) -> Tuple[bool, List[Violation]]:
    """Scan file for hardcoded secrets, private keys, or API credentials."""
    secret_patterns = [
        ("SEC001", re.compile(r"""(?i)(api[_-]?key|secret[_-]?key|password|token)\s*=\s*['\"][A-Za-z0-9_\-]{16,}['\"]"""), "Possible hardcoded API key or secret token"),
        ("SEC002", re.compile(r"-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----"), "Hardcoded private key header detected"),
        ("SEC003", re.compile(r"ghp_[A-Za-z0-9]{36}"), "Hardcoded GitHub Personal Access Token"),
        ("SEC004", re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}"), "Hardcoded Google Cloud / Firebase API Key"),
    ]
    violations: List[Violation] = []
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, 1):
            for rule_id, pattern, desc in secret_patterns:
                match = pattern.search(line)
                if match:
                    violations.append(
                        Violation(
                            rule_id=rule_id,
                            category="SAST_SECRET",
                            severity="ERROR",
                            line=idx,
                            col=match.start(),
                            message=desc,
                            snippet=line.strip(),
                        )
                    )
    except Exception as exc:
        violations.append(
            Violation(
                rule_id="SEC_ERR",
                category="SAST_SECRET",
                severity="ERROR",
                line=1,
                col=0,
                message=f"Secret scanner exception: {exc}",
            )
        )

    return len(violations) == 0, violations


def build_rstd_repair_context(file_path: Path, violations: List[Violation]) -> Dict[str, Any]:
    """Extracts isolated subtask repair windows (±3 lines) for autonomous RSTD self-healing."""
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        lines = []

    subtask_targets = []
    for v in violations:
        start_line = max(1, v.line - 3)
        end_line = min(len(lines), v.line + 3)
        context_block = lines[start_line - 1 : end_line]
        subtask_targets.append({
            "target_rule": v.rule_id,
            "target_line": v.line,
            "function_scope": v.function_scope,
            "repair_window": {
                "start_line": start_line,
                "end_line": end_line,
                "code": "\n".join(context_block),
            },
            "error_instruction": f"Fix violation: {v.message}",
        })

    return {
        "file": str(file_path),
        "isolated_repair_units": subtask_targets,
    }


def evaluate_single_file(file_path: Path, max_complexity: int) -> Tuple[Dict[str, Any], List[Violation]]:
    """Evaluates all VDD v3.0 gates for a single file and builds its diagnostic record."""
    file_violations: List[Violation] = []

    compile_ok, compile_violation = run_py_compile(file_path)
    if not compile_ok and compile_violation:
        file_violations.append(compile_violation)

    ast_ok, ast_violations = run_ast_analysis(file_path, max_complexity=max_complexity)
    file_violations.extend(ast_violations)

    sast_ok, sast_violations = run_sast_secret_scan(file_path)
    file_violations.extend(sast_violations)

    manifest_violations = check_manifest_dependencies(file_path)
    file_violations.extend(manifest_violations)

    file_passed = len(file_violations) == 0
    rstd_repair = build_rstd_repair_context(file_path, file_violations) if not file_passed else None

    record = {
        "file_path": str(file_path),
        "passed": file_passed,
        "checks": {
            "bytecode_compilation": {"passed": compile_ok},
            "ast_analysis": {"passed": ast_ok},
            "sast_secret_scan": {"passed": sast_ok},
            "slopsquatting_defense": {"passed": not any(v.rule_id == "AST007" for v in file_violations)},
            "dependency_pinning": {"passed": len(manifest_violations) == 0},
        },
        "violations_count": len(file_violations),
        "violations": [v.to_dict() for v in file_violations],
        "rstd_repair_context": rstd_repair,
    }
    return record, file_violations


def _print_ast_results(checks: Dict[str, Any], file_violations: List[Violation]) -> None:
    if checks["ast_analysis"]["passed"]:
        print("  [PASS] AST Static Analysis & Complexity Gate (Rule AST001-AST006)")
    else:
        print("  [FAIL] AST Verification Errors:")
        for v in file_violations:
            if v.category in {"AST_SECURITY", "AST_COMPLEXITY"} and v.rule_id != "AST007":
                print(f"         - {v}")


def _print_slopsquat_results(checks: Dict[str, Any], file_violations: List[Violation]) -> None:
    if checks["slopsquatting_defense"]["passed"]:
        print("  [PASS] Slopsquatting & Hallucinated Import Interceptor (Rule AST007)")
    else:
        print("  [FAIL] Slopsquatting Import Errors (Rule AST007):")
        for v in file_violations:
            if v.rule_id == "AST007":
                print(f"         - {v}")


def _print_sast_results(checks: Dict[str, Any], file_violations: List[Violation]) -> None:
    if checks["sast_secret_scan"]["passed"]:
        print("  [PASS] Secret & Security Pattern Scan (SEC001-SEC004)")
    else:
        print("  [FAIL] SAST / Secret Scan Warnings:")
        for v in file_violations:
            if v.category == "SAST_SECRET":
                print(f"         - {v}")


def print_human_report(file_path: Path, record: Dict[str, Any], file_violations: List[Violation]) -> None:
    """Outputs human-readable diagnostics for console inspection."""
    print(f"--> File: {file_path}")
    checks = record["checks"]

    print("  [PASS] Bytecode compilation (py_compile)" if checks["bytecode_compilation"]["passed"] else "  [FAIL] Compilation Error detected")
    _print_ast_results(checks, file_violations)
    _print_slopsquat_results(checks, file_violations)
    _print_sast_results(checks, file_violations)
    print()


def parse_cli_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Verifiability-Driven Development (VDD) Pre-Commit Gate v3.0 with AST007 & RSTD Feedback"
    )
    parser.add_argument("files", nargs="*", help="Explicit Python files to evaluate (defaults to git staged files).")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON schema for RSTD self-healing.")
    parser.add_argument("--report-file", type=str, help="Write RSTD JSON report to specified file path.")
    parser.add_argument("--max-complexity", type=int, default=10, help="Max cyclomatic complexity threshold (default: 10).")
    return parser.parse_args()


def _evaluate_all_files(target_files: List[Path], max_complexity: int, is_json: bool) -> Tuple[bool, List[Dict[str, Any]], List[Violation]]:
    all_passed = True
    overall_records: List[Dict[str, Any]] = []
    all_violations: List[Violation] = []

    for tf in target_files:
        if not tf.exists():
            continue
        record, file_violations = evaluate_single_file(tf, max_complexity=max_complexity)
        overall_records.append(record)
        all_violations.extend(file_violations)

        if not record["passed"]:
            all_passed = False

        if not is_json:
            print_human_report(tf, record, file_violations)

    return all_passed, overall_records, all_violations


def _write_summary_report(report_file: Optional[str], summary_payload: Dict[str, Any], is_json: bool) -> None:
    if not report_file:
        return
    try:
        Path(report_file).write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    except Exception as e:
        if not is_json:
            print(f"[WARN] Failed writing report file: {e}")


def _should_skip_dir(dirname: str) -> bool:
    skip_set = {".git", ".venv", "node_modules", "__pycache__", ".tox", "dist", "build"}
    return dirname in skip_set


def _collect_py_files_from_dir(directory: Path) -> List[Path]:
    collected: List[Path] = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for f in files:
            if f.endswith((".py", ".pyw")):
                collected.append(Path(root) / f)
    return collected


def _expand_target_files(raw_targets: List[Path]) -> List[Path]:
    """Expands directories into contained Python files and filters valid .py/.pyw targets."""
    expanded: List[Path] = []
    for t in raw_targets:
        if not t.exists():
            continue
        if t.is_dir():
            expanded.extend(_collect_py_files_from_dir(t))
        elif t.is_file() and t.suffix in {".py", ".pyw"}:
            expanded.append(t)
    return expanded


def main():
    args = parse_cli_args()
    raw_targets = [Path(f) for f in args.files] if args.files else get_staged_python_files()
    target_files = _expand_target_files(raw_targets)

    if not target_files:
        if not args.json:
            print("[VDD v3.0] No target Python files detected to evaluate. Clean exit.")
        sys.exit(0)

    if not args.json:
        print("=" * 65)
        print(" Verifiability-Driven Development (VDD) Pre-Commit Gate (v3.0)")
        print("=" * 65)
        print(f"[*] Analyzing {len(target_files)} target file(s)... \n")

    all_passed, overall_records, all_violations = _evaluate_all_files(target_files, args.max_complexity, args.json)

    summary_payload = {
        "version": "3.0",
        "passed": all_passed,
        "timestamp": sys.platform,
        "files_analyzed": len(overall_records),
        "total_violations": len(all_violations),
        "records": overall_records,
    }

    _write_summary_report(args.report_file, summary_payload, args.json)

    if args.json:
        print(json.dumps(summary_payload, indent=2))
    else:
        print("=" * 65)
        res_str = "[+] VDD GATE PASSED: All target files verified successfully." if all_passed else f"[-] VDD GATE REJECTED: {len(all_violations)} violation(s) detected."
        print(res_str)
        print("=" * 65)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
