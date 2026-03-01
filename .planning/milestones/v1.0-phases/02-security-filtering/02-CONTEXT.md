# Phase 2: Security Filtering - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement defense-in-depth security filtering to prevent secrets and PII from entering knowledge graphs. Content is sanitized before storage — secrets are detected and masked with placeholders. This phase covers detection, masking, and audit logging. Git-safe validation and merge conflict handling are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Detection Sensitivity
- Very aggressive detection — prefer false positives over leaking secrets
- Both known patterns AND high-entropy strings are flagged
- Known patterns include: AWS keys, GitHub tokens, JWTs, API keys, private keys, connection strings
- High-entropy detection catches random-looking strings that might be secrets

### Masking Behavior
- Secrets are replaced with typed placeholders: `[REDACTED:type]`
- Examples: `[REDACTED:aws_key]`, `[REDACTED:github_token]`, `[REDACTED:high_entropy]`
- Sanitized content IS stored — preserves context while removing secrets
- Storage never blocked — always store the sanitized version

### Allowlisting
- Optional per-project allowlist available (disabled by default)
- Users can add false positives to `.graphiti/allowlist` if needed
- Maximum security by default, escape hatch for edge cases

### Claude's Discretion
- File exclusion patterns (defaults for .env*, *secret*, *.key, etc.)
- Audit log format, retention, and storage location
- Entropy threshold tuning
- Pattern library maintenance and updates

</decisions>

<specifics>
## Specific Ideas

- "We should be very aggressive" — user explicitly prioritized catching secrets over false positive concerns
- Placeholders should indicate WHAT was redacted for debugging/context

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-security-filtering*
*Context gathered: 2026-02-03*
