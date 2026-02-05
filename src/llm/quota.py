"""Quota tracking for cloud LLM usage.

This module provides quota monitoring via response headers or local counting,
with configurable warning thresholds to prevent hitting cloud limits.
"""

import time
from dataclasses import dataclass
from typing import Optional

import structlog

logger = structlog.get_logger()


@dataclass
class QuotaInfo:
    """Quota information from headers or local counting.

    Attributes:
        limit: Total quota limit if known
        remaining: Remaining quota if known
        reset_timestamp: Unix timestamp when quota resets
        usage_percent: Computed usage percentage (0-100)
        source: Where the info came from ("headers" or "local_count")
    """

    limit: Optional[int] = None
    remaining: Optional[int] = None
    reset_timestamp: Optional[float] = None
    usage_percent: Optional[float] = None
    source: str = "unknown"


class QuotaTracker:
    """Track cloud LLM quota usage with warnings.

    Attempts to extract quota information from response headers.
    Falls back to local request counting when headers unavailable.
    Logs warnings when usage exceeds configurable threshold.
    """

    def __init__(self, warning_threshold: float = 0.8):
        """Initialize quota tracker.

        Args:
            warning_threshold: Usage percent (0-1) to trigger warning.
                             Default 0.8 = warn at 80% usage.
        """
        self.warning_threshold = warning_threshold
        self._requests_made: int = 0  # Local counting fallback
        self._last_quota_info: Optional[QuotaInfo] = None
        self._logger = structlog.get_logger()

    def update_from_headers(self, headers: dict) -> Optional[QuotaInfo]:
        """Extract quota info from response headers.

        Checks for common rate-limit header names (case-insensitive).
        If found, calculates usage and checks threshold.

        Args:
            headers: Response headers dict (case-insensitive keys)

        Returns:
            QuotaInfo if headers available, None otherwise
        """
        # Normalize headers to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Try to extract rate limit headers
        limit_key = None
        remaining_key = None
        reset_key = None

        # Check for standard header names (lowercase)
        for key in headers_lower:
            if 'ratelimit-limit' in key or 'rate-limit-limit' in key:
                limit_key = key
            elif 'ratelimit-remaining' in key or 'rate-limit-remaining' in key:
                remaining_key = key
            elif 'ratelimit-reset' in key or 'rate-limit-reset' in key:
                reset_key = key

        # If we don't have limit and remaining, headers unavailable
        if not (limit_key and remaining_key):
            return None

        try:
            limit = int(headers_lower[limit_key])
            remaining = int(headers_lower[remaining_key])
            reset_timestamp = float(headers_lower[reset_key]) if reset_key else None

            # Calculate usage percentage
            usage_percent = 1.0 - (remaining / limit) if limit > 0 else 0.0

            # Create quota info
            info = QuotaInfo(
                limit=limit,
                remaining=remaining,
                reset_timestamp=reset_timestamp,
                usage_percent=usage_percent,
                source="headers"
            )

            # Check threshold and log warning if exceeded
            self.check_threshold(usage_percent)

            # Store for get_status()
            self._last_quota_info = info

            return info

        except (ValueError, KeyError, ZeroDivisionError) as e:
            # Header parsing failed, fall back to local counting
            self._logger.debug(
                "quota_header_parse_failed",
                error=str(e),
                headers=list(headers_lower.keys())
            )
            return None

    def increment_local_count(self) -> None:
        """Increment local request counter.

        Used as fallback when quota headers unavailable.
        Does NOT check threshold (no known limit to compare against).
        """
        self._requests_made += 1
        self._logger.debug(
            "local_quota_count",
            requests_made=self._requests_made,
            source="local_count"
        )

    def check_threshold(self, usage_percent: float) -> bool:
        """Check if usage exceeds warning threshold.

        Args:
            usage_percent: Usage as decimal (0.0-1.0)

        Returns:
            True if threshold exceeded, False otherwise
        """
        if usage_percent >= self.warning_threshold:
            self._logger.warning(
                "quota_threshold_exceeded",
                usage_percent=f"{usage_percent * 100:.1f}%",
                threshold_percent=f"{self.warning_threshold * 100:.1f}%",
                message=f"Cloud quota at {usage_percent * 100:.1f}% - approaching limit"
            )
            return True
        return False

    def get_status(self) -> QuotaInfo:
        """Get current quota status.

        Returns:
            QuotaInfo from last header update, or local count fallback
        """
        if self._last_quota_info:
            return self._last_quota_info

        # Fallback: return local count info
        return QuotaInfo(
            limit=None,
            remaining=None,
            reset_timestamp=None,
            usage_percent=None,
            source="local_count"
        )

    def reset(self) -> None:
        """Reset quota tracking state.

        Used when quota period resets (detected via reset_timestamp).
        """
        self._requests_made = 0
        self._last_quota_info = None
        self._logger.debug("quota_tracker_reset")
