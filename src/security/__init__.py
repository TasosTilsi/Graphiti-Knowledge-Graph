"""Security package for secret detection and sanitization.

This package provides:
- File exclusion system (prevents sensitive files from being scanned)
- Audit logging (structured JSON logs for all security events)
"""

from src.security.exclusions import FileExcluder, is_excluded_file
from src.security.audit import (
    SecurityAuditLogger,
    get_audit_logger,
    log_sanitization_event,
)

__all__ = [
    "FileExcluder",
    "is_excluded_file",
    "SecurityAuditLogger",
    "get_audit_logger",
    "log_sanitization_event",
]
