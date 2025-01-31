from typing import List, Optional, Type, Mapping
import uuid
from snakemake_interface_storage_plugins.tests import TestStorageBase
from snakemake_interface_storage_plugins.storage_provider import StorageProviderBase
from snakemake_interface_storage_plugins.settings import StorageProviderSettingsBase
from snakemake_interface_executor_plugins.settings import ExecutorSettingsBase
from snakemake_interface_executor_plugins.registry import ExecutorPluginRegistry
from snakemake.executors import local as local_executor
from snakemake_storage_plugin_s3 import StorageProvider, StorageProviderSettings
from snakemake.common.tests import TestWorkflowsBase
import snakemake.common.tests
import snakemake.settings.types
from snakemake_interface_common.plugin_registry.plugin import TaggedSettings

from snakemake_interface_common.utils import lazy_property


class TestStorageNoSettings(TestStorageBase):
    __test__ = True
    retrieve_only = False
    files_only = False

    def get_query(self, tmp_path) -> str:
        return "s3://snakemake-test-bucket/testdir1/testdir2/test-file.txt"

    def get_query_not_existing(self, tmp_path) -> str:
        bucket = uuid.uuid4().hex
        key = uuid.uuid4().hex
        return f"s3://{bucket}/{key}"

    def get_storage_provider_cls(self) -> Type[StorageProviderBase]:
        # Return the StorageProvider class of this plugin
        return StorageProvider

    def get_storage_provider_settings(self) -> Optional[StorageProviderSettingsBase]:
        # instantiate StorageProviderSettings of this plugin as appropriate
        return StorageProviderSettings(
            endpoint_url="http://127.0.0.1:9000",
            access_key="minio",
            secret_key="minio123",
        )

    def get_example_args(self) -> List[str]:
        return []


registry = ExecutorPluginRegistry()
registry.register_plugin("local", local_executor)


class TestWorkflowsMinioLocalStorageBase(TestWorkflowsBase):
    def get_default_storage_provider(self) -> Optional[str]:
        return "s3"

    def get_default_storage_prefix(self) -> Optional[str]:
        return f"s3://{self.bucket}"

    def get_default_storage_provider_settings(
        self,
    ) -> Optional[Mapping[str, TaggedSettings]]:
        from snakemake_storage_plugin_s3 import StorageProviderSettings

        self._storage_provider_settings = StorageProviderSettings(
            endpoint_url=self.endpoint_url,
            access_key=self.access_key,
            secret_key=self.secret_key,
        )

        tagged_settings = TaggedSettings()
        tagged_settings.register_settings(self._storage_provider_settings)
        return {"s3": tagged_settings}

    def cleanup_test(self):
        import boto3

        # clean up using boto3
        s3c = boto3.resource(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        try:
            s3c.Bucket(self.bucket).delete()
        except Exception:
            pass

    @lazy_property
    def bucket(self):
        return f"snakemake-{uuid.uuid4().hex}"

    @property
    def endpoint_url(self):
        return "http://127.0.0.1:9000"

    @property
    def access_key(self):
        return "minio"

    @property
    def secret_key(self):
        return "minio123"


class TestWorkflows(TestWorkflowsMinioLocalStorageBase):
    __test__ = True

    def get_executor(self) -> str:
        return "local"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return None

    def get_assume_shared_fs(self) -> bool:
        return True

    def get_remote_execution_settings(
        self,
    ) -> snakemake.settings.types.RemoteExecutionSettings:
        return snakemake.settings.types.RemoteExecutionSettings()
