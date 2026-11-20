"""Exercise inventory through the real engine cache, including directory aliases."""

import asyncio
from types import SimpleNamespace

import pytest
import snakemake.api  # noqa: F401
from snakemake.io import IOCache, IOFile, flag
from botocore.exceptions import ClientError

import test_storage_mtime


@pytest.fixture
def provider(tmp_path):
    yield from test_storage_mtime.provider.__wrapped__(tmp_path)


def engine_file(provider, query: str, cache=None):
    obj = provider.object(query)
    if cache is None:
        cache = IOCache(10)
    rule = SimpleNamespace(
        workflow=SimpleNamespace(iocache=cache),
        pathvars=SimpleNamespace(apply=lambda path: path),
    )
    return IOFile(flag(str(obj.local_path()), "storage_object", obj), rule=rule)


def test_empty_inventory_does_not_invent_parent(provider):
    shared = IOCache(10)
    child = engine_file(provider, "s3://test-bucket/missing/child", shared)
    asyncio.run(child.inventory())
    parent = engine_file(provider, "s3://test-bucket/missing", shared)
    assert not asyncio.run(parent.exists_in_storage())
    assert not parent.storage_object.exists()


@pytest.mark.parametrize("marker", [{"mtime": "1"}, {}])
def test_marker_does_not_override_directory_aggregate(provider, marker):
    provider.s3c.Object("test-bucket", "dir/").put(Body=b"", Metadata=marker)
    provider.s3c.Object("test-bucket", "dir/member").put(
        Body=b"hello", Metadata={"mtime": "2"}
    )
    provider.s3c.Object("test-bucket", "dir/.snakemake_timestamp").put(
        Body=b"", Metadata={"mtime": "3"}
    )
    shared = IOCache(10)
    root = engine_file(provider, "s3://test-bucket/sibling", shared)
    asyncio.run(root.inventory())
    directory = engine_file(provider, "s3://test-bucket/dir", shared)
    assert (
        asyncio.run(directory.mtime()).storage()
        == directory.storage_object.mtime()
        == 3.0
    )
    assert asyncio.run(directory.size()) == directory.storage_object.size() == 5
    assert (
        shared.exists_in_storage[
            provider.object("s3://test-bucket/dir/member").cache_key()
        ]
        is True
    )


def test_overlapping_prefixes_reuse_complete_metadata(provider, monkeypatch):
    for key in ["a/file", "a/b/file", "a/b/c/file"]:
        provider.s3c.Object("test-bucket", key).put(
            Body=key.encode(), Metadata={"mtime": "1"}
        )
    original = provider.s3c.meta.client._make_api_call
    heads = []

    def call(operation, params):
        if operation == "HeadObject":
            heads.append(params["Key"])
        return original(operation, params)

    monkeypatch.setattr(provider.s3c.meta.client, "_make_api_call", call)
    shared = IOCache(10)
    for key in ["a/b/c/file", "a/b/file", "a/file"]:
        asyncio.run(
            engine_file(provider, f"s3://test-bucket/{key}", shared).inventory()
        )
    assert sorted(heads) == ["a/b/c/file", "a/b/file", "a/file"]
    for key in heads:
        cache_key = provider.object(f"s3://test-bucket/{key}").cache_key()
        assert shared.exists_in_storage[cache_key] is True
        assert shared.size[cache_key] == len(key)
        assert shared.mtime[cache_key].storage() == 1.0


@pytest.mark.parametrize("wanted", ["public", "private"])
def test_unreadable_siblings_do_not_expand_input_permissions(
    provider, monkeypatch, wanted
):
    for key in ["public", "private"]:
        provider.s3c.Object("test-bucket", key).put(
            Body=b"hello", Metadata={"mtime": "1"}
        )
    original = provider.s3c.meta.client._make_api_call

    def call(operation, params):
        if operation == "HeadObject" and params["Key"] == "private":
            raise ClientError(
                {"Error": {"Code": "403", "Message": "denied"}}, operation
            )
        return original(operation, params)

    monkeypatch.setattr(provider.s3c.meta.client, "_make_api_call", call)
    file = engine_file(provider, f"s3://test-bucket/{wanted}")
    if wanted == "private":
        with pytest.raises(ClientError):
            asyncio.run(file.inventory())
    else:
        asyncio.run(file.inventory())
        assert asyncio.run(file.exists_in_storage())
        assert asyncio.run(file.mtime()).storage() == 1.0
        assert (
            provider.object("s3://test-bucket/private").cache_key()
            not in file.rule.workflow.iocache.mtime
        )


@pytest.mark.parametrize("marker", [False, True])
def test_retained_directory_refreshes_newer_members(provider, marker):
    remote = provider.s3c.Object("test-bucket", "dir/nested/member")
    remote.put(Body=b"old", Metadata={"mtime": "1700000000"})
    if marker:
        provider.s3c.Object("test-bucket", "dir/.snakemake_timestamp").put(
            Body=b"", Metadata={"mtime": "1699999999"}
        )
    obj = provider.object("s3://test-bucket/dir")
    asyncio.run(obj.managed_retrieve())
    first = engine_file(provider, "s3://test-bucket/dir")
    assert asyncio.run(first.mtime()).local() == 1700000000.0
    nested = engine_file(provider, "s3://test-bucket/dir/nested")
    assert asyncio.run(nested.mtime()).local() == 1700000000.0
    remote.put(Body=b"new", Metadata={"mtime": "1700000001"})
    updated = engine_file(provider, "s3://test-bucket/dir")
    asyncio.run(updated.retrieve_from_storage())
    assert (obj.local_path() / "nested/member").read_bytes() == b"new"
    assert (
        asyncio.run(engine_file(provider, "s3://test-bucket/dir").mtime()).local()
        == 1700000001.0
    )


@pytest.mark.parametrize("marker_time", [None, "1", "3"])
def test_directory_aggregate_is_max_not_marker_precedence(provider, marker_time):
    provider.s3c.Object("test-bucket", "dir/nested/member").put(
        Body=b"hello", Metadata={"mtime": "2"}
    )
    if marker_time:
        provider.s3c.Object("test-bucket", "dir/.snakemake_timestamp").put(
            Body=b"", Metadata={"mtime": marker_time}
        )
    assert provider.object("s3://test-bucket/dir").mtime() == (
        3.0 if marker_time == "3" else 2.0
    )
