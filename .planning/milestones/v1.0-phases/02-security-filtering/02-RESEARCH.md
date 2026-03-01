# Phase 2: Security Filtering - Research

**Researched:** 2026-02-03
**Domain:** Secret detection, PII sanitization, security filtering
**Confidence:** MEDIUM

## Summary

Security filtering for knowledge graphs requires defense-in-depth detection combining pattern matching, entropy analysis, and context awareness. The standard Python ecosystem offers mature libraries for secret detection (detect-secrets, TruffleHog) and PII detection (Microsoft Presidio), each addressing different aspects of the sanitization pipeline.

The research identifies detect-secrets as the most suitable library for secret scanning due to its lightweight design, extensive plugin system (28+ detectors), and enterprise-friendly baseline management. For aggressive detection matching user requirements, combining regex-based pattern matching with entropy detection (Shannon entropy thresholds of 3.0-4.5) catches both known secret formats and unknown high-randomness strings. Microsoft Presidio provides PII detection with spaCy-based NER, though it adds significant dependencies.

**Primary recommendation:** Use detect-secrets for secret detection with aggressive entropy thresholds, implement structured JSON audit logging with structlog, and design a layered sanitization architecture separating file-level exclusion from content-level detection.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| detect-secrets | 1.5.0+ | Secret detection and baseline management | Enterprise-grade tool by Yelp with 28+ detectors, lightweight for pre-commit hooks, backwards-compatible baseline system |
| structlog | 25.5.0+ | Structured audit logging | Production-ready JSON logging with processor chains, context binding, integration with stdlib logging |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| presidio-analyzer | Latest (2026) | PII detection with NER | When high-accuracy PII detection needed (adds spaCy dependency) |
| presidio-anonymizer | Latest (2026) | PII anonymization | Companion to presidio-analyzer for redaction/masking |
| secrets-patterns-db | Latest | Regex pattern database | Reference for building custom pattern sets (1600+ patterns) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| detect-secrets | TruffleHog | TruffleHog has 700+ detectors with API verification but is Go-based (harder Python integration) and resource-intensive |
| detect-secrets | Gitleaks | Gitleaks excels at git history scanning but is Go-based with less Python-friendly API |
| structlog | python-json-logger | python-json-logger is simpler but lacks processor chains and context binding |
| Presidio | spaCy directly | Presidio provides pre-built PII recognizers vs custom NER training |

**Installation:**
```bash
pip install detect-secrets>=1.5.0 structlog>=25.5.0
# Optional for PII detection:
# pip install presidio-analyzer presidio-anonymizer
# python -m spacy download en_core_web_lg
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── security/
│   ├── __init__.py
│   ├── detector.py         # Main SecretDetector class
│   ├── patterns.py         # Pattern definitions and entropy config
│   ├── sanitizer.py        # Sanitization logic and masking
│   ├── exclusions.py       # File/path exclusion logic
│   └── audit.py            # Audit logging with structlog
├── models/
│   └── security.py         # SanitizationResult, DetectionType enums
└── config/
    └── security.py         # Security configuration and thresholds
```

### Pattern 1: Layered Detection Pipeline
**What:** Multi-stage filtering from coarse-grained (file exclusion) to fine-grained (entity sanitization)
**When to use:** All security filtering scenarios - provides defense-in-depth

**Example:**
```python
# Stage 1: File-level exclusion (fast, pattern-based)
if is_excluded_file(file_path, exclusion_patterns):
    return FileExcluded(reason="matched pattern")

# Stage 2: Content scanning (detect-secrets integration)
from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings

secrets = SecretsCollection()
with default_settings():
    secrets.scan_file(file_path)

# Stage 3: High-entropy detection (custom thresholds)
for string in extract_strings(content):
    if calculate_entropy(string) > ENTROPY_THRESHOLD:
        findings.append(HighEntropyString(string))

# Stage 4: Sanitization and masking
sanitized = mask_secrets(content, findings)
```

### Pattern 2: Typed Placeholder Masking
**What:** Replace detected secrets with descriptive placeholders indicating secret type
**When to use:** When sanitized content needs debugging context

**Example:**
```python
PLACEHOLDER_TEMPLATES = {
    "aws_access_key": "[REDACTED:aws_key]",
    "github_token": "[REDACTED:github_token]",
    "jwt": "[REDACTED:jwt]",
    "high_entropy": "[REDACTED:high_entropy]",
    "generic_api_key": "[REDACTED:api_key]",
}

def mask_secret(content: str, finding: SecretFinding) -> str:
    """Replace secret with typed placeholder preserving context."""
    placeholder = PLACEHOLDER_TEMPLATES.get(
        finding.secret_type,
        f"[REDACTED:{finding.secret_type}]"
    )
    return content.replace(finding.matched_text, placeholder)
```

### Pattern 3: Allowlist with Explicit Opt-In
**What:** Per-project allowlist stored in `.graphiti/allowlist` with hash-based verification
**When to use:** False positives requiring developer acknowledgment

**Example:**
```python
# .graphiti/allowlist format (JSON)
{
    "allowed_patterns": [
        "sha256:abc123...",  # Hash of false positive string
        "sha256:def456..."
    ],
    "comments": {
        "sha256:abc123...": "Test fixture UUID, not a secret"
    }
}

def is_allowlisted(finding: SecretFinding, allowlist_path: Path) -> bool:
    """Check if finding is explicitly allowlisted."""
    finding_hash = hashlib.sha256(finding.matched_text.encode()).hexdigest()
    allowlist = load_allowlist(allowlist_path)
    return f"sha256:{finding_hash}" in allowlist["allowed_patterns"]
```

### Pattern 4: Structured Audit Logging
**What:** JSON audit logs with correlation IDs for traceability
**When to use:** All sanitization events for compliance and debugging

**Example:**
```python
# Source: https://betterstack.com/community/guides/logging/structlog/
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

audit_logger = structlog.get_logger("audit.security")

def log_sanitization_event(finding: SecretFinding, action: str):
    """Log security event with full context."""
    audit_logger.info(
        "secret_detected",
        event_type="sanitization",
        action=action,  # "masked", "blocked", "allowlisted"
        secret_type=finding.secret_type,
        file_path=finding.file_path,
        line_number=finding.line_number,
        confidence=finding.confidence,
        entropy_score=finding.entropy_score if finding.entropy_score else None,
    )
```

### Anti-Patterns to Avoid
- **Blocking storage on detection:** User decided "storage never blocked" - always store sanitized version, never fail
- **Silent sanitization:** Every secret detection must be audit logged
- **Single detection method:** Combine pattern matching AND entropy detection for aggressive coverage
- **Hardcoded patterns:** Use detect-secrets plugin system for maintainability
- **Context-free allowlisting:** Allowlist should be per-project, not global

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret pattern matching | Custom regex collection | detect-secrets plugins | 28+ battle-tested detectors, ReDos protection, regularly updated patterns |
| Entropy calculation | Custom Shannon entropy | detect-secrets Base64HighEntropyString/HexHighEntropyString | Tuned thresholds (3.0/4.5), handles base64/hex encoding edge cases |
| PII detection | Custom NER training | Microsoft Presidio | Pre-trained recognizers for 20+ PII types, context-aware detection |
| Audit logging | Manual JSON formatting | structlog | Processor chains, context binding, stdlib integration, exception handling |
| File pattern exclusion | fnmatch loops | pathspec library or detect-secrets --exclude-files | Handles gitignore-style patterns, glob combinations, edge cases |
| Secret verification | Ping APIs manually | TruffleHog (if needed) | 700+ detectors with API verification, reduces false positives |

**Key insight:** Secret detection has severe edge cases (encoding, obfuscation, split strings, context-dependent false positives). Mature libraries have handled years of real-world bypass attempts and encoding schemes. Custom implementations miss edge cases and create security gaps.

## Common Pitfalls

### Pitfall 1: Insufficient Entropy Thresholds
**What goes wrong:** Default entropy thresholds (4.5 for base64) miss moderate-entropy secrets like short API keys
**Why it happens:** Tools optimize for low false positive rates, not aggressive detection
**How to avoid:** User specified "very aggressive" - lower thresholds to 3.0-4.0 and accept higher false positive rate
**Warning signs:** Known test secrets pass through detection

### Pitfall 2: Pattern-Only Detection Missing Custom Secrets
**What goes wrong:** Only using regex patterns misses organization-specific tokens and randomly generated credentials
**Why it happens:** Over-reliance on known patterns from databases like secrets-patterns-db
**How to avoid:** Combine pattern matching with entropy detection as parallel detection paths
**Warning signs:** Custom API keys from internal services not detected

### Pitfall 3: File Exclusion Bypass via Symlinks
**What goes wrong:** Excluded files (.env) accessed through symlinks circumvent file-level filtering
**Why it happens:** Path matching on symlink path instead of resolved real path
**How to avoid:** Resolve symlinks with `Path.resolve()` before exclusion checking
**Warning signs:** Test shows .env symlink content reaches sanitizer

### Pitfall 4: False Positive Fatigue Leading to Allowlist Abuse
**What goes wrong:** Developers add real secrets to allowlist due to alert overload
**Why it happens:** Too many false positives without clear remediation guidance
**How to avoid:** Audit log shows allowlist additions, require comment explaining why allowlisted, periodic allowlist review
**Warning signs:** Allowlist growing rapidly, comments missing or vague

### Pitfall 5: Split String Secrets Bypass Detection
**What goes wrong:** Secrets concatenated from multiple strings or variables bypass both pattern and entropy detection
**Why it happens:** Detectors scan final strings, not construction logic
**How to avoid:** Document limitation, focus on content-at-rest (what enters graph), not source code analysis
**Warning signs:** Manual review finds concatenated secrets in source

### Pitfall 6: Test Data Contamination
**What goes wrong:** Test fixtures with fake secrets trigger detection, pollute allowlist
**Why it happens:** Test files not excluded from scanning
**How to avoid:** Default exclusions should include `tests/`, `test_*.py`, `*_test.py`, `fixtures/`, `mocks/`
**Warning signs:** Allowlist dominated by test file paths

### Pitfall 7: Encoding Bypass (Base64, Hex, URL encoding)
**What goes wrong:** Secrets encoded before detection run bypass pattern matching
**Why it happens:** Patterns match specific formats, encoded versions different
**How to avoid:** Use detect-secrets entropy detectors (Base64HighEntropyString) which detect encoded high-entropy strings
**Warning signs:** Base64 strings in content not flagged

### Pitfall 8: Audit Log Explosion Without Retention
**What goes wrong:** Audit logs grow unbounded, fill disk, or get lost
**Why it happens:** No log rotation or retention policy configured
**How to avoid:** Use Python logging.handlers.RotatingFileHandler or TimedRotatingFileHandler for audit logs
**Warning signs:** Audit log file size grows without bound

## Code Examples

Verified patterns from official sources:

### Entropy Detection with detect-secrets
```python
# Source: https://github.com/Yelp/detect-secrets
from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings

# Configure aggressive entropy thresholds
settings = default_settings()
settings.plugins = {
    "Base64HighEntropyString": {"base64_limit": 3.5},  # Aggressive (default 4.5)
    "HexHighEntropyString": {"hex_limit": 2.5},        # Aggressive (default 3.0)
    "KeywordDetector": {},
    "AWSKeyDetector": {},
    "GitHubTokenDetector": {},
    "JwtTokenDetector": {},
}

secrets = SecretsCollection()
with settings:
    # Scan file or string
    secrets.scan_file("path/to/file.py")

    # Check if secrets found
    if secrets.files:
        for filename, secret_list in secrets.files.items():
            for secret in secret_list:
                print(f"Found {secret.type} at line {secret.line_number}")
```

### Pattern Matching for Known Secret Types
```python
# Source: https://github.com/mazen160/secrets-patterns-db (pattern concepts)
# Source: https://github.com/Yelp/detect-secrets (implementation)

KNOWN_SECRET_PATTERNS = {
    "aws_access_key": r"(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
    "aws_secret_key": r"(?i)aws(.{0,20})?(?-i)['\"][0-9a-zA-Z/+]{40}['\"]",
    "github_token": r"(?i)github[_\-\.]?token['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9]{35,40})['\"]?",
    "jwt": r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
    "generic_api_key": r"(?i)(api[_\-]?key|apikey|secret[_\-]?key)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-._~+/]{16,})['\"]?",
    "private_key": r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----",
    "connection_string": r"(?i)(mongodb|postgres|mysql|redis)://[^\s]+",
}

def detect_known_patterns(content: str) -> list[SecretFinding]:
    """Detect secrets using known patterns."""
    findings = []
    for secret_type, pattern in KNOWN_SECRET_PATTERNS.items():
        matches = re.finditer(pattern, content)
        for match in matches:
            findings.append(SecretFinding(
                secret_type=secret_type,
                matched_text=match.group(0),
                line_number=content[:match.start()].count('\n') + 1,
                confidence="high",
            ))
    return findings
```

### File Exclusion with Path Patterns
```python
# Source: https://github.com/Yelp/detect-secrets (pattern concepts)
from pathlib import Path
import fnmatch

DEFAULT_EXCLUSIONS = [
    # Environment and secrets
    ".env", ".env.*", "*.env",
    "*secret*", "*credential*", "*password*",
    "*.key", "*.pem", "*.p12", "*.pfx", "*.jks",

    # Directories
    "node_modules/", ".git/", "venv/", ".venv/",
    "__pycache__/", ".pytest_cache/",

    # Test files
    "tests/", "test/", "**/test_*.py", "**/*_test.py",
    "fixtures/", "mocks/",

    # Build artifacts
    "dist/", "build/", "*.egg-info/",
]

def is_excluded_file(file_path: Path, exclusions: list[str] = None) -> bool:
    """Check if file matches exclusion patterns."""
    if exclusions is None:
        exclusions = DEFAULT_EXCLUSIONS

    # Resolve symlinks to prevent bypass
    resolved_path = file_path.resolve()
    path_str = str(resolved_path)

    for pattern in exclusions:
        # Handle directory patterns
        if pattern.endswith('/'):
            if f"/{pattern}" in f"/{path_str}/":
                return True
        # Handle glob patterns
        elif fnmatch.fnmatch(path_str, f"*{pattern}*"):
            return True

    return False
```

### Structured Audit Logging Configuration
```python
# Source: https://betterstack.com/community/guides/logging/structlog/
import structlog
import logging
from logging.handlers import RotatingFileHandler

# Configure stdlib logging for file output
logging.basicConfig(
    format="%(message)s",
    handlers=[
        RotatingFileHandler(
            ".graphiti/audit.log",
            maxBytes=10_000_000,  # 10 MB
            backupCount=5,
        )
    ],
    level=logging.INFO,
)

# Configure structlog for JSON output
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Create audit logger
audit_logger = structlog.get_logger("audit.security")

# Usage
def audit_sanitization(event_type: str, **context):
    """Log sanitization event with context."""
    audit_logger.info(event_type, **context)

# Example
audit_sanitization(
    "secret_masked",
    secret_type="aws_key",
    file_path="/path/to/file.py",
    line_number=42,
    action="masked",
    placeholder="[REDACTED:aws_key]",
)
```

### Allowlist Management
```python
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class AllowlistEntry:
    """Entry in allowlist with metadata."""
    hash: str
    comment: str
    added_date: str
    added_by: str

class Allowlist:
    """Manage per-project allowlist for false positives."""

    def __init__(self, project_root: Path):
        self.path = project_root / ".graphiti" / "allowlist.json"
        self._load()

    def _load(self):
        """Load allowlist from disk."""
        if self.path.exists():
            with open(self.path) as f:
                data = json.load(f)
                self.entries = {
                    h: AllowlistEntry(
                        hash=h,
                        comment=data["comments"].get(h, ""),
                        added_date=data["metadata"].get(h, {}).get("added_date", ""),
                        added_by=data["metadata"].get(h, {}).get("added_by", ""),
                    )
                    for h in data["allowed_patterns"]
                }
        else:
            self.entries = {}

    def is_allowed(self, finding: str) -> bool:
        """Check if finding is allowlisted."""
        finding_hash = self._hash(finding)
        return finding_hash in self.entries

    def add(self, finding: str, comment: str, added_by: str):
        """Add finding to allowlist with metadata."""
        from datetime import datetime

        finding_hash = self._hash(finding)
        self.entries[finding_hash] = AllowlistEntry(
            hash=finding_hash,
            comment=comment,
            added_date=datetime.now().isoformat(),
            added_by=added_by,
        )
        self._save()

    @staticmethod
    def _hash(text: str) -> str:
        """Generate SHA256 hash for allowlist key."""
        return f"sha256:{hashlib.sha256(text.encode()).hexdigest()}"

    def _save(self):
        """Save allowlist to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "allowed_patterns": list(self.entries.keys()),
            "comments": {h: e.comment for h, e in self.entries.items()},
            "metadata": {
                h: {"added_date": e.added_date, "added_by": e.added_by}
                for h, e in self.entries.items()
            },
        }
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Regex-only detection | Regex + entropy + AI validation | 2024-2025 | Higher recall, context-aware false positive reduction |
| Pre-commit hooks only | Continuous + pre-commit + IDE integration | 2025 | Shift-left security, earlier detection |
| Manual pattern maintenance | Curated databases (secrets-patterns-db, 1600+ patterns) | 2023-2024 | Reduced maintenance burden, community patterns |
| Generic secret detection | Type-specific verification via API calls | 2024 (TruffleHog v3) | Confirms live secrets vs expired tokens |
| Scheduled scanning | Triggered on every commit | 2025 | Seconds to detection vs hours/days |

**Deprecated/outdated:**
- **git-secrets (AWS Labs):** Still functional but limited pattern set, prefer detect-secrets or Gitleaks
- **TruffleHog v2:** Superseded by v3 rewrite in Go with verification
- **Manual entropy calculation:** Libraries provide tuned thresholds and encoding awareness

## Open Questions

Things that couldn't be fully resolved:

1. **PII Detection Scope and Necessity**
   - What we know: Presidio provides robust PII detection but adds spaCy dependency (100+ MB models)
   - What's unclear: Whether PII detection is in scope for this phase or deferred. User context mentions "PII detection with confidence thresholds" but prioritizes secrets. R3.2 includes PII detection.
   - Recommendation: Implement secrets detection first (required), add Presidio PII detection as optional plugin with lazy loading. User can enable if needed without mandatory dependency.

2. **Custom Pattern Additions**
   - What we know: User mentioned "pattern library maintenance and updates" under Claude's discretion
   - What's unclear: Whether project needs custom patterns beyond detect-secrets' 28+ built-in detectors
   - Recommendation: Start with detect-secrets defaults, add custom patterns only when needed. Log unknown secret-like strings for pattern development.

3. **Entropy Threshold Tuning**
   - What we know: User wants "very aggressive" detection. Standard thresholds are base64=4.5, hex=3.0
   - What's unclear: Exact false positive rate acceptable to user
   - Recommendation: Start with base64=3.5, hex=2.5 (aggressive but not extreme). Provide configuration option. Monitor audit logs for false positive rate and adjust based on user feedback.

4. **Audit Log Retention and Storage Location**
   - What we know: User marked as Claude's discretion
   - What's unclear: How long to retain, where to store (per-project vs global), max size
   - Recommendation: Per-project `.graphiti/audit.log` with 5-file rotation at 10MB per file (50MB total). Retention configurable. Follows project-scoped pattern from Phase 1.

5. **Performance Impact on Large Files**
   - What we know: detect-secrets scans files, entropy calculation can be expensive on large files
   - What's unclear: Performance requirements, whether to skip large files (e.g., >10MB)
   - Recommendation: Add configurable file size limit (default 1MB) with warning log for skipped files. Large files typically binary (already excluded) or generated code (should be excluded).

## Sources

### Primary (HIGH confidence)
- GitHub: Yelp/detect-secrets - https://github.com/Yelp/detect-secrets - Plugin system, entropy thresholds, baseline management, API usage
- Microsoft Presidio Analyzer - https://microsoft.github.io/presidio/analyzer/ - PII detection, recognizers, installation
- Microsoft Presidio Installation - https://microsoft.github.io/presidio/installation/ - Python version requirements, dependencies
- Better Stack structlog guide - https://betterstack.com/community/guides/logging/structlog/ - Production configuration, processors, audit logging patterns

### Secondary (MEDIUM confidence)
- [Python Secret Detection Best Practices 2026](https://blog.gitguardian.com/how-to-handle-secrets-in-python/) - GitGuardian blog on secret management
- [Top 7 Secret Scanning Tools for 2026](https://www.apono.io/blog/top-7-secret-scanning-tools-for-2026/) - Tool comparison and rankings
- [TruffleHog vs Gitleaks Comparison](https://www.jit.io/resources/appsec-tools/trufflehog-vs-gitleaks-a-detailed-comparison-of-secret-scanning-tools) - Detailed tool comparison
- [Secret Scanner Comparison](https://medium.com/@navinwork21/secret-scanner-comparison-finding-your-best-tool-ed899541b9b6) - Tool evaluation
- [Secrets Patterns DB](https://github.com/mazen160/secrets-patterns-db) - 1600+ regex patterns for secret detection
- [GitHub Secret Scanning Patterns](https://docs.github.com/en/code-security/secret-scanning/introduction/supported-secret-scanning-patterns) - Official GitHub patterns
- [Python Logging Best Practices](https://www.apriorit.com/dev-blog/cybersecurity-logging-python) - Security logging guidance
- [Structured Logging Best Practices](https://uptrace.dev/glossary/structured-logging) - JSON logging patterns

### Tertiary (LOW confidence)
- [Secret Detection False Positives Study](https://link.springer.com/article/10.1007/s10664-021-10109-y) - Academic research on false positives and developer behavior
- [FPSecretBench Dataset](https://github.com/setu1421/FPSecretBench) - False positive test cases from 9 tools
- [Using AI to Reduce False Positives](https://www.legitsecurity.com/blog/using-ai-to-reduce-false-positives-in-secrets-scanners) - AI-assisted detection trends

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - detect-secrets and structlog are well-established, verified from official sources
- Architecture: MEDIUM - Patterns based on best practices but adapted for knowledge graph context (novel application)
- Pitfalls: MEDIUM - Mix of verified industry pitfalls and inferred issues specific to this use case
- PII detection: LOW - Presidio verified but unclear if in scope for this phase

**Research date:** 2026-02-03
**Valid until:** ~30 days (stable domain, but security patterns evolve with new secret types)

**Notes:**
- User decisions from CONTEXT.md strongly constrain implementation: aggressive detection, typed placeholders, always-store sanitized content, per-project allowlist
- Phase depends on Phase 1 storage layer (already complete)
- Integration point: Sanitization happens BEFORE content reaches `GraphManager.get_driver()` - needs middleware layer
- Future phases: Git integration (Phase 7) will need git-safe sanitization validation, but implementation is separate
