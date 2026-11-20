"""Real Snakemake workflows retain producer times despite a future S3 clock."""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import asyncio
import os

from botocore.client import BaseClient
from moto import mock_aws
import pytest

import snakemake_storage_plugin_s3 as plugin


@pytest.mark.parametrize(
    "preserve,directory", [(False, False), (True, False), (True, True)]
)
def test_fast_storage_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture,
    caplog: pytest.LogCaptureFixture,
    preserve: bool,
    directory: bool,
) -> None:
    import boto3
    from snakemake.cli import main
    import snakemake.io as io

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    producer = "bundle" if directory else "hello.txt"
    output = "directory('bundle')" if directory else "'hello.txt'"
    command = (
        "mkdir -p {output}; printf hello > {output}/file; "
        "touch -t 202001010000 {output}/file"
        if directory
        else "printf hello > {output}"
    )
    source = "{input}/file" if directory else "{input}"
    (tmp_path / "Snakefile").write_text(
        "rule all:\n    input: 'world.txt'\n"
        f'rule hello:\n    output: {output}\n    shell: "{command}"\n'
        f"rule world:\n    input: '{producer}'\n    output: 'world.txt'\n"
        f'    shell: "cat {source} > {{output}}; printf world >> {{output}}"\n'
    )
    original_touch = io.lutime

    def lutime(path, times):
        if times is None:
            times = (1700000000.0, 1700000000.0)
        original_touch(path, times)

    monkeypatch.setattr(io, "lutime", lutime)
    original = BaseClient._make_api_call

    def call(self, operation, parameters):
        result = original(self, operation, parameters)
        if "LastModified" in result:
            result["LastModified"] = datetime(2030, 1, 1, tzinfo=timezone.utc)
        for entry in result.get("Contents", []):
            entry["LastModified"] = datetime(2030, 1, 1, tzinfo=timezone.utc)
        return result

    monkeypatch.setattr(BaseClient, "_make_api_call", call)
    if not preserve:
        # Restore the old LastModified semantics without changing the engine's checker.
        monkeypatch.setattr(
            plugin,
            "effective_mtime_ns",
            lambda metadata, modified: int(modified.timestamp()) * 1000000000,
        )

    with mock_aws():
        client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        client.create_bucket(Bucket="test-bucket")
        arguments = [
            "--cores",
            "1",
            "--executor",
            "local",
            "--default-storage-provider",
            "s3",
            "--default-storage-prefix",
            "s3://test-bucket/results",
            "--storage-s3-access-key",
            "testing",
            "--storage-s3-secret-key",
            "testing",
            "--local-storage-prefix",
            str(tmp_path / "storage"),
            "--keep-storage-local-copies",
            "--verbose",
        ]
        with pytest.raises(SystemExit) as status:
            main(arguments)
        assert status.value.code == (0 if preserve else 1)
        captured = capfd.readouterr()
        if not preserve:
            assert (
                "older modification time" in captured.out + captured.err + caplog.text
            )
            return
        assert (
            client.get_object(Bucket="test-bucket", Key="results/world.txt")[
                "Body"
            ].read()
            == b"helloworld"
        )
        key = (
            "results/bundle/.snakemake_timestamp" if directory else "results/hello.txt"
        )
        assert (
            client.head_object(Bucket="test-bucket", Key=key)["Metadata"]["mtime"]
            == "1700000000"
        )
        # Force the consumer in a fresh workspace to retrieve its remote input.
        second = tmp_path / "second"
        second.mkdir()
        (second / "Snakefile").write_text((tmp_path / "Snakefile").read_text())
        monkeypatch.chdir(second)
        arguments[arguments.index("--local-storage-prefix") + 1] = str(
            second / "storage"
        )
        with pytest.raises(SystemExit) as status:
            main(arguments + ["--forcerun", "world"])
        assert status.value.code == 0
        input_path = second / "storage/s3/test-bucket/results" / producer
        marker = input_path / ".snakemake_timestamp" if directory else input_path
        assert marker.stat().st_mtime_ns == 1700000000000000000
        assert (
            client.get_object(Bucket="test-bucket", Key="results/world.txt")[
                "Body"
            ].read()
            == b"helloworld"
        )


def test_genuine_stale_output_is_still_rejected(tmp_path: Path) -> None:
    import snakemake.api  # noqa: F401
    from snakemake.dag import DAG
    from snakemake.io import IOFile
    from snakemake_interface_common.exceptions import WorkflowError

    source, output = tmp_path / "input", tmp_path / "output"
    source.write_bytes(b"input")
    output.write_bytes(b"old output")
    os.utime(source, (100.0, 100.0))
    os.utime(output, (99.0, 99.0))
    rule = SimpleNamespace(
        workflow=SimpleNamespace(iocache=SimpleNamespace(active=False)),
        pathvars=SimpleNamespace(apply=lambda path: path),
    )
    job = SimpleNamespace(input=[IOFile(str(source), rule=rule)], rule=None)
    with pytest.raises(WorkflowError, match="older modification time"):
        asyncio.run(DAG.check_output_mtime(None, job, [IOFile(str(output), rule=rule)]))
