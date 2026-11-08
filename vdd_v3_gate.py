#!/usr/bin/env python3
"""
VDD v3.0 Gate — Deterministic AST Complexity & Hygiene Auditor
McCabe Cyclomatic Complexity <= 9 Gatekeeper (Rule AST005)
Zero external dependencies (Python Standard Library only).
"""

import ast
from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Iterable, List, Sequence, Set

IGNORED_DIRS: Set[str] = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    ".tox",
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
    "ida-free-mcp-main",
    "packages",
    "Master_Archive",
}

_BRANCH_NODES = (
    ast.If,
    ast.While,
    ast.For,
    ast.AsyncFor,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncWith,
    ast.IfExp,
)


@dataclass(frozen=True)
class ComplexityViolation:
    filepath: Path
    lineno: int
    function_name: str
    score: int


def _calc_child_complexity(node: ast.AST) -> int:
    """Recursively counts complexity branches while isolating nested function definitions."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    score = 0
    if isinstance(node, _BRANCH_NODES):
        score += 1
    elif isinstance(node, ast.BoolOp):
        score += len(node.values) - 1
    for child in ast.iter_child_nodes(node):
        score += _calc_child_complexity(child)
    return score


def _calc_node_complexity(node: ast.AST) -> int:
    """Calculates McCabe cyclomatic complexity for a function AST node (CC <= 9)."""
    return 1 + sum(_calc_child_complexity(child) for child in ast.iter_child_nodes(node))


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
    """Collects Python files under target_path while pruning ignored directories."""
    if target_path.is_file() and target_path.suffix == ".py":
        return [target_path]
    if not target_path.is_dir():
        return []
    collected: List[Path] = []
    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                collected.append(Path(root) / fname)
    return collected


def audit_targets(targets: Iterable[Path], max_cc: int = 9) -> int:
    """Audits one or more file or directory targets for McCabe complexity violations."""
    files: List[Path] = []
    seen: Set[Path] = set()
    for target_path in targets:
        for candidate in _collect_python_files(target_path):
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(candidate)

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
    """CLI entrypoint supporting single or multiple file/directory arguments, including --files."""
    raw_args = list(argv if argv is not None else sys.argv[1:])
    args: List[str] = []
    i = 0
    while i < len(raw_args):
        a = raw_args[i]
        if a == "--files":
            i += 1
            while i < len(raw_args) and not raw_args[i].startswith("-"):
                args.append(raw_args[i])
                i += 1
            continue
        elif not a.startswith("-"):
            args.append(a)
        i += 1
    targets = [Path(a) for a in args] if args else [Path(".")]
    return audit_targets(targets)


if __name__ == "__main__":
    sys.exit(main())
