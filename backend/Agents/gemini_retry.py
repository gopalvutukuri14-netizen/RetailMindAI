"""
Shared Gemini API call helper with bounded retry and quota handling.

Policy:
  Max 3 retries total.
  HTTP 429 RESOURCE_EXHAUSTED: respect retry_delay from the exception
    when present; otherwise exponential back-off starting at 5 s.
  Transient server errors (500, 503, 504): exponential back-off from 2 s.
  Non-retryable errors (400, 401, 403): raised immediately.
  Empty or unparseable response: non-retryable (retrying wastes quota).
"""

import re
import time
import logging
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

_MAX_RETRIES = 3
_QUOTA_BASE_DELAY = 5.0
_TRANSIENT_BASE_DELAY = 2.0


def _extract_retry_delay(exc: Exception) -> float | None:
    """Try to read a server-suggested retry delay from the exception."""
    try:
        delay = getattr(exc, "retry_delay", None)
        if delay is not None:
            return max(1.0, float(delay))
    except Exception:
        pass
    match = re.search(r"retry_delay\s*\{.*?seconds:\s*(\d+)", str(exc))
    if match:
        return max(1.0, float(match.group(1)))
    return None


def _is_quota_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "QUOTA" in text


def _is_retryable(exc: Exception) -> bool:
    if _is_quota_error(exc):
        return True
    text = str(exc)
    return any(code in text for code in ("500", "503", "504"))


def call_with_retry(fn: Callable[[], T], *, context: str = "") -> T:
    """
    Call fn() with bounded retry on quota and transient errors.

    Args:
        fn:      Zero-argument callable performing one Gemini API call.
        context: Short description used in log messages.

    Returns:
        Whatever fn() returns.

    Raises:
        The last exception if all retries are exhausted, or any
        non-retryable exception immediately.
    """
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as exc:
            if not _is_retryable(exc):
                raise

            last_exc = exc
            remaining = _MAX_RETRIES - attempt

            if remaining == 0:
                logger.error(
                    "[%s] Gemini call failed after %d attempts: %s",
                    context or "gemini",
                    _MAX_RETRIES + 1,
                    exc,
                )
                raise

            if _is_quota_error(exc):
                delay = _extract_retry_delay(exc) or (
                    _QUOTA_BASE_DELAY * (2 ** attempt)
                )
                logger.warning(
                    "[%s] Quota/rate-limit error (attempt %d/%d). Retrying in %.1f s.",
                    context or "gemini",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    delay,
                )
            else:
                delay = _TRANSIENT_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "[%s] Transient error (attempt %d/%d). Retrying in %.1f s: %s",
                    context or "gemini",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    delay,
                    exc,
                )

            time.sleep(delay)

    assert last_exc is not None
    raise last_exc
