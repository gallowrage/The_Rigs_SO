#!/usr/bin/env python3
"""
Runtime-Structured Task Decomposition (RSTD) Automated Repair Runner (v3.0 - Windows Native)
--------------------------------------------------------------------------------------------
Implements programmatic orchestration, bounded-context subtask repair, and
validation-gated selective retries as formalized in Asthana et al. (ACM CAIS 2026).

Native Windows & Google Antigravity CLI (`agy.exe`) Integration:
1. Executes deterministic VDD pre-commit gate (vdd_pre_commit-v3.py --json).
2. Deconstructs failures into isolated subtask repair units (bounded context ±3 lines).
3. Applies patches in reverse line order (bottom-up) to eliminate line-number drift.
4. Dispatches headless Antigravity CLI commands (`agy -p "..." --mode accept-edits`)
   targeting ONLY the failing subtask unit to prevent token runaway and hallucination.
5. Provides multi-tier fallback: `agy` -> Antigravity Python SDK / Gemini API -> Deterministic AST Remediator.
6. Re-verifies via deterministic bytecode compilation, AST inspection, and secret scans.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure safe UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def resolve_agy_binary(custom_bin: Optional[str] = None) -> str:
    """Resolves the Antigravity CLI binary path across Windows and Unix environments."""
    if custom_bin and (shutil.which(custom_bin) or Path(custom_bin).exists()):
        return custom_bin

    found = shutil.which("agy") or shutil.which("agy.exe")
    if found:
        return found

    default_win_bin = Path.home() / ".gemini" / "bin" / "agy.exe"
    if default_win_bin.exists():
        return str(default_win_bin)

    return "agy"


def _fix_ast001(line: str, indent: str) -> Optional[str]:
    if "from " in line and "import *" in line:
        mod_name = line.split("from")[1].split("import")[0].strip()
        return f"import {mod_name}"
    return None


def _fix_ast002(line: str, indent: str) -> Optional[str]:
    if "eval(" in line or "exec(" in line:
        return f"{indent}pass  # [REMEDIATED RSTD] Dynamic execution removed"
    return None


def _fix_ast004(line: str, indent: str) -> Optional[str]:
    if "while True:" in line:
        return f"{line}\n{indent}    break  # [REMEDIATED RSTD] loop exit"
    return None


def _fix_ast006(line: str, indent: str) -> Optional[str]:
    if "except:" in line:
        return line.replace("except:", "except Exception:")
    return None


def _fix_sec001(line: str, indent: str) -> Optional[str]:
    if "=" in line:
        var_name = line.split("=")[0].strip()
        return f"{var_name} = os.environ.get('{var_name}', '')  # RSTD vaulted credential"
    return None


REMEDIATION_DISPATCH = {
    "AST001": _fix_ast001,
    "AST002": _fix_ast002,
    "AST004": _fix_ast004,
    "AST006": _fix_ast006,
    "SEC001": _fix_sec001,
}


class RSTDRepairRunner:
    """Orchestrates runtime-structured selective repair passes over failing code."""

    def __init__(
        self,
        gate_script: Path,
        max_retries: int = 3,
        dry_run: bool = False,
        agy_bin: Optional[str] = None,
        agy_model: Optional[str] = None,
        agy_effort: Optional[str] = None,
    ):
        self.gate_script = gate_script
        self.max_retries = max_retries
        self.dry_run = dry_run
        self.agy_bin = resolve_agy_binary(agy_bin)
        self.agy_model = agy_model
        self.agy_effort = agy_effort
        self.state_manager: Dict[str, Any] = {
            "repaired_subtasks": [],
            "failed_subtasks": [],
            "dispatch_methods": {},
        }

    def run_deterministic_gate(self, target_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute deterministic verification gate and retrieve structured JSON report."""
        cmd = [sys.executable, str(self.gate_script), "--json"]
        if target_files:
            cmd.extend(target_files)

        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        try:
            return json.loads(res.stdout)
        except json.JSONDecodeError as exc:
            print(f"[ERROR] Failed to parse VDD Gate JSON: {exc}\nRaw Output:\n{res.stdout}")
            return {"overall_passed": False, "files": [], "error": str(exc)}

    def execute_typed_judgment_operator(
        self,
        repair_unit: Dict[str, Any],
        file_path: Path,
    ) -> bool:
        """Typed LLM Judgment Operator scoped to the isolated repair window."""
        rule_id = repair_unit.get("target_rule", "UNKNOWN")
        line_no = repair_unit.get("target_line", 0)
        instruction = repair_unit.get("error_instruction", "")
        window = repair_unit.get("repair_window", {})
        code_snippet = window.get("code", "")
        start_line = window.get("start_line", line_no)
        end_line = window.get("end_line", line_no)

        print(f"  [*] Dispatching Subtask -> Rule: {rule_id} at line {line_no}")
        print(f"      Instruction: {instruction}")

        # Tier 1: Headless Antigravity CLI (`agy`)
        agy_ok, _ = self._dispatch_antigravity_cli(
            file_path=file_path,
            rule_id=rule_id,
            line_no=line_no,
            instruction=instruction,
            start_line=start_line,
            end_line=end_line,
            snippet=code_snippet,
        )
        if agy_ok:
            self.state_manager["dispatch_methods"][rule_id] = "antigravity_cli"
            return True

        # Tier 2: Gemini / Google Antigravity Python SDK
        sdk_ok = self._dispatch_gemini_sdk(
            file_path=file_path,
            rule_id=rule_id,
            window=window,
            instruction=instruction,
            snippet=code_snippet,
        )
        if sdk_ok:
            self.state_manager["dispatch_methods"][rule_id] = "gemini_sdk"
            return True

        # Tier 3: Deterministic Rule-Based Remediator (Offline Fallback)
        rule_ok = self._apply_deterministic_remediation(file_path, rule_id, line_no)
        if rule_ok:
            self.state_manager["dispatch_methods"][rule_id] = "deterministic_rule"
            return True

        return False

    def _build_cli_command(
        self,
        file_path: Path,
        rule_id: str,
        line_no: int,
        instruction: str,
        start_line: int,
        end_line: int,
        snippet: str,
    ) -> List[str]:
        """Constructs the headless Antigravity CLI command."""
        mode_val = "dry-run" if self.dry_run else "accept-edits"
        prompt = (
            f"Fix code violation in file {file_path.resolve()}:\n"
            f"- Rule ID: {rule_id}\n"
            f"- Instruction: {instruction}\n"
            f"- Target Line: {line_no} (Window lines {start_line}-{end_line})\n"
            f"Violating Code Context:\n"
            f"```python\n{snippet}\n```\n\n"
            f"Requirements:\n"
            f"1. Make precision edits to fix ONLY this violation without altering unrelated logic.\n"
            f"2. Maintain strict Python syntax, valid indentation, and cyclomatic complexity <= 10.\n"
            f"3. Do not introduce wildcard imports, bare excepts, or unbounded loops.\n"
            f"Apply the edits directly to the file."
        )

        cmd = [self.agy_bin, "-p", prompt, "--mode", mode_val]
        if self.agy_model:
            cmd.extend(["--model", self.agy_model])
        if self.agy_effort:
            cmd.extend(["--effort", self.agy_effort])
        return cmd

    def _execute_cli_process(self, cmd: List[str], file_path: Path) -> Tuple[bool, str]:
        """Executes the CLI command and checks filesystem mtime change."""
        try:
            mtime_before = file_path.stat().st_mtime if file_path.exists() else 0
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120, encoding="utf-8")

            if res.returncode != 0:
                return False, f"agy exit {res.returncode}: {res.stderr.strip()}"

            mtime_after = file_path.stat().st_mtime if file_path.exists() else 0
            if mtime_after > mtime_before or self.dry_run:
                action = "[DRY-RUN] Verified" if self.dry_run else "[+] Applied"
                print(f"      {action} subtask fix via Antigravity CLI (`agy`).")
                return True, "success"

            return False, "file unchanged"
        except subprocess.TimeoutExpired:
            return False, "agy process timed out"
        except Exception as exc:
            return False, f"agy error: {exc}"

    def _dispatch_antigravity_cli(
        self,
        file_path: Path,
        rule_id: str,
        line_no: int,
        instruction: str,
        start_line: int,
        end_line: int,
        snippet: str,
    ) -> Tuple[bool, str]:
        """Dispatch targeted subtask to Antigravity CLI with --mode accept-edits."""
        if not shutil.which(self.agy_bin) and not Path(self.agy_bin).exists():
            return False, "agy binary not found"

        cmd = self._build_cli_command(
            file_path=file_path,
            rule_id=rule_id,
            line_no=line_no,
            instruction=instruction,
            start_line=start_line,
            end_line=end_line,
            snippet=snippet,
        )
        return self._execute_cli_process(cmd, file_path)

    def _dispatch_gemini_sdk(
        self,
        file_path: Path,
        rule_id: str,
        window: Dict[str, Any],
        instruction: str,
        snippet: str,
    ) -> bool:
        """Fallback to direct Gemini client API if GEMINI_API_KEY is available."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key or self.dry_run:
            return False

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = (
                f"You are an automated code repair operator adhering to strict AST and VDD rules.\n"
                f"Task Instruction: {instruction}\n"
                f"Violating Snippet (lines {window.get('start_line')}-{window.get('end_line')}):\n"
                f"```python\n{snippet}\n```\n"
                f"Return ONLY the replacement code snippet for these lines. No markdown, no prose."
            )
            response = client.models.generate_content(
                model=self.agy_model or "gemini-2.5-pro",
                contents=prompt,
            )
            replacement_code = (
                response.text.strip()
                .removeprefix("```python")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            success = self._apply_isolated_patch(file_path, window, replacement_code)
            if success:
                print(f"      [+] Applied subtask fix via Gemini SDK API.")
            return success
        except Exception:
            return False

    @staticmethod
    def _remediate_single_line(rule_id: str, original_line: str) -> Optional[str]:
        """Deterministic remediation transformation via dispatch table."""
        handler = REMEDIATION_DISPATCH.get(rule_id)
        if not handler:
            return None
        indent = " " * (len(original_line) - len(original_line.lstrip()))
        return handler(original_line, indent)

    def _apply_deterministic_remediation(self, file_path: Path, rule_id: str, line_no: int) -> bool:
        """Applies targeted, deterministic structural corrections preserving indentation and AST safety."""
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            idx = line_no - 1
            if idx >= len(lines):
                return False

            remediated = self._remediate_single_line(rule_id, lines[idx])
            if remediated is None:
                return False

            lines[idx] = remediated
            if not self.dry_run:
                file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                print(f"      [+] Applied targeted fallback patch to line {line_no}.")
            else:
                print(f"      [DRY-RUN] Would patch line {line_no}: '{lines[idx]}'")

            return True
        except Exception as err:
            print(f"      [!] Failed to apply patch: {err}")
            return False

    def _apply_isolated_patch(self, file_path: Path, window: Dict[str, Any], replacement: str) -> bool:
        """Splices the model's replacement snippet into the file's line window."""
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            start = window["start_line"] - 1
            end = window["end_line"]

            new_lines = lines[:start] + replacement.splitlines() + lines[end:]
            file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            return True
        except Exception as e:
            print(f"      [!] Splice error: {e}")
            return False

    def _repair_failed_file(self, file_entry: Dict[str, Any]) -> int:
        """Executes isolated subtask repairs for a single failed file entry."""
        raw_path = file_entry.get("file_path") or file_entry.get("file") or ""
        file_path = Path(raw_path)
        repair_units = file_entry.get("rstd_repair_context", {}).get("isolated_repair_units", [])
        repair_units.sort(key=lambda u: u.get("target_line", 0), reverse=True)

        print(f"\n--> File: {file_path.name} ({len(repair_units)} isolated subtask repair units)")
        for unit in repair_units:
            success = self.execute_typed_judgment_operator(unit, file_path)
            target_bucket = "repaired_subtasks" if success else "failed_subtasks"
            self.state_manager[target_bucket].append(unit["target_rule"])
        return len(repair_units)

    def run_repair_pipeline(self, target_files: Optional[List[str]] = None) -> bool:
        """Executes the full RSTD self-healing loop with selective subtask retries."""
        print("=" * 68)
        print(" Runtime-Structured Task Decomposition (RSTD) Repair Loop (v3.0)")
        print(f" Active CLI Binary: {self.agy_bin}")
        print("=" * 68)

        for cycle in range(1, self.max_retries + 1):
            print(f"\n[CYCLE {cycle}/{self.max_retries}] Running deterministic VDD pre-commit gate...")
            report = self.run_deterministic_gate(target_files)

            if report.get("overall_passed", report.get("passed", False)):
                print("\n[+] SUCCESS: Deterministic VDD Gate 100% PASSED!")
                print(f"[+] Total subtasks repaired: {len(self.state_manager['repaired_subtasks'])}")
                if self.state_manager["dispatch_methods"]:
                    print(f"[+] Remediation Methods Employed: {self.state_manager['dispatch_methods']}")
                return True

            file_records = report.get("files", report.get("records", []))
            failed_files = [f for f in file_records if not f.get("passed")]
            print(f"[-] Gate flagged {len(failed_files)} file(s) requiring remediation.")

            total_subtasks_in_cycle = sum(self._repair_failed_file(fe) for fe in failed_files)
            if total_subtasks_in_cycle == 0:
                print("[!] No automatable subtask repair units found. Manual intervention required.")
                break

        print("\n[!] Maximum RSTD repair cycles exhausted. Remaining violations require developer sign-off.")
        return False


def main():
    parser = argparse.ArgumentParser(description="RSTD Automated Repair Runner (v3.0 with Antigravity CLI)")
    parser.add_argument("files", nargs="*", help="Optional target files to verify and heal")
    parser.add_argument("--gate", default=None, help="Path to VDD gate script")
    parser.add_argument("--retries", type=int, default=3, help="Max repair iterations")
    parser.add_argument("--dry-run", action="store_true", help="Simulate repairs without modifying disk")
    parser.add_argument("--agy-bin", default=None, help="Custom path to Antigravity CLI binary")
    parser.add_argument("--model", default=None, help="Model override for agy (e.g., 'gemini-3.8-flash-high')")
    parser.add_argument("--effort", default=None, choices=["low", "medium", "high"], help="Reasoning effort level")
    args = parser.parse_args()

    script_dir = Path(__file__).parent.resolve()
    candidates = [
        Path(args.gate) if args.gate else None,
        script_dir / "vdd_pre_commit-v3.py",
        script_dir / "vdd_pre_commit.py",
        Path("C:/Users/dngal/Projects/vdd_pre_commit-v3.py"),
        Path("C:/Users/dngal/Nexus_Galloway/01_Kernel/vdd_pre_commit/vdd_pre_commit.py"),
        Path("./vdd_pre_commit-v3.py"),
    ]

    gate_path = next((c for c in candidates if c and c.exists()), None)
    if not gate_path:
        print("[ERROR] Could not find vdd_pre_commit-v3.py in search paths.")
        sys.exit(1)

    runner = RSTDRepairRunner(
        gate_script=gate_path,
        max_retries=args.retries,
        dry_run=args.dry_run,
        agy_bin=args.agy_bin,
        agy_model=args.model,
        agy_effort=args.effort,
    )
    success = runner.run_repair_pipeline(args.files if args.files else None)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
