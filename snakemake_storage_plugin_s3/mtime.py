"""Preserve filesystem modification times in S3 user metadata."""

from collections.abc import Mapping
from datetime import datetime, timezone
import re


_SECONDS = 1_000_000_000
_MIN_NS = -(1 << 63)
_MAX_NS = (1 << 63) - 1
_FIXED_POINT = re.compile(r"([+-]?)([0-9]+)(?:\.([0-9]+))?", re.ASCII)


def format_mtime_ns(mtime_ns: int) -> str:
    """Encode nanoseconds as fixed-point Unix seconds compatible with rclone."""
    seconds, fraction = divmod(abs(mtime_ns), _SECONDS)
    value = f"{seconds}.{fraction:09d}".rstrip("0").rstrip(".")
    return ("-" if mtime_ns < 0 else "") + value


def parse_mtime_ns(value: str | None) -> int | None:
    """Read fixed-point seconds, returning None for unusable metadata."""
    if value is None or len(value) > 2048:
        return None
    match = _FIXED_POINT.fullmatch(value)
    if match is None:
        return None
    sign, whole, fraction = match.groups()
    whole = whole.lstrip("0") or "0"
    if len(whole) > 10:
        return None
    nanoseconds = int(whole) * _SECONDS + int(((fraction or "") + "000000000")[:9])
    if sign == "-":
        nanoseconds = -nanoseconds
    return nanoseconds if _MIN_NS <= nanoseconds <= _MAX_NS else None


def effective_mtime_ns(metadata: Mapping[str, str], last_modified: datetime) -> int:
    """Prefer preserved filesystem time, falling back to the service timestamp."""
    preserved = parse_mtime_ns(metadata.get("mtime"))
    if preserved is not None:
        return preserved
    delta = last_modified - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * _SECONDS + delta.microseconds * 1000
