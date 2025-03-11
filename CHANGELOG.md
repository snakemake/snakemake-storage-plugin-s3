# Changelog

## [0.3.0](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.13...v0.3.0) (2025-03-11)


### Features

* allow specification of location (e.g. AWS region)  ([#38](https://github.com/snakemake/snakemake-storage-plugin-s3/issues/38)) ([c78fa78](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/c78fa7815bfe1fa739626773cf6aa7ba3733f420))


### Bug Fixes

* limit inventory by prefix ([#43](https://github.com/snakemake/snakemake-storage-plugin-s3/issues/43)) ([f9331e8](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/f9331e811c4f9bc7edda312b223d5eca0e74808c))

## [0.2.13](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.12...v0.2.13) (2025-03-06)


### Bug Fixes

* `InsecureRequestWarning` from `urllib3` ([#36](https://github.com/snakemake/snakemake-storage-plugin-s3/issues/36)) ([69bc140](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/69bc1405bf9fd65ec158a46c5c994188e22712ff))
* prevent credential leakage ([#40](https://github.com/snakemake/snakemake-storage-plugin-s3/issues/40)) ([948475c](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/948475c276d4a1c6050f0157bc05e4ba65980edd))

## [0.2.12](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.11...v0.2.12) (2024-08-14)


### Bug Fixes

* allow boto3 to automatically refresh credentials ([#33](https://github.com/snakemake/snakemake-storage-plugin-s3/issues/33)) ([fc92231](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/fc922318d0000dfba7584f97f5ee2afbba072f06))
* fix retrieval of nested directories ([#27](https://github.com/snakemake/snakemake-storage-plugin-s3/issues/27)) ([42e55c3](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/42e55c35841c45bf1018d50dfba6ff3340dd774a))

## [0.2.11](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.10...v0.2.11) (2024-04-17)


### Bug Fixes

* update to at least 3.2.2 of storage interface ([a0bb3a5](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/a0bb3a5faadef23ac030cd01505327c8fc7cc897))
* fix errors when retrieving directories

## [0.2.10](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.9...v0.2.10) (2024-02-15)


### Bug Fixes

* pin urrllib to avoid boto bug ([#19](https://github.com/snakemake/snakemake-storage-plugin-s3/issues/19)) ([ab680d9](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/ab680d9a745aaf018d98b2eed38246e39e0a646d))

## [0.2.9](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.8...v0.2.9) (2024-02-07)


### Bug Fixes

* adapt to newer botocore ([#17](https://github.com/snakemake/snakemake-storage-plugin-s3/issues/17)) ([77d789a](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/77d789a2f642322896e2abe68307de4ce3c732f9))

## [0.2.8](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.7...v0.2.8) (2023-12-08)


### Documentation

* update metadata ([d3528c3](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/d3528c3d981b04a95ae5bf3a52c3811c196d91df))

## [0.2.7](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.6...v0.2.7) (2023-12-05)


### Bug Fixes

* adapt to interface change ([490493d](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/490493dab38bc3900cc19f78b4a2d07d72666155))

## [0.2.6](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.5...v0.2.6) (2023-11-23)


### Bug Fixes

* inventory calculation ([0915a5d](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/0915a5d18caf3413cff1891dddd32dff674b2f81))
* remove superfluous method ([10ac28b](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/10ac28ba7b57ab565a278c2df00e4b9d8a9a002a))

## [0.2.5](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.4...v0.2.5) (2023-11-15)


### Bug Fixes

* adapt to changes in interface ([2ab1c31](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/2ab1c313107523e6778e61617c8864f9074ed0fc))


### Performance Improvements

* implemented inventory functionality for dramatically reducing the S3 requests ([3a06bb0](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/3a06bb0dc9a890a8734c7cff5989c138a2a657fc))

## [0.2.4](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.3...v0.2.4) (2023-10-25)


### Bug Fixes

* specify required settings ([1b6cab1](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/1b6cab11950c5baae4c5930fe537ccc4215e7e19))

## [0.2.3](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.2...v0.2.3) (2023-10-24)


### Bug Fixes

* fix release process ([9b0f046](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/9b0f046312cdb7caa09df89fd5e83eee77388f9d))

## [0.2.2](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.1...v0.2.2) (2023-10-24)


### Bug Fixes

* update dependencies ([0e71519](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/0e71519ac2722d900edb29d48c1c1de30fd6f0ec))
* update dependencies ([387065f](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/387065f0ae5b5142b5d84746d7900a15ada6344d))

## [0.2.1](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.2.0...v0.2.1) (2023-10-13)


### Bug Fixes

* add homepage to metadata ([825c969](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/825c9693909097c590b8fbc6bf7ffb3b94d0ef4f))

## [0.2.0](https://github.com/snakemake/snakemake-storage-plugin-s3/compare/v0.1.0...v0.2.0) (2023-10-11)


### Features

* add example query ([03501ea](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/03501eac385ffb8238e8f5a5265f2e7c1e44c1f1))


### Bug Fixes

* delete bucket if empty after deleting object ([9cfcf33](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/9cfcf3384fcdf5a5ff8f08eeb111b9256885f460))
* fix bug when checking existence of non-existing items ([383face](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/383faceb5c294de6ce2988008a70e31e7156e3dd))
* update interface dependency ([968bd1b](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/968bd1b65b9c7a6b522eecf92925ad3fc543fb50))

## 0.1.0 (2023-09-27)


### Miscellaneous Chores

* release 0.1.0 ([a701958](https://github.com/snakemake/snakemake-storage-plugin-s3/commit/a701958e05e46fb251299806c74d6a3ed52e7c93))
