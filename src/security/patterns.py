"""Pattern definitions and detection type mapping for secret detection.

Maps detect-secrets plugin types to our DetectionType enum for
consistent categorization across the security filtering pipeline.
"""
from src.models.security import DetectionType

# Map detect-secrets plugin names to our DetectionType enum
# Note: detect-secrets returns human-readable type names like "AWS Access Key"
DETECTION_TYPE_MAP: dict[str, DetectionType] = {
    # AWS detectors
    "AWS Access Key": DetectionType.AWS_KEY,

    # GitHub
    "GitHub Token": DetectionType.GITHUB_TOKEN,

    # JWT
    "JSON Web Token": DetectionType.JWT,

    # Private keys
    "Private Key": DetectionType.PRIVATE_KEY,

    # Entropy-based
    "Base64 High Entropy String": DetectionType.HIGH_ENTROPY_BASE64,
    "Hex High Entropy String": DetectionType.HIGH_ENTROPY_HEX,

    # Generic patterns (Keyword, BasicAuth)
    "Secret Keyword": DetectionType.GENERIC_API_KEY,
    "Basic Authentication Credentials": DetectionType.GENERIC_API_KEY,
}

# Confidence mapping based on detection method
CONFIDENCE_MAP: dict[str, str] = {
    # Pattern-based detectors are high confidence
    "AWS Access Key": "high",
    "GitHub Token": "high",
    "JSON Web Token": "high",
    "Private Key": "high",

    # Entropy-based are medium (more false positives)
    "Base64 High Entropy String": "medium",
    "Hex High Entropy String": "medium",

    # Keyword-based are medium
    "Secret Keyword": "medium",
    "Basic Authentication Credentials": "medium",
}


def get_detection_type(plugin_name: str) -> DetectionType:
    """Get DetectionType for a detect-secrets plugin.

    Args:
        plugin_name: Name of detect-secrets plugin

    Returns:
        Corresponding DetectionType, defaults to GENERIC_API_KEY
    """
    return DETECTION_TYPE_MAP.get(plugin_name, DetectionType.GENERIC_API_KEY)


def get_confidence(plugin_name: str) -> str:
    """Get confidence level for a detect-secrets plugin.

    Args:
        plugin_name: Name of detect-secrets plugin

    Returns:
        Confidence level (high, medium, low)
    """
    return CONFIDENCE_MAP.get(plugin_name, "medium")
