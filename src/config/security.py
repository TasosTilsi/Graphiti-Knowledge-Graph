"""Security configuration for secret detection and sanitization.

This module provides centralized configuration for:
- Entropy thresholds (aggressive per user decision)
- File exclusion patterns
- Redaction templates
- Audit logging settings
- detect-secrets plugin configuration
"""

from src.models.security import DetectionType

# Entropy thresholds (aggressive per user decision)
BASE64_ENTROPY_LIMIT = 3.5  # Default is 4.5, aggressive is 3.5
HEX_ENTROPY_LIMIT = 2.5  # Default is 3.0, aggressive is 2.5

# File size limit (skip large files)
MAX_FILE_SIZE_BYTES = 1_000_000  # 1MB

# Default file exclusion patterns
DEFAULT_FILE_EXCLUSIONS = [
    # Environment and secrets
    ".env",
    ".env.*",
    "*.env",
    "*secret*",
    "*credential*",
    "*password*",
    "*.key",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.jks",
    "*token*",
    # Directories (note trailing /)
    "node_modules/",
    ".git/",
    "venv/",
    ".venv/",
    "__pycache__/",
    ".pytest_cache/",
    # Test files (don't scan test fixtures)
    "tests/",
    "test/",
    "**/test_*.py",
    "**/*_test.py",
    "fixtures/",
    "mocks/",
    # Build artifacts
    "dist/",
    "build/",
    "*.egg-info/",
]

# Placeholder template
REDACTION_PLACEHOLDER = "[REDACTED:{type}]"

# Audit log settings
AUDIT_LOG_FILENAME = "audit.log"
AUDIT_LOG_MAX_BYTES = 10_000_000  # 10 MB
AUDIT_LOG_BACKUP_COUNT = 5

# detect-secrets plugin configuration
# Format: List of dicts with 'name' key and optional plugin-specific params
DETECT_SECRETS_PLUGINS = [
    {"name": "Base64HighEntropyString", "limit": BASE64_ENTROPY_LIMIT},
    {"name": "HexHighEntropyString", "limit": HEX_ENTROPY_LIMIT},
    {"name": "KeywordDetector"},
    {"name": "AWSKeyDetector"},
    {"name": "GitHubTokenDetector"},
    {"name": "JwtTokenDetector"},
    {"name": "PrivateKeyDetector"},
    {"name": "BasicAuthDetector"},
]

__all__ = [
    "BASE64_ENTROPY_LIMIT",
    "HEX_ENTROPY_LIMIT",
    "MAX_FILE_SIZE_BYTES",
    "DEFAULT_FILE_EXCLUSIONS",
    "REDACTION_PLACEHOLDER",
    "AUDIT_LOG_FILENAME",
    "AUDIT_LOG_MAX_BYTES",
    "AUDIT_LOG_BACKUP_COUNT",
    "DETECT_SECRETS_PLUGINS",
]
