from dataclasses import dataclass, field
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

import boto3
import botocore.credentials

from snakemake_interface_common.exceptions import WorkflowError
from snakemake_interface_storage_plugins.settings import StorageProviderSettingsBase
from snakemake_interface_storage_plugins.storage_provider import (
    StorageProviderBase,
    StorageQueryValidationResult,
)
from snakemake_interface_storage_plugins.storage_object import (
    StorageObjectRead,
    StorageObjectWrite,
    StorageObjectGlob,
    retry_decorator,
)
from snakemake_interface_storage_plugins.io import (
    IOCacheStorageInterface,
    get_constant_prefix,
)


# Optional:
# Define settings for your storage plugin (e.g. host url, credentials).
# They will occur in the Snakemake CLI as --storage-<storage-plugin-name>-<param-name>
# Make sure that all defined fields are 'Optional' and specify a default value
# of None or anything else that makes sense in your case.
# Note that we allow storage plugin settings to be tagged by the user. That means,
# that each of them can be specified multiple times (an implicit nargs=+), and
# the user can add a tag in front of each value (e.g. tagname1:value1 tagname2:value2).
# This way, a storage plugin can be used multiple times within a workflow with different
# settings.
@dataclass
class StorageProviderSettings(StorageProviderSettingsBase):
    endpoint_url: Optional[str] = field(
        default=None,
        metadata={
            "help": "S3 endpoint URL (if omitted, AWS S3 is used)",
            # Optionally request that setting is also available for specification
            # via an environment variable. The variable will be named automatically as
            # SNAKEMAKE_<storage-plugin-name>_<param-name>, all upper case.
            # This mechanism should only be used for passwords, usernames, and other
            # credentials.
            # For other items, we rather recommend to let people use a profile
            # for setting defaults
            # (https://snakemake.readthedocs.io/en/stable/executing/cli.html#profiles).
            "env_var": False,
            # Optionally specify that setting is required when the executor is in use.
            "required": False,
        },
    )
    access_key: Optional[str] = field(
        default=None,
        metadata={
            "help": "S3 access key (if omitted, credentials are taken from .aws/credentials as e.g. created by aws configure)",
            "env_var": True,
            "required": False,
        },
    )
    secret_key: Optional[str] = field(
        default=None,
        metadata={
            "help": "S3 secret key (if omitted, credentials are taken from .aws/credentials as e.g. created by aws configure)",
            "env_var": True,
            "required": False,
        },
    )
    token: Optional[str] = field(
        default=None,
        metadata={
            "help": "S3 token (usually not required)",
            "env_var": True,
            "required": False,
        },
    )
    signature_version: Optional[str] = field(
        default=None,
        metadata={
            "help": "S3 signature version",
            "env_var": False,
            "required": False,
        },
    )
    retries: int = field(
        default=5,
        metadata={
            "help": "S3 API retries",
            "env_var": False,
            "required": False,
        },
    )

    def __post_init__(self):
        session = boto3.Session()
        credentials = session.get_credentials()

        if credentials:
            if self.access_key is None:
                self.access_key = credentials.access_key
            if self.secret_key is None:
                self.secret_key = credentials.secret_key
            if self.token is None:
                self.token = credentials.token

        if self.access_key is None:
            raise WorkflowError(
                "Invalid settings for s3 storage: no access key provided"
            )
        if self.secret_key is None:
            raise WorkflowError(
                "Invalid settings for s3 storage: no secret key provided"
            )


# Required:
# Implementation of your storage provider
# This class can be empty as the one below.
# You can however use it to store global information or maintain e.g. a connection
# pool.
class StorageProvider(StorageProviderBase):
    # For compatibility with future changes, you should not overwrite the __init__
    # method. Instead, use __post_init__ to set additional attributes and initialize
    # futher stuff.

    def __post_init__(self):
        self.s3c = boto3.resource(
            "s3",
            endpoint_url=self.settings.endpoint_url,
            aws_access_key_id=self.settings.access_key,
            aws_secret_access_key=self.settings.secret_key,
            aws_session_token=self.settings.token,
            config=boto3.session.Config(
                signature_version=self.settings.signature_version,
                retries={
                    "max_attempts": self.settings.retries,
                    "mode": "standard",
                },
            ),
            verify=False,  # TODO required?
        )

    @classmethod
    def is_valid_query(cls, query: str) -> StorageQueryValidationResult:
        """Return whether the given query is valid for this storage provider."""
        # Ensure that also queries containing wildcards (e.g. {sample}) are accepted
        # and considered valid. The wildcards will be resolved before the storage
        # object is actually used.
        try:
            parsed = urlparse(query)
        except Exception as e:
            return StorageQueryValidationResult(
                query=query,
                valid=False,
                reason=f"cannot be parsed as URL ({e})",
            )
        if parsed.scheme != "s3":
            return StorageQueryValidationResult(
                query=query,
                valid=False,
                reason="must start with s3 (s3://...)",
            )
        return StorageQueryValidationResult(
            query=query,
            valid=True,
        )

    def list_objects(self, query: Any) -> Iterable[str]:
        """Return an iterator over all objects in the storage that match the query.

        This is optional and can raise a NotImplementedError() instead.
        """
        parsed = urlparse(query)
        bucket_name = parsed.netloc
        b = self.s3.Bucket(bucket_name)
        return [o.key for o in b.objects.iterator()]


# Required:
# Implementation of storage object. If read-only storage (e.g. see
# snakemake-storage-http for comparison), inherit from StorageObjectRead instead.
class StorageObject(StorageObjectRead, StorageObjectWrite, StorageObjectGlob):
    # For compatibility with future changes, you should not overwrite the __init__
    # method. Instead, use __post_init__ to set additional attributes and initialize
    # futher stuff.

    def __post_init__(self):
        # This is optional and can be removed if not needed.
        # Alternatively, you can e.g. prepare a connection to your storage backend here.
        # and set additional attributes.
        if self.is_valid_query():
            parsed = urlparse(self.query)
            self.bucket = parsed.netloc
            self.key = parsed.path.lstrip("/")
            self._local_suffix = f"{self.bucket}/{self.key}"
        self._is_dir = None

    def s3obj(self, subkey: Optional[str] = ""):
        if subkey:
            subkey = f"/{subkey}"
        return self.provider.s3c.Object(self.bucket, f"{self.key}{subkey}")

    def s3bucket(self):
        return self.provider.s3c.Bucket(self.bucket)

    async def inventory(self, cache: IOCacheStorageInterface):
        """From this file, try to find as much existence and modification date
        information as possible. Only retrieve that information that comes for free
        given the current object.
        """
        # This is optional and can be left as is

        # If this is implemented in a storage object, results have to be stored in
        # the given IOCache object.
        pass

    def get_inventory_parent(self) -> Optional[str]:
        """Return the parent directory of this object."""
        # this is optional and can be left as is
        return None

    def local_suffix(self) -> str:
        return self._local_suffix

    def close(self):
        # Close any open connections, unmount stuff, etc.
        pass

    # Fallible methods should implement some retry logic.
    # Here we simply rely on botos retry logic.
    def exists(self) -> bool:
        # return True if the object exists
        try:
            self.s3obj().load()
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                if self.is_dir():
                    return True
                return False
            else:
                raise e
        return True

    def mtime(self) -> float:
        # return the modification time
        if self.is_dir():
            return max(item.last_modified.timestamp() for item in self.get_subkeys())
        else:
            return self.s3obj().last_modified.timestamp()

    def size(self) -> int:
        # return the size in bytes
        if self.is_dir():
            return 0
        else:
            return self.s3obj().content_length

    def retrieve_object(self):
        # Ensure that the object is accessible locally under self.local_path()
        if self.is_dir():
            self.local_path().mkdir(parents=True, exist_ok=True)
            for item in self.get_subkeys():
                if item.key != self.s3obj().key:
                    item.download_file(self.local_path() / item.key)
        else:
            self.s3obj().download_file(self.local_path())

    def is_dir(self):
        if self._is_dir is None:
            self._is_dir = any(self.get_subkeys())
        return self._is_dir

    def get_subkeys(self):
        prefix = self.s3obj().key + "/"
        return (
            item
            for item in self.s3bucket().objects.filter(Prefix=prefix)
            if item.key != prefix
        )

    # The following to methods are only required if the class inherits from
    # StorageObjectReadWrite.

    def store_object(self):
        # Ensure that the object is stored at the location specified by
        # self.local_path().
        if not self.bucket_exists(self.bucket):
            self.provider.s3c.create_bucket(Bucket=self.bucket)

        if self.local_path().is_dir():
            self._is_dir = True
            for item in self.local_path().rglob("*"):
                if item.is_file():
                    self.s3obj(subkey=item.relative_to(self.local_path())).upload_file(
                        item
                    )
        else:
            self.s3obj().upload_file(self.local_path())

    def remove(self):
        # Remove the object from the storage.
        if self.is_dir():
            for item in self.get_subkeys():
                item.delete()
        else:
            self.s3obj().delete()

    @retry_decorator
    def list_candidate_matches(self) -> Iterable[str]:
        """Return a list of candidate matches in the storage for the query."""
        # This is used by glob_wildcards() to find matches for wildcards in the query.
        # The method has to return concretized queries without any remaining wildcards.
        prefix = get_constant_prefix(self.query)
        if prefix.startswith(self.bucket):
            prefix = prefix[len(self.bucket) :]
            return (item.key for item in self.s3bucket().objects.filter(Prefix=prefix))
        else:
            raise WorkflowError(
                "S3 storage object {self.query} cannot be used to list matching "
                "objects because bucket name contains a wildcard, which is not "
                "supported."
            )

    def bucket_exists(self, bucket_name):
        try:
            self.provider.s3c.meta.client.head_bucket(Bucket=bucket_name)
            return True
        except Exception:
            return False