# Benchmark protocol and results

**Status: protocol only. No benchmark has been run; no measured values exist.** Do not interpret estimates in [DEPLOYMENT](DEPLOYMENT.md) as observed performance.

## Reproducible workload

Generate a synthetic Windows NTFS tree of **100 GB across 500,000 files**, seeded deterministically with recorded distribution of file sizes, depth, Unicode/long paths and modifications. Exclude real user data. Capture a baseline Full, then an Incremental with a known changed/deleted/new-file set, a Differential against the same Full, a sample restore and integrity scrub. Record VSS enabled/disabled only as separate named configurations; never compare live copy and VSS copy without labeling. Include 1/10/100 concurrent-host scenarios as infrastructure permits, with scripted bandwidth limits and disconnects.

Pin workload seed, target Windows build, worker OS/CPU/RAM/disk, network RTT/throughput, source/repository storage class, SMB dialect/signing/encryption, WinRM/TLS, chunk/compression/crypto versions, dedup configuration, DB/MinIO settings and CLI/app commit. Run warm-up and at least three measured repetitions; report median and spread. Record wall time, read/write throughput, files/s, peak scratch/storage, CPU, memory, dedup ratio, chunk count, queue delay, restore speed and hash-validation result.

## Regression gate

Establish a reviewed baseline from actual comparable runs, then fail CI if median throughput falls by more than 20% under the same workload/hardware class. Use a separate perf runner or controlled environment; do not gate on noisy shared CI hardware without variance control. An absent baseline is **blocked**, not a pass. Keep raw reports linked from results.

## Result log

| Date | Commit | Environment/workload seed | Full | Incremental | Differential | Restore | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Not run | — | — | — | — | — | — | Pending implementation and test environment |

Capacity sizing for 100, 1,000 and 10,000 hosts must be calculated from real full-size, daily change rate, retention and observed compression/dedup with scratch headroom; until then use workload-specific formulae only, not fabricated numeric sizing.
