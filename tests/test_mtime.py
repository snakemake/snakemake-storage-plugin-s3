"""Logical mtimes must round-trip without binary floating-point truncation."""

from datetime import datetime, timezone

import pytest

from snakemake_storage_plugin_s3 import mtime


@pytest.mark.parametrize(
    "nanoseconds,encoded",
    [
        (0, "0"),
        (1, "0.000000001"),
        (-1, "-0.000000001"),
        (-1500000000, "-1.5"),
        (1700000000123456789, "1700000000.123456789"),
        (1000000000, "1"),
        (9223372036854775807, "9223372036.854775807"),
        (-9223372036854775808, "-9223372036.854775808"),
    ],
)
def test_exact_decimal_round_trip(nanoseconds: int, encoded: str) -> None:
    assert mtime.format_mtime_ns(nanoseconds) == encoded
    assert mtime.parse_mtime_ns(encoded) == nanoseconds


@pytest.mark.parametrize(
    "encoded,expected",
    [
        ("+1.25", 1250000000),
        ("1.1234567899", 1123456789),
        ("-1.0000000009", -1000000000),
    ],
)
def test_rclone_fixed_point_precision(encoded: str, expected: int) -> None:
    assert mtime.parse_mtime_ns(encoded) == expected


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "bad",
        "NaN",
        "Infinity",
        "-inf",
        "1e999999999",
        "1e-999999999",
        " 1",
        "1 ",
        "1.2.3",
        "9223372036.854775808",
        "-9223372036.854775809",
        "9" * 10000,
    ],
)
def test_invalid_metadata_uses_service_time(value: str | None) -> None:
    assert mtime.parse_mtime_ns(value) is None
    modified = datetime(2023, 11, 14, 22, 13, 20, 123456, tzinfo=timezone.utc)
    metadata = {} if value is None else {"mtime": value}
    assert mtime.effective_mtime_ns(metadata, modified) == 1700000000123456000


def test_metadata_takes_precedence_over_service_clock() -> None:
    modified = datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert (
        mtime.effective_mtime_ns({"mtime": "1700000000.123456789"}, modified)
        == 1700000000123456789
    )
