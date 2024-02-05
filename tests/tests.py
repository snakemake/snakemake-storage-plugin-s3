from typing import List, Optional, Type
import uuid
from snakemake_interface_storage_plugins.tests import TestStorageBase
from snakemake_interface_storage_plugins.storage_provider import StorageProviderBase
from snakemake_interface_storage_plugins.settings import StorageProviderSettingsBase
from snakemake_interface_executor_plugins.settings import ExecutorSettingsBase

from snakemake_storage_plugin_s3 import StorageProvider, StorageProviderSettings
import snakemake.common.tests
import snakemake.settings


class TestStorageNoSettings(TestStorageBase):
    __test__ = True
    retrieve_only = False

    def get_query(self, tmp_path) -> str:
        return "s3://snakemake-test-bucket/test-file.txt"

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
            endpoint_url="https://play.minio.io:9000",
            access_key="Q3AM3UQ867SPQQA43P2F",
            secret_key="zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG",
        )

    def get_example_args(self) -> List[str]:
        return []


class TestWorkflows(snakemake.common.tests.TestWorkflowsMinioPlayStorageBase):
    __test__ = True

    def get_executor(self) -> str:
        return "local"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        from snakemake.executors.local import ExecutorSettings
        return ExecutorSettings()

    def get_assume_shared_fs(self) -> bool:
        return True

    def get_remote_execution_settings(
        self,
    ) -> snakemake.settings.RemoteExecutionSettings:
        return snakemake.settings.RemoteExecutionSettings()
