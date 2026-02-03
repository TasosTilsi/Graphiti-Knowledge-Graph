"""Security package for secret detection and sanitization.

This package provides:
- File exclusion system (prevents sensitive files from being scanned)
- Audit logging (structured JSON logs for all security events)
- Secret detection (pattern + entropy-based detection with detect-secrets)
- Allowlist management (per-project false positive handling)
"""

from src.security.exclusions import FileExcluder, is_excluded_file
from src.security.audit import (
    SecurityAuditLogger,
    get_audit_logger,
    log_sanitization_event,
)
from src.security.detector import SecretDetector, detect_secrets_in_content
from src.security.patterns import get_detection_type, get_confidence
from src.security.allowlist import Allowlist, is_allowlisted

__all__ = [
    "FileExcluder",
    "is_excluded_file",
    "SecurityAuditLogger",
    "get_audit_logger",
    "log_sanitization_event",
    "SecretDetector",
    "detect_secrets_in_content",
    "get_detection_type",
    "get_confidence",
    "Allowlist",
    "is_allowlisted",
]
