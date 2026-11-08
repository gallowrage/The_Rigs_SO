#!/usr/bin/env python3
"""
VDD v3.0 Gate — Deterministic AST Complexity & Hygiene Auditor
McCabe Cyclomatic Complexity <= 9 Gatekeeper (Rule AST005)
Zero external dependencies (Python Standard Library only).
"""

import ast
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable, List, Sequence, Set

IGNORED_DIRS: Set[str] = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "forensics",
    ".agents",
    "Agent-Reach",
    "REA_Engine",
    "archive",
    "scratch",
    "donors",
    "awesome-gamedev-skills",
}


@dataclass(frozen=True)
class ComplexityViolation:
    filepath: Path
    lineno: int
    function_name: str
    score: int


def _calc_node_complexity(node: ast.AST) -> int:
    """Calculates McCabe cyclomatic complexity for a function AST node (CC <= 9)."""
    score = 1
    for child in ast.walk(node):
        if isinstance(
            child,
            (
                ast.If,
                ast.While,
                ast.For,
                ast.AsyncFor,
                ast.ExceptHandler,
                ast.With,
                ast.AsyncWith,
            ),
        ):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += len(child.values) - 1
    return score


def audit_file_complexity(filepath: Path, max_cc: int = 9) -> List[ComplexityViolation]:
    """Audits all functions in a Python file against the McCabe complexity ceiling."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []

    violations: List[ComplexityViolation] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            score = _calc_node_complexity(node)
            if score > max_cc:
                violations.append(
                    ComplexityViolation(
                        filepath=filepath,
                        lineno=node.lineno,
                        function_name=node.name,
                        score=score,
                    )
                )
    return violations


def _collect_python_files(target_path: Path) -> List[Path]:
    """Collects Python files under target_path while excluding ignored directories."""
    if target_path.is_file() and target_path.suffix == ".py":
        return [target_path]
    if not target_path.is_dir():
        return []
    return [
        p
        for p in target_path.rglob("*.py")
        if not any(part in IGNORED_DIRS for part in p.parts)
    ]


def audit_targets(targets: Iterable[Path], max_cc: int = 9) -> int:
    """Audits one or more file or directory targets for McCabe complexity violations."""
    files: List[Path] = []
    for target_path in targets:
        files.extend(_collect_python_files(target_path))

    all_violations: List[ComplexityViolation] = []
    for f in files:
        all_violations.extend(audit_file_complexity(f, max_cc=max_cc))

    if not all_violations:
        print(f"[VDD_V3 PASS] All {len(files)} module(s) verified (McCabe CC <= {max_cc}).")
        return 0

    for v in all_violations:
        print(f"[VDD_V3 FAIL] {v.filepath}:{v.lineno} in '{v.function_name}' CC={v.score} > {max_cc}")
    print(f"\n[ACTION REQUIRED] {len(all_violations)} function(s) violate cyclomatic complexity ceiling.")
    return 1


def audit_target(target_path: Path, max_cc: int = 9) -> int:
    """Audits a single file or directory tree for McCabe complexity violations."""
    return audit_targets([target_path], max_cc=max_cc)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint supporting single or multiple file/directory arguments."""
    args = [a for a in (argv if argv is not None else sys.argv[1:]) if not a.startswith("-")]
    targets = [Path(a) for a in args] if args else [Path(".")]
    return audit_targets(targets)


if __name__ == "__main__":
    sys.exit(main())
