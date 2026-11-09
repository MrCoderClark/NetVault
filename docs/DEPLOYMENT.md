# Deployment and observability design

**Status: planned topology; no images or Compose/Helm files exist.** Production serves the Next.js static export from FastAPI; browser and API share origin. The backend, scheduler and worker are separate processes. Python dependencies are uv locked; image builds pin checked versions and do not contain secret values or a build toolchain in the final stage.

## Local and on-prem Compose target

Services: API/static UI, one scheduler, scalable worker(s), PostgreSQL 15+, MinIO S3-compatible storage, Vault dev for local-only demonstration, optional Prometheus/Grafana/OTel collector. Production must replace Vault dev mode, inject protected keys via orchestration secret source and provide durable DB/repository volumes; never treat local demo credentials as production secrets. Each process starts with validated Pydantic settings; `.env.example` is names/default explanations only, no real secret. Planned settings groups: DB URL/SSL, secret provider/address/auth reference, repository backend/key refs, WinRM/SMB policy and timeouts, worker concurrency/deadlines, HTTP/CORS/session settings, OTLP endpoint, notification refs and scheduler timezone. An invalid/missing required setting lists errors and fails startup.

Separate migration job obtains advisory lock; API/worker readiness waits for expected schema version. `healthz` no dependency, `readyz` checks DB/queue/secret backend and schema, `startupz` initialization. Multi-stage image non-root UID, read-only-rootfs-friendly with scratch mount, dropped capabilities, HEALTHCHECK; define measured size budget in CI after first build, not an invented figure.

**Worker topology:** Windows workers can execute robocopy if they can reach a verified snapshot-share view. Linux containers cannot invoke robocopy; use a vetted SMB client for an accessible snapshot view or dispatch jobs to a Windows worker. Windows services and Linux workers need route to SMB/445 and WinRM/5986. The Windows worker requires a separately provisioned scratch directory with quota and cleanup; do not assume Compose Linux service can satisfy the Windows-robocopy acceptance path. [WINDOWS-SETUP](WINDOWS-SETUP.md) lists prerequisites.

## Kubernetes target

Helm: API and worker Deployments, singleton scheduler (DB leader fallback), migration Job, housekeeping CronJob, queue-depth-driven worker HPA, PodDisruptionBudget, network policies (DB, Vault, object storage, Windows hosts only), requests/limits, secret mounts, non-root/read-only root filesystem and dropped capabilities. Windows workers run on compatible Windows nodes or outside Linux cluster; do not schedule robocopy containers on Linux. Use dedicated scratch volume, probes and graceful termination budget. Postgres/MinIO/Vault production can be externally managed; configure TLS/mTLS, durable backups and restricted egress. Scale workers without changing at-least-once lease semantics.

## Telemetry and alerts

JSON logs and OTel spans carry correlation ID, tenant, job, host, credential **ID only**, attempt, phase and redacted error. No file content, secrets or optional sensitive filenames. OTLP spans: preflight, snapshot, scan, copy per source, verify, index, prune; include bytes/files/duration without uncontrolled path labels.

Prometheus HTTP RED and domain metrics: `backup_job_duration_seconds`, `backup_bytes_total`, `backup_files_total`, `backup_failures_total{reason}`, `dedup_ratio`, `repository_free_bytes`, `host_reachability`, `credential_failures_total`, `queue_depth`, `worker_in_flight`. Guard metric cardinality (no per-file labels, avoid raw host paths). Dashboards: fleet health, job outcomes/durations, repository growth, queue/worker load, credential health. Alerts: high backup failure rate, host without successful backup > 2× schedule interval, low repository capacity, credential nearing expiry, queue backlog and orphan snapshots. Graphs/alerts are design deliverables, not currently shipped.

## Capacity and migration

For each host, estimate `changed_bytes_per_day × retention_days / effective_dedup_ratio` plus initial Full, compression and metadata; add peak staging space and 30% headroom as an **illustrative planning assumption**, not measured fact. For 100/1,000/10,000 hosts run the same formula with measured per-host workload distributions, concurrency and DB index/queue volume; publish actual sizing only after [BENCHMARKS](BENCHMARKS.md). Self-backup must capture DB, repository manifests/key references and escrowed keys consistently; restore drill validates the full chain.
