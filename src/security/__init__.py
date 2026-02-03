"""Security filtering for knowledge graphs.

Defense-in-depth security filtering to prevent secrets and PII
from entering knowledge graphs. Content is sanitized before
storage - secrets are detected and masked with placeholders.

Usage:
    from src.security import sanitize_content, ContentSanitizer

    # Simple usage
    result = sanitize_content("my content with API_KEY=secret123")
    safe_content = result.sanitized_content

    # With file processing
    sanitizer = ContentSanitizer()
    if sanitizer.should_process_file(Path("myfile.py")):
        result = sanitizer.sanitize_file(Path("myfile.py"))
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
from src.security.sanitizer import (
    ContentSanitizer,
    sanitize_content,
    get_placeholder,
)

__all__ = [
    # File exclusions
    "FileExcluder",
    "is_excluded_file",

    # Audit logging
    "SecurityAuditLogger",
    "get_audit_logger",
    "log_sanitization_event",

    # Secret detection
    "SecretDetector",
    "detect_secrets_in_content",
    "get_detection_type",
    "get_confidence",

    # Allowlist
    "Allowlist",
    "is_allowlisted",

    # Sanitization (main entry point)
    "ContentSanitizer",
    "sanitize_content",
    "get_placeholder",
]
