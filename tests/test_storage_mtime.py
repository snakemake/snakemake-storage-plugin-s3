"""Exercise preserved mtimes through real boto transfers and metadata lookups."""

import asyncio
from pathlib import Path
import os

import logging
import shutil
from types import SimpleNamespace

from botocore.exceptions import ClientError
from snakemake_interface_common.exceptions import WorkflowError
from moto import mock_aws
import pytest

from snakemake_storage_plugin_s3 import StorageProvider, StorageProviderSettings


@pytest.fixture
def provider(tmp_path: Path) -> StorageProvider:
    with mock_aws():
        result = StorageProvider(
            local_prefix=tmp_path,
            logger=logging.getLogger("test"),
            settings=StorageProviderSettings(
                access_key="testing", secret_key="testing"
            ),
            keep_local=True,
            is_default=True,
        )
        result.s3c.create_bucket(Bucket="test-bucket")
        yield result


def test_upload_preserves_exact_filesystem_mtime(provider: StorageProvider) -> None:
    obj = provider.object("s3://test-bucket/file")
    obj.local_path().parent.mkdir(parents=True, exist_ok=True)
    obj.local_path().write_bytes(b"hello")
    os.utime(obj.local_path(), ns=(1700000000123456789, 1700000000123456789))
    asyncio.run(obj.managed_store())
    remote = provider.s3c.Object("test-bucket", "file")
    assert remote.metadata["mtime"] == "1700000000.123456789"
    assert remote.get()["Body"].read() == b"hello"
    assert obj.mtime() == 1700000000.123456789


@pytest.mark.parametrize(
    "value", [None, "bad", "NaN", "1e999999", "1700000000.123456789"]
)
def test_lookup_and_download_use_same_effective_time(
    provider: StorageProvider, value: str | None
) -> None:
    metadata = {"other": "retained"}
    if value is not None:
        metadata["mtime"] = value
    remote = provider.s3c.Object("test-bucket", "file")
    remote.put(Body=b"hello", Metadata=metadata)
    service_ns = int(remote.last_modified.timestamp()) * 1000000000
    expected_ns = 1700000000123456789 if value == "1700000000.123456789" else service_ns
    obj = provider.object("s3://test-bucket/file")
    assert obj.mtime() == expected_ns / 1000000000
    asyncio.run(obj.managed_retrieve())
    assert obj.local_path().stat().st_mtime_ns == expected_ns
    assert obj.local_path().read_bytes() == b"hello"
    assert remote.metadata == metadata


def test_restoration_preserves_downloaded_atime(
    provider: StorageProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider.s3c.Object("test-bucket", "file").put(
        Body=b"hello", Metadata={"mtime": "1.25"}
    )
    obj = provider.object("s3://test-bucket/file")
    original = os.utime
    calls = []

    def utime(path, *args, **kwargs):
        before = Path(path).stat()
        calls.append((before.st_atime_ns, kwargs.get("ns")))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "utime", utime)
    asyncio.run(obj.managed_retrieve())
    assert calls and calls[-1][1] == (calls[-1][0], 1250000000)
    assert obj.local_path().stat().st_mtime_ns == 1250000000


def test_directory_round_trip_and_aggregate(provider: StorageProvider) -> None:
    obj = provider.object("s3://test-bucket/dir")
    times = {
        "a": 1700000000123456789,
        "nested/b space+#": 1700000001000000001,
        ".snakemake_timestamp": 1700000002000000000,
    }
    encoded = {
        "a": "1700000000.123456789",
        "nested/b space+#": "1700000001.000000001",
        ".snakemake_timestamp": "1700000002",
    }
    for name, ns in times.items():
        path = obj.local_path() / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
        os.utime(path, ns=(ns, ns))
    asyncio.run(obj.managed_store())
    for name in times:
        assert (
            provider.s3c.Object("test-bucket", f"dir/{name}").metadata["mtime"]
            == encoded[name]
        )
    assert obj.mtime() == 1700000002.0
    shutil.rmtree(obj.local_path())
    asyncio.run(obj.managed_retrieve())
    for name, ns in times.items():
        path = obj.local_path() / name
        assert path.stat().st_mtime_ns == ns
        assert path.read_bytes() == name.encode()


@pytest.mark.parametrize("failure", ["transfer", "utime"])
def test_download_errors_propagate_and_clean_up(
    provider: StorageProvider, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    remote = provider.s3c.Object("test-bucket", "file")
    remote.put(Body=b"hello", Metadata={"mtime": "1.25"})
    obj = provider.object("s3://test-bucket/file")
    if failure == "transfer":

        def fail(*args, **kwargs):
            raise OSError("download interrupted")

        monkeypatch.setattr(remote, "download_file", fail)
        monkeypatch.setattr(obj, "s3obj", lambda: remote)
    else:

        def fail(*args, **kwargs):
            raise PermissionError("timestamp denied")

        monkeypatch.setattr(os, "utime", fail)
    with pytest.raises(WorkflowError, match="Failed to retrieve"):
        asyncio.run(obj.managed_retrieve())
    assert not obj.local_path().exists()


def cache() -> SimpleNamespace:
    return SimpleNamespace(exists_in_storage={}, mtime={}, size={})


@pytest.mark.parametrize("prefix", ["dir/", ""])
def test_inventory_matches_direct_metadata_and_scans_each_prefix(
    provider: StorageProvider, monkeypatch: pytest.MonkeyPatch, prefix: str
) -> None:
    values = {
        prefix + "a": {"mtime": "1.25"},
        prefix + "nested/b space+": {"mtime": "2.5"},
        prefix + "legacy": {},
        prefix + "invalid": {"mtime": "bad"},
        "dir-archive/unrelated": {"mtime": "9"},
        "other/c": {"mtime": "3"},
    }
    for key, metadata in values.items():
        provider.s3c.Object("test-bucket", key).put(Body=b"hello", Metadata=metadata)
    calls = []
    client = provider.s3c.meta.client
    original = client._make_api_call

    def call(operation, params):
        calls.append((operation, params))
        return original(operation, params)

    monkeypatch.setattr(client, "_make_api_call", call)
    obj = provider.object(f"s3://test-bucket/{prefix}a")
    result = cache()
    asyncio.run(obj.inventory(result))
    assert result.mtime[obj.cache_key()].storage() == 1.25
    included = [key for key in values if key.startswith(prefix)]
    for key in included:
        child = provider.object(f"s3://test-bucket/{key}")
        assert result.mtime[child.cache_key()].storage() == child.mtime()
        assert result.size[child.cache_key()] == 5
        assert result.exists_in_storage[child.cache_key()] is True
    if prefix:
        other = provider.object("s3://test-bucket/other/c")
        assert other.cache_key() not in result.mtime
        asyncio.run(other.inventory(result))
        assert result.mtime[other.cache_key()].storage() == 3.0
        assert (
            provider.object("s3://test-bucket/dir-archive/unrelated").cache_key()
            not in result.mtime
        )
    assert result.exists_in_storage[obj.get_inventory_parent()] is True
    assert any(op == "HeadObject" for op, _ in calls)


def test_inventory_failure_does_not_publish_partial_results(
    provider: StorageProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ["a", "b"]:
        provider.s3c.Object("test-bucket", f"dir/{name}").put(
            Body=b"hello", Metadata={"mtime": "1"}
        )
    client = provider.s3c.meta.client
    original = client._make_api_call

    def call(operation, params):
        if operation == "HeadObject" and params["Key"] == "dir/b":
            raise ClientError(
                {"Error": {"Code": "500", "Message": "service failure"}}, operation
            )
        return original(operation, params)

    monkeypatch.setattr(client, "_make_api_call", call)
    result = cache()
    with pytest.raises(ClientError):
        asyncio.run(provider.object("s3://test-bucket/dir/a").inventory(result))
    assert result.mtime == result.size == result.exists_in_storage == {}


@pytest.mark.parametrize("failure", ["transfer", "utime"])
def test_directory_late_download_errors_clean_whole_tree(
    provider, monkeypatch, failure
):
    for key in ["dir/a", "dir/b"]:
        provider.s3c.Object("test-bucket", key).put(
            Body=b"hello", Metadata={"mtime": "1"}
        )
    obj = provider.object("s3://test-bucket/dir")
    if failure == "transfer":
        client = provider.s3c.meta.client
        original = client._make_api_call

        def call(operation, params):
            if operation == "GetObject" and params["Key"] == "dir/b":
                raise OSError("second member interrupted")
            return original(operation, params)

        monkeypatch.setattr(client, "_make_api_call", call)
    else:
        original_utime = os.utime

        def utime(path, *args, **kwargs):
            if Path(path).name == "b":
                raise PermissionError("second timestamp denied")
            return original_utime(path, *args, **kwargs)

        monkeypatch.setattr(os, "utime", utime)
    with pytest.raises(WorkflowError) as error:
        asyncio.run(obj.managed_retrieve())
    assert "second" in str(error.value)
    assert not obj.local_path().exists()
