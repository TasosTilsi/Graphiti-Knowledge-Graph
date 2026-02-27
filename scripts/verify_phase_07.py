#!/usr/bin/env python3
"""
Phase 07: Git Integration — Human Verification Script
Requirements: R8.1 (Git-Safe Knowledge Graphs)

Usage:
    python scripts/verify_phase_07.py [--fail-fast]

NOTE: Journal, LFS, checkpoint, and compact-journal tests are obsolete.
      Phase 7.1 removed those systems. This script tests only what remains:

    1. .graphiti/.gitignore generation   — src/gitops/config.py
    2. Secret detection in staged files  — src/gitops/hooks.py  (temp repo)
    3. GRAPHITI_SKIP=1 bypass            — src/gitops/hooks.py
    4. check_graphiti_size thresholds    — src/gitops/hooks.py
    5. Hook installation idempotency     — src/hooks/installer.py

No Ollama, network, or long-running operations required.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Terminal colours ──────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

GRAPHITI = str(ROOT / ".venv" / "bin" / "graphiti")


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
        width = 60
        print(f"\n{BOLD}{'━' * width}{RESET}")
        print(f"{BOLD} Phase 07: Git Integration — Verification Results{RESET}")
        print(f"{BOLD}{'━' * width}{RESET}")
        print(f" Tests passed: {GREEN}{self.passed}{RESET}")
        print(f" Tests failed: {RED}{self.failed}{RESET}")
        if self.failures:
            print("\n Failed:")
            for f in self.failures:
                print(f"   {RED}✗{RESET} {f}")
        else:
            print(f"\n {GREEN}All tests passed.{RESET} Requirement R8.1 (git-safe graphs) verified.")
        print()
        return self.failed == 0


# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout
    )


def _init_temp_repo(tmp_root: Path) -> None:
    """Initialize a minimal git repo with one commit to establish HEAD."""
    run(["git", "init"], cwd=tmp_root)
    run(["git", "config", "user.email", "test@example.com"], cwd=tmp_root)
    run(["git", "config", "user.name", "Test User"], cwd=tmp_root)
    readme = tmp_root / "README.md"
    readme.write_text("# Test repo\n")
    run(["git", "add", "README.md"], cwd=tmp_root)
    run(["git", "commit", "-m", "init"], cwd=tmp_root)


# ── Prerequisites ─────────────────────────────────────────────────────────────
def check_prerequisites() -> None:
    try:
        import src.gitops  # noqa: F401
    except ImportError as e:
        print(f"{RED}ERROR: Cannot import src.gitops — {e}{RESET}")
        print(f"       Run: pip install -e '.[dev]'")
        sys.exit(1)
    try:
        import src.hooks  # noqa: F401
    except ImportError as e:
        print(f"{RED}ERROR: Cannot import src.hooks — {e}{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} src.gitops and src.hooks importable")


# ── Test 1: .gitignore generation ─────────────────────────────────────────────
def test_gitignore_generation(r: Runner) -> None:
    r.banner("Test 1: .graphiti/.gitignore Generation (R8.1 — config.py)")

    from src.gitops.config import ensure_git_config, GRAPHITI_GITIGNORE

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)

        result = ensure_git_config(tmp_root)

        if not result.get("gitignore"):
            r.fail("ensure_git_config returned gitignore=False")
            return
        r.ok("ensure_git_config returned {'gitignore': True}")

        gitignore_path = tmp_root / ".graphiti" / ".gitignore"
        if not gitignore_path.exists():
            r.fail(".graphiti/.gitignore was not created")
            return
        r.ok(".graphiti/.gitignore file created")

        content = gitignore_path.read_text()
        expected_entries = ["queue.db", "*.tmp", "*.lock", ".rebuilding"]
        missing = [e for e in expected_entries if e not in content]
        if missing:
            r.fail(
                f".gitignore missing expected entries: {missing}",
                detail=f"Content:\n{content[:300]}",
            )
        else:
            r.ok(f".gitignore contains all expected entries: {expected_entries}")

        # Calling again (idempotent) should succeed and overwrite cleanly
        result2 = ensure_git_config(tmp_root)
        if result2.get("gitignore"):
            r.ok("ensure_git_config is idempotent (second call succeeds)")
        else:
            r.fail("ensure_git_config not idempotent — second call returned gitignore=False")


# ── Test 2: Secret detection in staged files ──────────────────────────────────
def test_secret_detection(r: Runner) -> None:
    r.banner("Test 2: Secret Detection in Staged Files (R8.1 — scan_staged_secrets)")

    from src.gitops.hooks import scan_staged_secrets

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        _init_temp_repo(tmp_root)

        # Commit a clean config.py first, then modify it to add a fake AWS key.
        config_file = tmp_root / "config.py"
        config_file.write_text("# App configuration\nDEBUG = False\n")
        run(["git", "add", "config.py"], cwd=tmp_root)
        run(["git", "commit", "-m", "add config"], cwd=tmp_root)

        # Now modify the existing file to add a fake AWS key (AKIA + 16 chars = 20 total)
        config_file.write_text(
            "# App configuration\n"
            "DEBUG = False\n"
            "AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'\n"
        )
        run(["git", "add", "config.py"], cwd=tmp_root)

        warnings = scan_staged_secrets(tmp_root)

        if warnings:
            r.ok(f"Detected {len(warnings)} secret warning(s) for staged AWS key")
            r.info(f"Warning: {warnings[0]}")
        else:
            r.fail(
                "scan_staged_secrets returned no warnings for staged AWS key",
                detail="Expected detection of AKIAIOSFODNN7EXAMPLE pattern (AKIA + 16 chars)",
            )

        # Commit the staged file, then modify config.py to a clean version
        run(["git", "commit", "-m", "add secret (test only)"], cwd=tmp_root)
        config_file.write_text("# App configuration\nDEBUG = False\n")
        run(["git", "add", "config.py"], cwd=tmp_root)

        clean_warnings = scan_staged_secrets(tmp_root)

        if not clean_warnings:
            r.ok("No false positives on clean file")
        else:
            r.fail(
                f"False positive: {len(clean_warnings)} warning(s) for clean file",
                detail=str(clean_warnings),
            )

        # Commit the clean version so index is clean again
        run(["git", "commit", "-m", "restore clean config"], cwd=tmp_root)

        # Sub-test: brand-new file (not previously in HEAD) — tests the 8.7-01 fix
        new_file = tmp_root / "new_secrets.py"
        new_file.write_text("TOKEN = 'AKIAIOSFODNN7EXAMPLE'\n")
        run(["git", "add", "new_secrets.py"], cwd=tmp_root)
        new_file_warnings = scan_staged_secrets(tmp_root)
        if new_file_warnings:
            r.ok("New staged file (not in HEAD) — secrets detected (8.7-01 fix confirmed)")
        else:
            r.fail("New staged file not scanned — 8.7-01 fix not applied")


# ── Test 3: GRAPHITI_SKIP=1 bypass ────────────────────────────────────────────
def test_graphiti_skip_bypass(r: Runner) -> None:
    r.banner("Test 3: GRAPHITI_SKIP=1 Bypass (R8.1 — hooks.py)")

    from src.gitops.hooks import scan_staged_secrets, check_graphiti_size

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        _init_temp_repo(tmp_root)

        # Commit a clean file then modify it to add a fake key
        bad_file = tmp_root / "secrets.py"
        bad_file.write_text("TOKEN = 'placeholder'\n")
        run(["git", "add", "secrets.py"], cwd=tmp_root)
        run(["git", "commit", "-m", "add secrets placeholder"], cwd=tmp_root)
        bad_file.write_text("TOKEN = 'AKIAIOSFODNN7EXAMPLE'\n")
        run(["git", "add", "secrets.py"], cwd=tmp_root)

        # With GRAPHITI_SKIP=1, scan should return empty
        os.environ["GRAPHITI_SKIP"] = "1"
        try:
            warnings = scan_staged_secrets(tmp_root)
            size_mb, size_warning = check_graphiti_size(tmp_root)
        finally:
            del os.environ["GRAPHITI_SKIP"]

        if not warnings:
            r.ok("scan_staged_secrets returns [] with GRAPHITI_SKIP=1")
        else:
            r.fail(
                "GRAPHITI_SKIP=1 did not bypass scan_staged_secrets",
                detail=f"Got warnings: {warnings}",
            )

        if size_mb == 0.0 and size_warning is None:
            r.ok("check_graphiti_size returns (0.0, None) with GRAPHITI_SKIP=1")
        else:
            r.fail(
                "GRAPHITI_SKIP=1 did not bypass check_graphiti_size",
                detail=f"Got: ({size_mb}, {size_warning!r})",
            )


# ── Test 4: check_graphiti_size thresholds ────────────────────────────────────
def test_size_check(r: Runner) -> None:
    r.banner("Test 4: check_graphiti_size Thresholds (R8.1 — hooks.py)")

    from src.gitops.hooks import check_graphiti_size, SIZE_WARNING_MB, SIZE_STRONG_WARNING_MB

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)

        # No .graphiti dir → (0.0, None)
        size_mb, warning = check_graphiti_size(tmp_root)
        if size_mb == 0.0 and warning is None:
            r.ok("No .graphiti dir → (0.0, None)")
        else:
            r.fail(
                "Expected (0.0, None) for missing .graphiti dir",
                detail=f"Got: ({size_mb}, {warning!r})",
            )

        # Small .graphiti dir (a few bytes) → no warning
        graphiti_dir = tmp_root / ".graphiti"
        graphiti_dir.mkdir()
        small_file = graphiti_dir / "index-state.json"
        small_file.write_text('{"last_sha": null, "processed": []}')

        size_mb, warning = check_graphiti_size(tmp_root)
        if warning is None and size_mb < SIZE_WARNING_MB:
            r.ok(f"Small .graphiti dir ({size_mb:.3f} MB) → no warning")
        else:
            r.fail(
                f"Unexpected warning for small .graphiti dir",
                detail=f"size_mb={size_mb:.3f}, warning={warning!r}",
            )

        # Verify threshold constants are sane
        if SIZE_WARNING_MB == 50 and SIZE_STRONG_WARNING_MB == 100:
            r.ok(f"Thresholds are correct: warn={SIZE_WARNING_MB}MB, strong={SIZE_STRONG_WARNING_MB}MB")
        else:
            r.fail(
                f"Unexpected threshold values: warn={SIZE_WARNING_MB}, strong={SIZE_STRONG_WARNING_MB}",
                detail="Expected SIZE_WARNING_MB=50, SIZE_STRONG_WARNING_MB=100",
            )

        r.info(
            f"Note: 50MB+ and 100MB+ thresholds require creating large files to test — "
            "skipped (unit-level threshold logic is sufficient)"
        )


# ── Test 5: Hook installation idempotency ─────────────────────────────────────
def test_hook_idempotency(r: Runner) -> None:
    r.banner("Test 5: Hook Installation Idempotency (R8.1 — installer.py)")

    # Run graphiti hooks install twice in the real project
    r.info("Running 'graphiti hooks install' twice...")

    res1 = subprocess.run(
        [GRAPHITI, "hooks", "install"],
        capture_output=True, text=True, cwd=ROOT, timeout=30,
    )
    res2 = subprocess.run(
        [GRAPHITI, "hooks", "install"],
        capture_output=True, text=True, cwd=ROOT, timeout=30,
    )

    if res1.returncode != 0:
        r.fail(
            "First 'graphiti hooks install' failed",
            detail=(res1.stderr or res1.stdout).strip()[:200],
        )
        return
    if res2.returncode != 0:
        r.fail(
            "Second 'graphiti hooks install' failed",
            detail=(res2.stderr or res2.stdout).strip()[:200],
        )
        return
    r.ok("Both installs exited 0")

    # Check each managed hook file for exactly one GRAPHITI_HOOK_START marker
    hooks_dir = ROOT / ".git" / "hooks"
    hooks_to_check = ["post-commit", "pre-commit", "post-merge", "post-checkout", "post-rewrite"]

    all_ok = True
    for hook_name in hooks_to_check:
        hook_file = hooks_dir / hook_name
        if not hook_file.exists():
            r.info(f"  {hook_name}: not installed (OK — may not be managed by graphiti)")
            continue

        content = hook_file.read_text()
        count = content.count("GRAPHITI_HOOK_START")

        if count == 0:
            r.info(f"  {hook_name}: exists but has no GRAPHITI_HOOK_START (not managed)")
        elif count == 1:
            r.ok(f"{hook_name}: exactly 1 GRAPHITI_HOOK_START (no duplication)")
        else:
            r.fail(
                f"{hook_name}: {count} GRAPHITI_HOOK_START markers after double-install",
                detail="Marker-based idempotency is broken",
            )
            all_ok = False

    if all_ok:
        r.ok("All managed hooks pass idempotency check")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    fail_fast = "--fail-fast" in sys.argv

    print(f"\n{BOLD}Phase 07: Git Integration — Human Verification{RESET}")
    print(f"Requirements: R8.1 (Git-Safe Knowledge Graphs)")
    print(f"{YELLOW}Note: Journal/LFS/checkpoint tests are obsolete — Phase 7.1 removed those systems.{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites()

    test_gitignore_generation(r)
    test_secret_detection(r)
    test_graphiti_skip_bypass(r)
    test_size_check(r)
    test_hook_idempotency(r)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
