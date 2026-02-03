---
phase: 02-security-filtering
plan: 04
type: execute
subsystem: security
tags: [sanitization, masking, placeholders, audit-logging, integration]
requires: [02-02-detector, 02-03-allowlist]
provides:
  - content-sanitizer
  - typed-placeholder-masking
  - integrated-pipeline
affects: [02-05-tests]
tech-stack:
  added: []
  patterns:
    - integration-pipeline
    - defense-in-depth
key-files:
  created:
    - src/security/sanitizer.py
  modified:
    - src/security/__init__.py
decisions:
  - id: typed-placeholders
    choice: "[REDACTED:type] format for masked secrets"
    rationale: "Preserves detection type information for debugging while redacting actual values"
    alternatives: "Generic [REDACTED] placeholder, hash-based placeholders"
  - id: storage-never-blocked
    choice: "Always return sanitized content, never block storage"
    rationale: "User decision - prioritize data preservation, rely on sanitization quality"
    alternatives: "Block storage if secrets detected, require manual review"
metrics:
  duration: 159
  tasks: 2
  commits: 2
  files_modified: 2
  files_created: 1
completed: 2026-02-03
---

# Phase 02 Plan 04: Content Sanitizer with Typed Placeholders Summary

**One-liner:** Defense-in-depth sanitization pipeline integrating detection, allowlisting, and typed placeholder masking ([REDACTED:aws_key], [REDACTED:high_entropy]) with complete audit logging.

## What Was Built

### Core Components

**ContentSanitizer class** (`src/security/sanitizer.py`)
- Integrates SecretDetector, Allowlist, and audit logging
- Four-step sanitization pipeline:
  1. Detect secrets using pattern + entropy detection
  2. Filter out allowlisted findings
  3. Mask remaining secrets with typed placeholders
  4. Build SanitizationResult with original + sanitized content
- **Storage never blocked** - always returns sanitized content
- Preserves original content in result for debugging

**Typed Placeholder System**
- Maps each DetectionType to specific placeholder suffix
- Format: `[REDACTED:type]` where type is semantic (aws_key, github_token, high_entropy, etc.)
- Provides debugging information while masking actual values
- Configured via REDACTION_PLACEHOLDER template in config

**File-Level Integration**
- `should_process_file()` - checks exclusions before processing
- `sanitize_file()` - complete file processing workflow
- Excluded files return None (blocked at file level)
- Normal files return SanitizationResult

**Public API** (`src/security/__init__.py`)
- Clean exports organized by function
- Main entry points: `sanitize_content()`, `ContentSanitizer`
- Simple usage: `result = sanitize_content(text)`
- File usage: `sanitizer.sanitize_file(path)`

## Architecture

```
File Input
    ↓
should_process_file() → [is_excluded_file?] → Yes → None
    ↓ No
sanitize_file()
    ↓
sanitize() → [SecretDetector.detect()]
    ↓
[Allowlist.is_allowed?] → Yes → log allowlist check
    ↓ No
[Replace with placeholder] + log_sanitization_event
    ↓
SanitizationResult (original + sanitized + findings)
```

**Defense-in-depth layers:**
1. File exclusions (block sensitive files)
2. Secret detection (find patterns + entropy)
3. Allowlist override (handle false positives)
4. Typed masking (replace with placeholders)
5. Audit logging (track all events)

## Tasks Completed

| Task | Description | Files | Commit |
|------|-------------|-------|--------|
| 1 | Create content sanitizer | sanitizer.py | cc85048 |
| 2 | Integrate file exclusions and create pipeline | sanitizer.py, __init__.py | 3feb1d5 |

## Decisions Made

### 1. Typed Placeholders Format
**Decision:** Use `[REDACTED:type]` format with semantic type suffixes

**Context:** Need to mask secrets while preserving debugging information

**Options considered:**
- Generic `[REDACTED]` - simple but loses type information
- Hash-based `[REDACTED:sha256]` - unique but not human-readable
- Typed `[REDACTED:aws_key]` - semantic and debuggable

**Chosen:** Typed placeholders
- Preserves what *type* of secret was detected
- Helps debug false positives
- Human-readable in logs
- No actual secret value exposed

**Impact:** Detection type mapping required, but provides better developer experience

### 2. Storage Never Blocked
**Decision:** Always return sanitized content, never raise exceptions or block storage

**Context:** User decision from planning phase - prioritize data preservation

**Rationale:**
- Trust sanitization quality (defense-in-depth approach)
- Prefer false positives over data loss
- Knowledge graph should always receive data (sanitized)
- Audit logs provide transparency for review

**Implementation:** All methods return results, never raise for detected secrets

## Implementation Details

### Placeholder Type Mapping
```python
PLACEHOLDER_TYPE_MAP = {
    DetectionType.AWS_KEY: "aws_key",
    DetectionType.GITHUB_TOKEN: "github_token",
    DetectionType.JWT: "jwt",
    DetectionType.GENERIC_API_KEY: "api_key",
    DetectionType.PRIVATE_KEY: "private_key",
    DetectionType.CONNECTION_STRING: "connection_string",
    DetectionType.HIGH_ENTROPY_BASE64: "high_entropy",
    DetectionType.HIGH_ENTROPY_HEX: "high_entropy",
}
```

### Sanitization Flow
1. **Detection:** `SecretDetector.detect()` returns list of SecretFinding
2. **Allowlist check:** For each finding, check `Allowlist.is_allowed()`
   - If allowed: increment counter, log allowlist check, skip masking
   - If not allowed: add to findings_to_mask list
3. **Masking:** Replace matched_text with typed placeholder
4. **Logging:** `log_sanitization_event()` for each masked secret
5. **Result:** Return SanitizationResult with both original and sanitized

### Integration Points
- **Detector:** Uses `SecretDetector.detect()` for finding secrets
- **Allowlist:** Uses `Allowlist.is_allowed()` and `get_entry()` for overrides
- **Audit:** Uses `get_audit_logger()` and `log_sanitization_event()`
- **Exclusions:** Uses `is_excluded_file()` for file-level filtering

## Deviations from Plan

None - plan executed exactly as written.

## Testing & Verification

All verification criteria met:
- ✓ Imports from `src.security` work
- ✓ Excluded files (*.env, *secret*) return None
- ✓ Normal files return SanitizationResult
- ✓ Detected secrets replaced with `[REDACTED:type]` placeholders
- ✓ Allowlisted items not masked
- ✓ All events logged to audit.log

**Manual verification:**
```python
# Test typed placeholders
result = sanitize_content('AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"')
# Produces: 'AWS_ACCESS_KEY_ID = "[REDACTED:aws_key]"'

# Test file exclusions
sanitizer.sanitize_file(Path('.env'))  # Returns None
sanitizer.sanitize_file(Path('main.py'))  # Returns SanitizationResult

# Original preserved
assert result.original_content == original
assert result.sanitized_content != original  # Modified
```

## Files Modified

**Created:**
- `src/security/sanitizer.py` (154 lines)
  - ContentSanitizer class
  - get_placeholder() function
  - sanitize_content() convenience function
  - PLACEHOLDER_TYPE_MAP constant

**Modified:**
- `src/security/__init__.py`
  - Added sanitizer exports
  - Updated docstring with usage examples
  - Organized exports by function

## Next Phase Readiness

**Provides for 02-05 (Security Tests):**
- `ContentSanitizer` class ready for testing
- `sanitize_content()` convenience function
- Complete pipeline for integration tests
- All components integrated and verified

**Blockers:** None

**Concerns:** None - implementation matches plan exactly

## Performance Notes

**Duration:** 159 seconds (2.7 minutes)
- Task 1 (sanitizer): ~80 seconds
- Task 2 (integration): ~70 seconds
- Verification: ~10 seconds

**Efficiency:**
- Clean integration - no rework needed
- All APIs aligned from previous plans
- Verification passed first try

## Lessons Learned

### What Went Well
1. **Modular architecture paid off** - Clean APIs from detector, allowlist, audit made integration trivial
2. **Typed placeholders** - Semantic suffixes provide excellent debugging experience
3. **Defense-in-depth** - Multiple layers (exclusions, detection, allowlist, masking, audit) provide robust security

### Patterns to Reuse
- **Integration pipeline pattern** - Layer multiple security checks with audit logging
- **Typed placeholders** - Semantic masking that preserves metadata
- **Storage never blocked** - Trust sanitization, preserve data, log everything

### Improvements for Next Plans
- Consider placeholder customization (user-defined formats)
- Add metrics for sanitization performance (secrets found, allowlisted, masked)
