#!/usr/bin/env python3
"""
Phase 02: Security Filtering — Human Verification Script
Requirements: R3.1 (File Exclusions), R3.2 (Entity Sanitization), R3.3 (Audit Logging)

Usage:
    python scripts/verify_phase_02.py [--fail-fast]

No Ollama, network, or git operations required.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure we run from project root
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Terminal colours ──────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


class Runner:
    def __init__(self, fail_fast: bool = False):
        self.fail_fast = fail_fast
        self.passed = 0
        self.failed = 0
        self.failures: list[str] = []

    def ok(self, msg: str) -> None:
        print(f"  {GREEN}[PASS]{RESET} {msg}")
        self.passed += 1

    def fail(self, msg: str, detail: str = "") -> None:
        print(f"  {RED}[FAIL]{RESET} {msg}")
        if detail:
            print(f"         {YELLOW}{detail}{RESET}")
        self.failed += 1
        self.failures.append(msg)
        if self.fail_fast:
            self.summary()
            sys.exit(1)

    def info(self, msg: str) -> None:
        print(f"         {msg}")

    def banner(self, title: str) -> None:
        print(f"\n{BOLD}── {title} ──{RESET}")

    def summary(self) -> bool:
        width = 55
        print(f"\n{BOLD}{'━' * width}{RESET}")
        print(f"{BOLD} Phase 02: Security Filtering — Verification Results{RESET}")
        print(f"{BOLD}{'━' * width}{RESET}")
        print(f" Tests passed: {GREEN}{self.passed}{RESET}")
        print(f" Tests failed: {RED}{self.failed}{RESET}")
        if self.failures:
            print("\n Failed:")
            for f in self.failures:
                print(f"   {RED}✗{RESET} {f}")
        else:
            print(f"\n {GREEN}All tests passed.{RESET} Requirements R3.1, R3.2, R3.3 verified.")
        print()
        return self.failed == 0


# ── Prerequisites ─────────────────────────────────────────────────────────────
def check_prerequisites() -> None:
    try:
        import src.security  # noqa: F401
    except ImportError as e:
        print(f"{RED}ERROR: Cannot import src.security — {e}{RESET}")
        print(f"       Run: pip install -e '.[dev]'")
        sys.exit(1)
    try:
        import detect_secrets  # noqa: F401
    except ImportError:
        print(f"{RED}ERROR: detect_secrets not installed — run: pip install -e '.[dev]'{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} src.security and detect_secrets available")


# ── Test 1: Full pytest suite ─────────────────────────────────────────────────
def test_full_pytest_suite(r: Runner) -> None:
    r.banner("Test 1: Full Security Test Suite (46 tests)")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_security.py", "-q", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    output = result.stdout + result.stderr
    summary_line = next(
        (line for line in reversed(output.splitlines()) if "passed" in line),
        "",
    )

    if result.returncode == 0 and "46 passed" in summary_line:
        r.ok(f"pytest tests/test_security.py — {summary_line.strip()}")
    else:
        r.fail(
            "pytest tests/test_security.py failed",
            detail=summary_line or "see output above",
        )
        # Print last 15 lines for context
        for line in output.splitlines()[-15:]:
            r.info(line)


# ── Test 2: AWS Key Detection ─────────────────────────────────────────────────
def test_aws_key_detection(r: Runner) -> None:
    r.banner("Test 2: AWS Key Detection (R3.2)")

    from src.security import sanitize_content

    # Positive: AWS key must be redacted
    aws_content = 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"'
    result = sanitize_content(aws_content)

    if result.was_modified and "[REDACTED:aws_key]" in result.sanitized_content:
        r.ok(f"AWS key → '{result.sanitized_content.strip()}', Modified=True")
    else:
        r.fail(
            "AWS key not redacted",
            detail=f"was_modified={result.was_modified}, output='{result.sanitized_content}'",
        )

    # Negative: safe content must not be touched
    safe_content = 'app_name = "MyApp"\nversion = "1.0.0"\ndebug = False'
    result2 = sanitize_content(safe_content)

    if not result2.was_modified and len(result2.findings) == 0:
        r.ok("Safe content not modified (no false positive)")
    else:
        r.fail(
            "Safe content was incorrectly modified (false positive)",
            detail=f"findings={result2.findings}",
        )


# ── Test 3: .env File Exclusion ───────────────────────────────────────────────
def test_env_file_exclusion(r: Runner) -> None:
    r.banner("Test 3: .env File Exclusion (R3.1)")

    from src.security import is_excluded_file

    cases = [
        (".env",               True,  "env file"),
        (".env.local",         True,  "env.local"),
        (".env.production",    True,  "env.production"),
        ("secrets.json",       True,  "secrets.json"),
        ("private.key",        True,  "private.key"),
        ("credentials.yaml",   True,  "credentials.yaml"),
        ("api_token.txt",      True,  "api_token.txt"),
        ("README.md",          False, "README.md"),
        ("main.py",            False, "main.py"),
        ("config.toml",        False, "config.toml"),
        ("src/service.py",     False, "src/service.py"),
    ]

    pass_count = 0
    fail_count = 0
    for filename, expected, label in cases:
        got = is_excluded_file(Path(filename))
        if got == expected:
            pass_count += 1
        else:
            fail_count += 1
            r.info(f"  FAIL {filename}: got excluded={got}, expected {expected}")

    if fail_count == 0:
        r.ok(f"File exclusion — {pass_count}/{len(cases)} correct")
    else:
        r.fail(
            f"File exclusion — {pass_count}/{len(cases)} correct, {fail_count} wrong",
        )


# ── Test 4: High-Entropy Detection ───────────────────────────────────────────
def test_high_entropy_detection(r: Runner) -> None:
    r.banner("Test 4: High-Entropy String Detection (R3.2)")

    from src.security import sanitize_content

    # base64-encoded string with high entropy
    content = "TOKEN=dGVzdC1zZWNyZXQta2V5LXZhbHVlLTEyMzQ1Njc4OTAtYWJjZGVmZ2hpamts"
    result = sanitize_content(content)

    if result.was_modified:
        r.ok(f"High-entropy base64 token detected → '{result.sanitized_content.strip()}'")
    else:
        r.fail(
            "High-entropy string not detected (Modified=False)",
            detail="Entropy thresholds may be too high for this string",
        )


# ── Test 5: Audit Log Writing ─────────────────────────────────────────────────
def test_audit_log_writing(r: Runner) -> None:
    r.banner("Test 5: Audit Log Writing (R3.3)")

    from src.security import ContentSanitizer
    from src.security.audit import SecurityAuditLogger

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        # SecurityAuditLogger is a singleton — reset it so the temp dir is used
        SecurityAuditLogger._instance = None
        SecurityAuditLogger._initialized = False

        sanitizer = ContentSanitizer(project_root=project_root)

        result = sanitizer.sanitize('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"', file_path="config.py")
        audit_log = project_root / ".graphiti" / "audit.log"

        # Restore singleton for any subsequent tests
        SecurityAuditLogger._instance = None
        SecurityAuditLogger._initialized = False

        if result.was_modified:
            r.ok(f"Sanitization returned Modified=True with {len(result.findings)} finding(s)")
        else:
            r.fail("Sanitization returned Modified=False — nothing was redacted")

        if audit_log.exists():
            lines = [line for line in audit_log.read_text().splitlines() if '"event"' in line]
            if lines:
                r.ok(f"audit.log created with {len(lines)} JSON event(s)")
            else:
                r.fail("audit.log exists but contains no JSON events")
        else:
            r.fail(f"audit.log not created at {audit_log}")


# ── Test 6: Custom Exclusion Patterns ────────────────────────────────────────
def test_custom_exclusion_patterns(r: Runner) -> None:
    r.banner("Test 6: Custom Exclusion Patterns (R3.1)")

    from src.security import FileExcluder

    excluder = FileExcluder(exclusion_patterns=["*.internal", "*_private*", "company_secrets/"])

    cases = [
        ("database.internal",       True,  "custom *.internal pattern"),
        ("my_private_config.yaml",  True,  "custom *_private* pattern"),
        ("public_config.yaml",      False, "normal config not excluded"),
        ("main.py",                 False, "python file not excluded"),
    ]

    pass_count = 0
    fail_count = 0
    for filename, expected, label in cases:
        got = excluder.check(Path(filename)).is_excluded
        if got == expected:
            pass_count += 1
        else:
            fail_count += 1
            r.info(f"  FAIL {filename}: got excluded={got}, expected {expected} ({label})")

    if fail_count == 0:
        r.ok(f"Custom exclusion patterns — {pass_count}/{len(cases)} correct")
    else:
        r.fail(f"Custom exclusion patterns — {pass_count}/{len(cases)} correct, {fail_count} wrong")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    fail_fast = "--fail-fast" in sys.argv

    print(f"\n{BOLD}Phase 02: Security Filtering — Human Verification{RESET}")
    print(f"Requirements: R3.1 (File Exclusions) · R3.2 (Sanitization) · R3.3 (Audit Logging)")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites()

    test_full_pytest_suite(r)
    test_aws_key_detection(r)
    test_env_file_exclusion(r)
    test_high_entropy_detection(r)
    test_audit_log_writing(r)
    test_custom_exclusion_patterns(r)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
