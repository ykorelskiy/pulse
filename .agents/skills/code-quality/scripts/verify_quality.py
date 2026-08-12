#!/usr/bin/env python3
"""Portable Code Quality & Safety Auditor for Python + TypeScript + Supabase projects."""

import ast
import re
import sys
from pathlib import Path

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


class QualityChecker:

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.issues: list[dict[str, str]] = []

    def log_issue(self, severity: str, category: str, location: str, message: str) -> None:
        self.issues.append({
            "severity": severity,
            "category": category,
            "location": location,
            "message": message,
        })

    def check_python_syntax(self) -> None:
        """1. Check syntax of all Python files."""
        py_files = list(self.root_dir.glob("src/**/*.py")) + list(self.root_dir.glob("scripts/**/*.py"))
        for py_path in py_files:
            try:
                with open(py_path, "r", encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content, filename=str(py_path))
            except Exception as e:
                self.log_issue(
                    "CRITICAL",
                    "Syntax Error",
                    str(py_path.relative_to(self.root_dir)),
                    f"Python syntax error: {e}",
                )

    def check_silent_exceptions(self) -> None:
        """2. Check for swallowed exceptions (except Exception: pass)."""
        py_files = list(self.root_dir.glob("src/**/*.py"))
        pattern = re.compile(r"except\s+Exception(?:\s+as\s+\w+)?:\s*(?:pass|\.\.\.)")
        for py_path in py_files:
            try:
                with open(py_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    if pattern.search(line) and "with contextlib.suppress" not in line:
                        self.log_issue(
                            "WARNING",
                            "Silent Exception",
                            f"{py_path.relative_to(self.root_dir)}:{i}",
                            "Swallowed exception found (except Exception: pass). Use logging or contextlib.suppress.",
                        )
            except Exception:
                pass

    def check_supabase_rls(self) -> None:
        """3. Check SQL files for CREATE TABLE without RLS."""
        sql_files = list(self.root_dir.glob("**/*.sql"))
        create_table_regex = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_\.]+)", re.IGNORECASE)
        rls_regex = re.compile(r"ENABLE\s+ROW\s+LEVEL\s+SECURITY", re.IGNORECASE)

        for sql_path in sql_files:
            if "node_modules" in str(sql_path) or ".venv" in str(sql_path):
                continue
            try:
                with open(sql_path, "r", encoding="utf-8") as f:
                    content = f.read()
                tables = create_table_regex.findall(content)
                if tables and not rls_regex.search(content):
                    self.log_issue(
                        "CRITICAL",
                        "Supabase Security",
                        str(sql_path.relative_to(self.root_dir)),
                        f"Found CREATE TABLE ({', '.join(tables)}) without ENABLE ROW LEVEL SECURITY.",
                    )
            except Exception:
                pass

    def check_hardcoded_secrets(self) -> None:
        """4. Check for hardcoded API keys or secrets in source files."""
        secret_patterns = [
            (re.compile(r"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+"), "JWT / Supabase Key"),
            (re.compile(r"\b\d{8,10}:[a-zA-Z0-9_-]{35}\b"), "Telegram Bot Token"),
            (re.compile(r"\bvk1\.a\.[a-zA-Z0-9_\-]{50,}\b"), "VK Access Token"),
        ]

        source_files = (
            list(self.root_dir.glob("src/**/*.py")) +
            list(self.root_dir.glob("site/src/**/*.ts*"))
        )

        for filepath in source_files:
            if filepath.name in ("config.py", "supabase.ts"):
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                for pattern, secret_type in secret_patterns:
                    if pattern.search(content):
                        self.log_issue(
                            "CRITICAL",
                            "Secret Leak",
                            str(filepath.relative_to(self.root_dir)),
                            f"Hardcoded {secret_type} detected!",
                        )
            except Exception:
                pass

    def run_all(self) -> int:
        print(f"\n{BOLD}======================================================{RESET}")
        print(f"{BOLD} CODE QUALITY & SECURITY VERIFICATION{RESET}")
        print(f"{BOLD} Project Root: {self.root_dir}{RESET}")
        print(f"{BOLD}======================================================{RESET}\n")

        self.check_python_syntax()
        self.check_silent_exceptions()
        self.check_supabase_rls()
        self.check_hardcoded_secrets()

        criticals = [i for i in self.issues if i["severity"] == "CRITICAL"]
        warnings = [i for i in self.issues if i["severity"] == "WARNING"]

        for issue in self.issues:
            color = RED if issue["severity"] == "CRITICAL" else YELLOW
            print(f"{color}[{issue['severity']}]{RESET} {BOLD}{issue['category']}{RESET} @ {issue['location']}")
            print(f"   ↳ {issue['message']}\n")

        print("------------------------------------------------------")
        if not self.issues:
            print(f"{GREEN}{BOLD}✅ ALL QUALITY CHECKS PASSED! No issues found.{RESET}\n")
            return 0

        print(f"Summary: {RED}{len(criticals)} Criticals{RESET}, {YELLOW}{len(warnings)} Warnings{RESET}\n")
        return 1 if criticals else 0


def main() -> None:
    root = Path.cwd()
    checker = QualityChecker(root)
    sys.exit(checker.run_all())


if __name__ == "__main__":
    main()
