"""Security models for secret detection and sanitization.

This module provides the core data types for the security filtering system:
- DetectionType: Enum of secret types that can be detected
- SecretFinding: Individual secret detection result
- SanitizationResult: Output from sanitizing content
- FileExclusionResult: Result from file exclusion checks
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal, Optional


class DetectionType(Enum):
    """Types of secrets that can be detected."""

    # Specific secret patterns
    AWS_KEY = "aws_key"
    GITHUB_TOKEN = "github_token"
    JWT = "jwt"
    GENERIC_API_KEY = "generic_api_key"
    PRIVATE_KEY = "private_key"
    CONNECTION_STRING = "connection_string"

    # Entropy-based detection
    HIGH_ENTROPY_BASE64 = "high_entropy_base64"
    HIGH_ENTROPY_HEX = "high_entropy_hex"

    # Override tracking
    ALLOWLISTED = "allowlisted"


@dataclass(frozen=True)
class SecretFinding:
    """A detected secret in content.

    Attributes:
        detection_type: Type of secret detected
        matched_text: The actual text that matched
        line_number: Line number where secret was found (1-indexed)
        confidence: Detection confidence level
        entropy_score: Entropy score if detected via entropy (0.0-8.0)
        file_path: Path to file where secret was found (optional)
    """

    detection_type: DetectionType
    matched_text: str
    line_number: int
    confidence: Literal["high", "medium", "low"]
    entropy_score: Optional[float] = None
    file_path: Optional[str] = None


@dataclass(frozen=True)
class SanitizationResult:
    """Result of sanitizing content for secrets.

    Attributes:
        original_content: Original text before sanitization
        sanitized_content: Text after redacting secrets
        findings: List of secrets found and redacted
        allowlisted_count: Number of findings that were allowlisted
        was_modified: Whether content was changed (computed from findings)
    """

    original_content: str
    sanitized_content: str
    findings: list[SecretFinding]
    allowlisted_count: int = 0

    @property
    def was_modified(self) -> bool:
        """Check if sanitization modified the content."""
        return len(self.findings) > 0


@dataclass(frozen=True)
class FileExclusionResult:
    """Result of checking if a file should be excluded from scanning.

    Attributes:
        file_path: Path that was checked
        is_excluded: Whether file matches exclusion pattern
        matched_pattern: The pattern that caused exclusion (if any)
    """

    file_path: Path
    is_excluded: bool
    matched_pattern: Optional[str] = None


__all__ = [
    "DetectionType",
    "SecretFinding",
    "SanitizationResult",
    "FileExclusionResult",
]
