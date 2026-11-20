# Snakemake storage plugin: s3

A Snakemake storage plugin for S3 API storage (AWS S3, MinIO, etc.).
For documentation and usage instructions, see the [Snakemake plugin catalog](https://snakemake.github.io/snakemake-plugin-catalog/plugins/storage/s3.html).

## Modification times

Uploads preserve each file's filesystem modification time in S3 user metadata
`mtime` (`X-Amz-Meta-Mtime`), using rclone-compatible decimal Unix seconds.
Downloads restore that timestamp, and metadata lookups and inventories report it
instead of the service's upload time. This prevents S3's clock from making a
retained local input newer than a fast downstream output on the same host.
Snakemake's stale-output validation remains enabled.

The metadata preserves nanosecond precision. Snakemake's timestamp API uses
floating-point seconds, so comparisons through that API have lower precision.
Directory timestamps are the maximum effective timestamp of their member files,
including an existing `.snakemake_timestamp` marker. After a directory download,
the local directory timestamp (or its existing Snakemake marker) is synchronized
to that aggregate so retained copies can detect later remote updates. A marker
older than another member therefore advances to the aggregate locally; ordinary
member files retain their individual times.

Objects without usable `mtime` metadata fall back to S3 `LastModified`. Metadata
must contain fixed-point decimal seconds within the signed 64-bit nanosecond
range (approximately 1677 through 2262); invalid, nonfinite and out-of-range
values use the same fallback. Extra fractional digits are truncated to
nanoseconds, as in rclone. Existing objects are not rewritten or backfilled.

S3 listings do not include user metadata, so inventory performs an additional
HEAD request per object not already fully cached. An unreadable unrelated sibling
is left uncached rather than requiring additional read permissions; errors for
the queried object still propagate. Downloads retain boto3's managed transfer support;
metadata reads and transfers are not atomic against concurrent replacements.

Preserving mtimes does not correct clock skew between producing hosts. As with
ordinary filesystem mtime comparisons, replacing content while retaining an
equal or older mtime may not trigger retrieval or recomputation.