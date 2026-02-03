"""Secret detection using detect-secrets with aggressive thresholds.

Combines pattern-based detection (AWS keys, GitHub tokens, etc.)
with entropy-based detection (catches random-looking strings).
User decision: Very aggressive - prefer false positives over leaking secrets.
"""
import re
import tempfile
from pathlib import Path
from typing import Optional

from detect_secrets import SecretsCollection
from detect_secrets.settings import transient_settings

from src.config.security import DETECT_SECRETS_PLUGINS
from src.models.security import SecretFinding, DetectionType
from src.security.patterns import get_detection_type, get_confidence


class SecretDetector:
    """Detects secrets in content using detect-secrets library."""

    def __init__(self, plugins_config: list[dict] | None = None):
        """Initialize detector with plugin configuration.

        Args:
            plugins_config: Custom detect-secrets plugins config (list of plugin dicts).
                          Uses aggressive defaults if None.
        """
        self._plugins = plugins_config or DETECT_SECRETS_PLUGINS

    def detect(
        self,
        content: str,
        file_path: str | None = None,
    ) -> list[SecretFinding]:
        """Detect secrets in content.

        Args:
            content: Text content to scan
            file_path: Optional source file path for reporting

        Returns:
            List of SecretFinding objects for detected secrets
        """
        findings: list[SecretFinding] = []

        # detect-secrets requires file-based scanning, use temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Configure detect-secrets with our aggressive settings
            with transient_settings({"plugins_used": self._plugins}):
                secrets = SecretsCollection()
                secrets.scan_file(tmp_path)

                # Convert to our SecretFinding format
                # secrets is iterable, yielding (filename, PotentialSecret) tuples
                for detected_file, secret in secrets:
                    # Get the actual secret value from content
                    lines = content.split('\n')
                    if 0 < secret.line_number <= len(lines):
                        line = lines[secret.line_number - 1]
                        matched_text = self._extract_secret_from_line(
                            line, secret.type
                        )
                    else:
                        matched_text = "<detected_but_not_extracted>"

                    finding = SecretFinding(
                        detection_type=get_detection_type(secret.type),
                        matched_text=matched_text,
                        line_number=secret.line_number,
                        confidence=get_confidence(secret.type),
                        file_path=file_path,
                    )
                    findings.append(finding)
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

        return findings

    def _extract_secret_from_line(
        self,
        line: str,
        plugin_type: str
    ) -> str:
        """Extract the actual secret value from a line.

        detect-secrets gives us line numbers but not the exact match.
        We use patterns to extract the actual secret value.

        Args:
            line: The line containing the secret
            plugin_type: Type of detector that found it

        Returns:
            The extracted secret string
        """
        # Common extraction patterns
        # Note: detect-secrets returns human-readable type names
        patterns = {
            "AWS Access Key": r"(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
            "GitHub Token": r"(ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|ghu_[a-zA-Z0-9]{36}|ghs_[a-zA-Z0-9]{36}|ghr_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{22,})",
            "JSON Web Token": r"eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
            "Private Key": r"-----BEGIN[^-]+-----",
            "Base64 High Entropy String": r"[A-Za-z0-9+/]{20,}={0,2}",
            "Hex High Entropy String": r"[a-fA-F0-9]{20,}",
        }

        pattern = patterns.get(plugin_type)
        if pattern:
            match = re.search(pattern, line)
            if match:
                return match.group(0)

        # Fallback: return trimmed line (without obvious prefixes)
        # Remove common prefixes like "API_KEY = "
        cleaned = re.sub(r"^[A-Za-z_]+\s*[=:]\s*['\"]?", "", line.strip())
        cleaned = re.sub(r"['\"]?\s*$", "", cleaned)
        return cleaned if cleaned else line.strip()


def detect_secrets_in_content(
    content: str,
    file_path: str | None = None,
) -> list[SecretFinding]:
    """Convenience function to detect secrets in content.

    Args:
        content: Text to scan
        file_path: Optional source path

    Returns:
        List of detected secrets
    """
    detector = SecretDetector()
    return detector.detect(content, file_path)
