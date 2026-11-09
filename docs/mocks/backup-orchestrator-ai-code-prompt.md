# Build Prompt: NetVault — Enterprise Windows Backup Orchestration Platform

> Paste everything below the line into your AI coding tool (Claude Code, Cursor, Codex, Devin, etc.).
> It is written as a single self-contained brief. If your tool supports a "spec file", save this as `SPEC.md` in the repo root and reference it in every session.

---

## 0. Your role and the outcome

You are a senior full-stack engineer and infrastructure architect. Build a **production-grade, multi-tenant enterprise web application** named **NetVault** that orchestrates **scheduled and on-demand backup jobs against remote Windows 10 / Windows 11 machines over the network**.

The app connects to target machines using **SMB** (for file transfer) and **WinRM** (for remote execution, pre/post scripts, service control, and VSS snapshot creation), using a **credential vault** that supports many distinct credential sets — including per-host, per-domain, and per-share credentials.

"Production-grade" is a hard requirement. This is not a demo. Every section below — auth, secrets, audit, retries, idempotency, observability, migrations, tests, CI, container builds, and runbooks — must be implemented, not stubbed with `TODO`.

Where this spec is silent on a detail, choose the boring, well-understood, industry-standard option and **write down your choice in `docs/DECISIONS.md`** with a one-paragraph rationale. Do not silently invent requirements that contradict this spec.

## 1. Non-negotiable constraints

1. **Primary language: Python 3.12+** for the backend and workers. Type-check clean under `mypy --strict` on all first-party code.
2. **Web UI** must be a real SPA build, served as static assets by the API in production. Accessibility target: WCAG 2.2 AA.
3. **No secrets in code, config files, environment dumps, or logs.** Ever. See §7.
4. **No agent installation on target machines.** All access is agentless via SMB + WinRM. (An optional agent is explicitly out of scope for v1 — leave an interface seam, implement nothing.)
5. **Every mutating action is audited** with actor, target, before/after, and correlation ID.
6. **Every network call to a target host is bounded** by connect timeout, read timeout, and an overall job deadline.
7. **The system must be resumable and idempotent.** A crashed worker must be able to resume or safely restart a backup without corrupting the repository or duplicating data.
8. **Never run as a domain admin by default.** Least privilege is the documented baseline.

## 2. Functional scope

### 2.1 Backup job types

Implement three first-class job types with a shared engine:

| Type | Definition | Implementation notes |
|---|---|---|
| **Full** | Complete copy of every selected source into a new backup set. | Establishes a new baseline. Records a manifest of every file (path, size, mtime, attributes, hash or hash-on-read policy). |
| **Incremental** | Only files changed since the **last backup of any type**. | Fastest, smallest. Each incremental depends on the chain root. Chain depth warning threshold (default 30) must be configurable. |
| **Differential** | Only files changed since the **last Full**. | Grows over time but needs only the last Full + the latest Differential to restore. |

**Hard requirements for all three:**

- Correctness must be anchored to a **stable change-detection method**, not naive mtime alone. Implement a pluggable detector with at least three strategies selectable per job:
  - `mtime_size` — fast, default for large trees.
  - `usn_journal` — Windows USN change journal read over WinRM where available (fall back automatically on failure, and log the fallback).
  - `hash_verify` — content hash comparison, available for jobs where integrity outweighs speed.
- **VSS snapshots are mandatory by default** for any source on an NTFS volume, so open/locked files (outlook `.pst`, `.vhd`, SQL data files, user hives) are captured consistently. Snapshot creation and deletion go over WinRM (`WMI`/`PowerShell`). The snapshot must be deleted in a `finally` block even on hard failure, and orphan-snapshot reaping must run on a schedule.
- **Robocopy over SMB** is the default copy mechanism where the source is reachable as a UNC path from the worker, because it gives you `/MIR`, `/XO`, `/XN`, restartable mode `/Z`, multithreading `/MT`, and reliable retry semantics. Use `rsync`-over-SMB only as an explicit opt-in alternative. The engine must be abstracted behind a `CopyStrategy` interface so a future strategy (e.g. a native SMB client for environments where `robocopy` is unavailable) can be dropped in.
- **Deduplication and compression** of stored data are required, using a **content-addressed chunk store**. Target: variable-length chunking (FastCDC or a documented alternative), BLAKE3 or SHA-256 chunk IDs, zstd compression, and per-backup manifests that reference chunk IDs. A configurable `dedup_enabled` flag must allow a plain "mirror" mode for users who do not want an opaque store.
- **Encryption at rest** for the repository is required (see §7.3), with the key hierarchy documented and recoverable, and with a `--verify` mode that proves a restore is possible without decrypting the whole store.
- **Retention / GFS policy** is per-job and per-policy-template: grandfather-father-son with configurable daily / weekly / monthly / yearly counts, plus a min-keep floor, plus a "never delete the last known-good full" invariant.
- **Verification** of every completed set: at minimum a manifest-vs-store integrity check, plus an optional sample-restore verification job that restores N random files to a scratch path and compares hashes.

### 2.2 Sources and selection

- Selection by **host → share → folder/file glob**, with include and exclude patterns, using a documented pattern language (document whether you implement glob-with-`**`, regex, or both).
- Per-source overrides for: VSS on/off, change-detection strategy, copy strategy, bandwidth throttling, retry policy, and credential reference.
- **Registry/acl/attribute fidelity**: preserve file attributes, timestamps, and (where the target supports it) ACLs. Document explicitly what is *not* preserved.
- **Pre-flight validation** on every job: resolve host, test WinRM connectivity, test SMB share access with the resolved credential, check free space on the repository, check that the snapshot can be created. Fail fast with an actionable error rather than at hour three of the copy.

### 2.3 Targets (destination)

The primary destination is the app's own **repository** (local disk, or a mounted network/S3-compatible object store behind a `StorageBackend` interface). Implement at least:
- `local_fs` (required)
- `s3_compatible` (required — MinIO/AWS S3/Wasabi; use the S3 API, not a provider SDK)
- `smb_share` (required — writes to a UNC destination, for customers who want their backups on a NAS)

## 3. Credential and connection layer

This is the most security-sensitive subsystem. Design it before writing application code.

### 3.1 Credential vault

- Credentials are **first-class entities**: `Credential { id, name, kind, username, domain, secret_ref, host_scope, share_scope, notes, tags, rotation_due_at, last_used_at }`.
- Secrets are **never stored in the application database in plaintext**. Store them in a pluggable `SecretBackend` with these implementations:
  - `vault_hashicorp` (preferred)
  - `aws_secrets_manager`
  - `azure_key_vault`
  - `encrypted_db` (envelope encryption with a KEK from a file/KMS, documented as the "small installer" fallback)
- Every secret read is audited (actor, credential ID, purpose, correlation ID) — **including reads by the scheduler itself**.
- **Credential resolution order** must be explicit and documented: job override → source override → host policy → credential group → global default. The resolution result (which credential won, and why) is logged at job start so operators can debug access failures without guessing.

### 3.2 Multiple credentials, in practice

Implement and support these real-world patterns:

- **Per-host credentials** — different local admin accounts on different machines.
- **Domain credentials** — a service account used across a domain, with `DOMAIN\user` vs `user@domain.tld` forms both supported and normalized.
- **Per-share credentials** — a share on a NAS reached with different credentials than the host it is mounted from.
- **Credential rotation** — change a secret in the vault; all jobs referencing it pick up the new value on next run with no restart. Support a grace window where both old and new credentials are valid during rollover.
- **Credential health checks** — a scheduled probe that logs into each host and reports: WinRM reachable, SMB share readable, Kerberos ticket valid (if applicable), password expiring soon, account locked/disabled. Surface as a dashboard and as a blocking pre-flight warning.
- **Lockout safety** — a global and per-host counter that halts authentication attempts after N consecutive failures for M minutes, so a bad credential in a schedule cannot lock out a service account across a fleet.

### 3.3 SMB specifics

- Use the **server message block protocol over TCP 445**. Do not implement SMB yourself; use a mature library or an OS mount, and document the choice.
- Support **NTLMv2** and **Kerberos**.
- Enforce a **minimum SMB dialect** (default: SMB 3.1.1 preferred, SMB 2.1 minimum) and **refuse to negotiate SMB1**. Log the negotiated dialect per connection.
- Support **SMB signing required** and **encryption required** enforcement for compliance customers, with a per-host policy override and a clear pre-flight failure when a host cannot meet the policy.
- Implement **reconnect with exponential backoff + jitter** on transient SMB errors, distinguishing retryable (`STATUS_NETWORK_NAME_DELETED`, timeouts, `STATUS_CONNECTION_DISCONNECTED`) from terminal (`STATUS_LOGON_FAILURE`, `STATUS_ACCESS_DENIED`, `STATUS_BAD_NETWORK_NAME`). Terminal errors fail the job immediately; retryable ones retry per policy.
- Handle **long paths** (>260 chars), **Unicode and non-UTF8 filenames**, and **case-collision** on case-sensitive destination filesystems.
- Support **DFS namespaces** and **IP-address-only targets where no DNS name exists**.

### 3.4 WinRM specifics

- Support both **HTTP/5985** and **HTTPS/5986**. Default to HTTPS with certificate validation; allow HTTP only behind an explicit, loudly documented per-host opt-in flag.
- Auth methods: **NTLM**, **Negotiate/Kerberos**, **Basic over HTTPS with the opt-in flag**, and **Certificate auth** as an option. Explicitly do **not** implement CredSSP in v1 (document why: double-hop delegation and unsafe credential handling), and say what operators should do instead.
- Commands run over WinRM are **PowerShell** by default. Implement:
  - A strict **command allowlist** — the engine may only run templates from an internal registry (snapshot create/delete, USN journal read, `robocopy`, service control, disk/space query, host info). Arbitrary user-supplied command strings are a v2 feature behind an admin-only flag with a documented risk acceptance.
  - **All parameters passed as encoded arguments**, never string-concatenated into a command line. No shell interpolation, ever.
  - **Idempotent, re-runnable scripts** with explicit exit-code contracts.
- **Session handling**: connection pooling with max-sessions-per-host, session reuse where safe, a hard per-host concurrency cap, and clean session teardown that does not leave orphaned WinRM shells on the target.
- **WinRM failure mode handling**: distinguish auth failure, throttling (`WSMan quota`), certificate failure, and transport failure. Log the target's `WSMan` quota state on throttle so operators know to raise it.
- **Where WinRM is unavailable**: allow a `smb_only` host mode. In that mode VSS, USN journal, and pre/post scripts are disabled, and the UI must show the job as "degraded capability" — never silently pretend the features are active.

## 4. Scheduling and execution engine

### 4.1 Scheduler

- Schedules are **cron-like with a timezone**, not naive UTC cron. Store the IANA timezone per schedule. Handle DST transitions explicitly: define and document whether a job scheduled in a skipped hour runs once or is skipped, and whether a repeated hour runs once or twice. Write tests for both.
- Support additional trigger types beyond cron: **interval**, **manual/on-demand**, **chained** (run B when A succeeds), and **event-driven** (a watched file appears, a webhook fires, a host comes back online).
- **Calendars and blackout windows**: per-schedule exclusion dates and shared maintenance windows. A job that would start inside a blackout is either deferred or skipped per policy.
- **Catch-up policy** for missed runs (agent down, host offline): `skip`, `run_once`, or `run_all`, per schedule.
- **Concurrency rules**: per-host mutual exclusion by default; per-policy concurrency limits; a global worker pool with priority classes. A slow Full must never starve the nightly Incrementals of a different host.
- **Jitter** on start time to avoid a thundering herd at midnight.

### 4.2 Job lifecycle

Implement an explicit state machine, persisted, with legal transitions enforced in code and tested:

```
QUEUED -> PREFLIGHT -> SNAPSHOT -> SCANNING -> COPYING -> VERIFYING -> INDEXING -> PRUNING -> SUCCEEDED
                                                                                      -> FAILED
                                                                                      -> CANCELLED
                                                                                      -> PARTIAL
```

- `PARTIAL` is a real, first-class state: some sources succeeded, some failed. Do not collapse it into `FAILED`.
- **Cancellation** must be cooperative and must still clean up: release the snapshot, close sessions, remove partial chunks, write the audit record.
- **Retries** with exponential backoff + jitter, a max attempt count, and per-error-class retry policy. Retries resume; they do not restart from zero where the strategy allows resumable copy.
- **Checkpointing**: progress is written to the durable queue at least every N files or T seconds so a worker crash loses bounded work, not the whole run.
- **Job deadline** independent of retries: a hard wall-clock ceiling after which the job is cancelled cleanly and marked `FAILED` with reason `deadline_exceeded`.

### 4.3 Queue and workers

- Durable queue with **at-least-once delivery** and **idempotent handlers**. Implement on top of a transactional store (Postgres `SELECT ... FOR UPDATE SKIP LOCKED` is an acceptable and preferred baseline) rather than requiring Redis/RabbitMQ — but keep the queue behind an interface so Redis/RabbitMQ/SQS can be swapped in.
- **Workers are horizontally scalable and stateless.** Their only local state is scratch space. Deploy as N replicas; a leader election (or a DB advisory lock) guards singleton duties like the scheduler tick and orphan reaper.
- **Graceful shutdown**: on SIGTERM a worker stops accepting new jobs, finishes or checkpoints the current one within a drain deadline, then exits.
- **Backpressure and rate limiting**: per-host, per-credential, and global limits on in-flight jobs and on bytes-per-second. Bandwidth throttling must be real (implemented in the copy strategy), not advisory.
- **Crash recovery**: on startup a worker reclaims jobs whose heartbeat has expired. Reclaimed jobs run their recovery path — verify/reap snapshot, reconcile partial manifests, then retry or fail.

### 4.4 "Other things" the app must also do

The scheduler is a general automation platform. Beyond backups it must support:

1. **Scheduled PowerShell tasks** against hosts (allowlisted, template-driven) — e.g. clear temp dirs, rotate IIS logs, restart a service, run a disk-cleanup script.
2. **Local (server-side) tasks** — run an internal Python callable or a script from a reviewed, admin-registered script library.
3. **Composable workflows** — a DAG of steps where a step is a backup, a remote command, a local task, a notification, a delay, or a conditional. Include retry and on-failure branching per step, with per-step timeout.
4. **Notifications** — SMTP email, generic webhook, Microsoft Teams and Slack incoming webhooks, and a pluggable `Notifier` interface. Notification rules are per-job and per-policy: on failure, on success, on long-running, on repeated failure (flap detection), with templated subject and body.
5. **Restore and browse** — browse a backup set as a tree, select files/folders or an entire set, and restore to the original location or an alternate location, with an overwrite policy and an optional restore-to-host-over-SMB path. Restores are jobs too, and are audited like any other.
6. **Reporting** — per-job success rate, duration trend, bytes protected, dedup ratio, storage growth, top failing hosts, mean time to recover. Exportable to CSV and via API.
7. **Health and housekeeping tasks** — repository integrity scrub, orphan snapshot reaper, orphan chunk GC, stale-job reaper, certificate expiry check, credential expiry check.
8. **Data classification and search** — an optional, off-by-default indexer that can search filenames and (with an explicit per-job opt-in) extracted text, so users can answer "which backup has the Q3 invoice?" Never enable content indexing without an explicit admin decision recorded in the audit log.

**Extension seam requirement:** adding a new task type must mean (a) implementing a `TaskHandler` interface, (b) registering it, (c) adding UI metadata. It must **not** require touching the scheduler, the queue, or the state machine. Demonstrate this by implementing at least one task type as a plugin loaded from an out-of-tree package, with a test proving the plugin loads without any core change.

## 5. Web application surface

### 5.1 Stack

- **Backend**: FastAPI (Python 3.12+), Pydantic v2 for all I/O models, SQLAlchemy 2.x with **Alembic** migrations, async I/O throughout.
- **Database**: PostgreSQL 15+ in production. SQLite is acceptable only for local dev and must be a documented dev-only path. No ORM lazy-loading in request handlers.
- **Frontend**: React 18 + TypeScript (strict), Vite, TanStack Query, React Router. Component library: your choice — pick one, justify it in `docs/DECISIONS.md`, and stay consistent. Include a dark mode.
- **API**: versioned REST under `/api/v1` with an **OpenAPI 3.1 spec generated from code** and served interactively. Also expose a **WebSocket or SSE stream** for live job logs and dashboard updates.
- **Packaging**: multi-stage Dockerfile producing a slim, non-root, read-only-rootfs-friendly image. `docker compose` for local dev with Postgres, MinIO, and Vault. Helm chart for Kubernetes (see §11).

### 5.2 Pages and features

1. **Dashboard** — fleet health, jobs running now with live progress, next 24h schedule, recent failures, storage consumed vs. capacity, credential warnings.
2. **Hosts** — inventory of target machines with OS version, WinRM/SMB reachability, last successful backup, capability flags (VSS available? WinRM available? degraded?), tags, and a connection test button.
3. **Credentials** — vault-backed credential list, health status, rotation due, usage map (which jobs use this), and a test-connection action. Secrets are write-only in the UI: never returned by the API, only replaced.
4. **Repositories** — storage backends, capacity, dedup ratio, integrity status, last scrub result.
5. **Jobs** — templates and instances as separate concepts. A **Job Template** is the definition (sources, type, schedule, retention, credentials, notifications); a **Job Instance** is one execution with its own status, logs, metrics, and artifacts. This separation is required.
6. **Schedules** — calendar view, blackout windows, upcoming runs, and a "simulate next 30 days" preview that shows exactly when the job would fire.
7. **Workflows** — visual DAG editor with drag-and-drop, validation on save (no cycles, no dangling references), and a dry-run mode.
8. **Restore** — browsable backup sets, selection UI, restore wizard with overwrite policy and a clear confirmation that names exactly what will be overwritten.
9. **Run console** — live tailing of logs with level filtering, search, and a "download full log" action.
10. **Reports** — the reporting set above with date-range filters and CSV/JSON export.
11. **Audit log** — immutable, filterable by actor, target, action, and time. Exportable.
12. **Settings** — global policy, authentication config, notification defaults, retention defaults, feature flags, license/telemetry toggles.
13. **Admin: RBAC** — roles, permissions, and user/group management.

Every list view needs server-side pagination, sorting, and filtering. Every destructive action needs a typed confirmation (the user types the resource name), not just an OK button. Every long operation needs optimistic UI with a real server-truth reconciliation, and the UI must never claim success before the server confirms it.

## 6. Authentication and authorization

- **Local accounts** (Argon2id password hashing) with optional **TOTP MFA**, **recovery codes**, and **WebAuthn/passkey** support.
- **OIDC / OAuth2** single sign-on with group-to-role mapping. Must work with Entra ID, Okta, and Keycloak — implement to the standard, verify against at least Entra ID and Keycloak.
- **LDAP / Active Directory** bind, including StartTLS and LDAPS, group-based authorization, and a documented group-to-role sync.
- **SAML 2.0** is optional for v1 but the auth layer must be an interface (`AuthProvider`) from day one so it can be added without refactoring.
- **Sessions**: short-lived access token + refresh rotation, absolute and idle timeouts, device/session management with remote revoke, and CSRF protection on cookie-based flows. Where the SPA uses bearer tokens, document the XSS-vs-CSRF tradeoff you chose.
- **RBAC model**: roles `Viewer`, `Operator`, `BackupAdmin`, `SecurityAdmin`, `Auditor`, `SuperAdmin`, with **resource-scoped** permissions (a BackupAdmin scoped to tag `site-eu` must not see or touch `site-us` hosts). Permission checks are enforced **server-side on every endpoint**, with a test that asserts each endpoint's required permission.
- **API keys** for automation, scoped, with expiry, last-used tracking, and `Bearer` auth. Keys are shown once at creation and stored hashed.
- **Service principals** for machine-to-machine use, distinct from human users in the audit trail.

## 7. Security requirements (treat as acceptance criteria)

### 7.1 General
- OWASP ASVS Level 2 as the baseline. Document any deviation and why.
- Input validation on every boundary via Pydantic. **No raw SQL string building.** Parameterized queries only.
- Security headers: strict CSP (no `unsafe-inline` in production), HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`. Explicit, narrow CORS allowlist — never `*` in production.
- Rate limiting on auth endpoints and expensive endpoints. Account lockout with alerting.
- Dependency scanning in CI (e.g. `pip-audit`, `npm audit`, OSV scanning) with a failing build on high-severity findings.

### 7.2 Path and injection safety
- **Zip-slip / path-traversal proof**: every path that originates from a backup manifest, an API parameter, or a remote host is normalized and asserted to remain inside its intended root. Write explicit tests for `..`, absolute paths, UNC paths, symlink escapes, and Windows 8.3 short names.
- **Symlink and reparse-point policy**: default to *not* following symlinks/junctions during backup, and document the flag that changes this.
- Remote command execution is template-only (§3.4). Add a test that a malicious filename cannot influence a remote command.

### 7.3 Secrets and data
- Secrets only from `SecretBackend`. Add a **CI secret scanner** plus a test that greps the repo, the built image layers, and the log output for patterns that look like credentials.
- Repository encryption: AES-256-GCM (or XChaCha20-Poly1305) with per-repository data keys wrapped by a KEK. Document key custody, rotation, and escrow. Encryption is **on by default** and the UI must refuse to create a repository without a documented key strategy.
- **Log redaction**: a logging filter that scrubs passwords, tokens, credential references, and UNC paths by policy. Add a test that feeds a synthetic secret through every log path and asserts it never appears.
- TLS everywhere: 1.2 minimum, 1.3 preferred; certificate validation on by default with an explicit, per-target opt-out that is audited.

### 7.4 Multi-tenancy
- Tenant isolation enforced at the **data layer**, not just the UI: every tenant-scoped table carries a `tenant_id`, and a repository-level guard rejects any query lacking a tenant filter. Write a test that attempts cross-tenant access on every model and expects denial.
- Per-tenant encryption keys, per-tenant retention defaults, and per-tenant audit separation.

## 8. Reliability and error handling

- **Typed error taxonomy**, not bare exceptions: `ConnectionError` subclasses (`AuthFailed`, `HostUnreachable`, `ShareNotFound`, `SmbProtocolRejected`), `SnapshotError`, `CopyError`, `StorageError` (`QuotaExceeded`, `BackendUnavailable`), `PreflightError`, `PolicyError`. Each carries a `retryable: bool` and a `remediation: str` written for an operator.
- **Actionable errors in the UI.** Every failure surface must answer: what failed, on which host, why, and what the operator should do. "Backup failed" is a defect.
- **Failure isolation**: one unreachable host must never fail a fleet-wide policy run. Aggregate results into `PARTIAL` with per-source detail.
- **Poison-job handling**: a job that fails the same way N times is quarantined, notified, and paused rather than retried forever.
- **Kill switches**: per-host, per-policy, and global pause. A single toggle must stop all new work without killing running jobs.
- **Maintenance mode** that drains workers gracefully.

## 9. Observability

- **Structured JSON logging** with correlation IDs propagated from API request → job → worker → remote call → audit record. Include `tenant_id`, `job_instance_id`, `host_id`, `credential_id` (never the secret), and `attempt`.
- **OpenTelemetry** traces and metrics, exported via OTLP. Spans for preflight, snapshot, scan, copy (per source), verify, index, prune. Attributes must include bytes copied, files copied, and duration.
- **Prometheus `/metrics`** endpoint with the RED metrics plus domain metrics: `backup_job_duration_seconds`, `backup_bytes_total`, `backup_files_total`, `backup_failures_total{reason}`, `dedup_ratio`, `repository_free_bytes`, `host_reachability`, `credential_failures_total`, `queue_depth`, `worker_in_flight`.
- **Health endpoints**: `/healthz` (liveness, no dependencies), `/readyz` (readiness, checks DB + queue + secret backend), `/startupz`. Kubernetes probes wired to these.
- **Dashboards and alerts**: ship Grafana dashboard JSON and Prometheus alert rules in the repo. Alert on backup failure rate, missing backups (a host with no successful backup in > 2× its schedule interval), repository capacity, credential expiry, and queue backlog.
- **Sensitive-data-safe**: logs and traces must never contain file *contents* or secrets. File *names* are configurable (audited) since they can be sensitive in some environments.

## 10. Data model (implement at minimum)

Design proper tables with indexes, foreign keys, and constraints. At minimum: `tenant`, `user`, `role`, `permission`, `user_role`, `api_key`, `session`, `auth_provider_config`, `host`, `host_tag`, `host_capability`, `credential`, `credential_scope`, `secret_ref`, `credential_health_check`, `repository`, `storage_backend_config`, `job_template`, `job_source`, `job_schedule`, `blackout_window`, `job_instance`, `job_step`, `job_log`, `job_metric`, `backup_set`, `backup_manifest`, `manifest_entry`, `chunk`, `chunk_ref`, `retention_policy`, `snapshot_record`, `restore_request`, `workflow`, `workflow_step`, `workflow_run`, `notification_channel`, `notification_rule`, `notification_delivery`, `audit_event`, `setting`, `feature_flag`, `plugin_registry`.

Deliverable: **Alembic migration history** that builds the schema from empty, plus a `docs/ERD.md` with a mermaid ER diagram, plus seed data for a working demo (see §13).

Key modelling rules:
- Manifests are **immutable** once written. A manifest entry is append-only.
- Chunks are reference-counted; GC only removes a chunk with a ref count of zero **and** past a safety window.
- `audit_event` is append-only and tamper-evident: chain each row with a hash of the previous row, and ship a verification CLI (`netvault audit verify`).
- Soft-delete only where operationally necessary; document the retention of soft-deleted rows.

## 11. Deployment, operations, and scale

- **Container-first.** Multi-stage Dockerfile, non-root UID, no build toolchain in the final image, `HEALTHCHECK` wired, image size budget stated and enforced in CI.
- **docker compose** for local dev and for small on-prem installs: API, worker (scalable via `--scale`), Postgres, MinIO, Vault (dev mode), optional Grafana/Prometheus.
- **Helm chart** for Kubernetes: separate Deployments for API and workers, HPA on workers driven by queue depth, PodDisruptionBudget, NetworkPolicy, resource requests/limits, `securityContext` with `runAsNonRoot`, `readOnlyRootFilesystem`, and dropped capabilities, plus a `CronJob` for housekeeping when the built-in scheduler is not desired.
- **Windows worker support**: document that workers must run on a platform that can reach the targets. State clearly which topologies are supported (Linux worker reaching Windows targets over SMB+WinRM; Windows worker hosting a scratch storage path). Include a documented `robocopy`-availability strategy for the Linux case (e.g. a documented alternative copy path, or a Windows-based worker), and do not hand-wave this — it is the single most likely place for the build to be subtly wrong.
- **Configuration**: 12-factor, environment-driven, with a validated settings object (Pydantic Settings) that **fails fast on startup** with a clear message listing every invalid or missing setting. Ship `.env.example` documenting every variable.
- **Migrations**: run automatically or via a dedicated job — pick one, document it, and make it safe for N concurrent replicas (advisory lock).
- **Backup the backup system**: document and implement how NetVault's own database and repository metadata are backed up and restored. Include a `netvault self-backup` command.
- **Capacity planning doc**: bytes-per-host estimates, chunk store growth math, dedup ratio expectations, and a sizing table for 100 / 1,000 / 10,000 hosts.

## 12. Testing, quality gates, and CI

- **Test pyramid with real numbers, not vibes.** Target ≥ 85% line coverage on first-party code, and require 100% coverage on the credential, crypto, path-safety, and retention modules.
- **Unit tests** for: the change detector (all three strategies), retention math (including DST and GFS edge cases), credential resolution order, path normalization, chunking and dedup ref counting, cron + timezone expansion, and the state machine's legal transitions.
- **Integration tests** with **Testcontainers**: real Postgres, real MinIO, real Vault, and a **mock SMB/WinRM server** that can simulate: successful copy, mid-copy disconnect, auth failure, throttle, share-not-found, locked file, path too long, Unicode filename, and snapshot failure. Tests must be deterministic — no `sleep`-based flakiness.
- **Contract tests** for the API against the generated OpenAPI spec, so the spec cannot drift from the implementation.
- **Property-based tests** (Hypothesis) for the retention calculator and the path normalizer.
- **End-to-end test** in CI that spins the full stack, creates a host pointing at the mock, runs a Full, then an Incremental, then a Differential, then a Restore, and asserts the restored bytes match the source bit-for-bit.
- **CI pipeline** (GitHub Actions or equivalent) that runs, as blocking gates: ruff/format, `mypy --strict`, unit + integration tests, frontend `tsc --noEmit` + lint + tests, `docker build`, container image scan (Trivy/Grype), `pip-audit`/`npm audit`, secret scanning, license check, and OpenAPI spec diff. Build must fail on any high-severity finding.
- **Frontend tests**: component tests plus at least one Playwright end-to-end flow covering login → create host → create job → run → view logs → restore.
- **Performance test**: a documented benchmark that backs up a synthetic 100 GB / 500,000-file tree, with the actual numbers recorded in `docs/BENCHMARKS.md`, plus a regression threshold that fails CI if throughput drops more than 20%.

## 13. Deliverables checklist

Produce all of the following. If you must sequence the work, do §1–§7 first and deliver a **runnable vertical slice** before broadening — "it starts and runs one real backup end-to-end" beats nine half-built subsystems.

- [ ] Complete source tree, backend and frontend, in one repo (monorepo layout: `backend/`, `frontend/`, `deploy/`, `docs/`, `scripts/`).
- [ ] `README.md` — what it is, architecture diagram (mermaid), 5-minute quickstart, and a clear "what this does NOT do yet" section.
- [ ] `docs/ARCHITECTURE.md` — components, data flow for each job type, sequence diagrams for Full/Incremental/Differential/restore, the failure and recovery model.
- [ ] `docs/SECURITY.md` — threat model (STRIDE), secret handling, key hierarchy, credential resolution order, least-privilege setup guide for the Windows side (what rights the service account actually needs, and why).
- [ ] `docs/OPERATIONS.md` — runbooks for: backup stuck, credential lockout, repository full, orphan snapshot, restore failure, worker crash loop, database restore, key rotation, and disaster recovery.
- [ ] `docs/WINDOWS-SETUP.md` — the exact PowerShell to enable WinRM (including `winrm quickconfig`, listener and firewall rules), the exact SMB/share permission changes needed, the VSS/`SeBackupPrivilege` requirements, and the specific list of Windows 10/11 edition caveats (e.g. SMB client limits on Home editions, WinRM defaults, and Defender/Firewall interference).
- [ ] `docs/DECISIONS.md` — every judgement call this spec left open, with rationale.
- [ ] `docs/ERD.md`, `docs/BENCHMARKS.md`, `docs/API.md`.
- [ ] Alembic migrations, seed script, and a demo dataset that produces a working dashboard on first boot.
- [ ] Dockerfiles, compose file, Helm chart, Grafana dashboards, Prometheus alert rules, `.env.example`.
- [ ] CI configuration with all gates from §12 wired up and passing.
- [ ] `scripts/` — `netvault` CLI with at least: `db migrate`, `worker run`, `scheduler run`, `job trigger`, `restore`, `audit verify`, `repo scrub`, `snapshot reap`, `self-backup`, `healthcheck`.
- [ ] A `CHANGELOG.md`, a `LICENSE`, and a `CONTRIBUTING.md` with the branch/review conventions you followed.

## 14. How to work (process requirements for the AI)

1. **Start with a written plan.** Before writing code, output: the module layout, the DB schema, the API surface, and an ordered milestone list. Wait for approval only if the tool supports it; otherwise write it to `docs/PLAN.md` and proceed.
2. **Build in vertical slices.** Each milestone must leave the system runnable and tested. Never leave the repo in a non-booting state at the end of a milestone.
3. **Commit discipline.** Small, focused commits with conventional-commit messages. Each milestone ends with a green CI run and a short entry in `CHANGELOG.md`.
4. **Ask, do not assume, on Windows-side specifics** you cannot verify — but do not block: choose a documented default, flag it clearly in `docs/DECISIONS.md` as unverified, and continue.
5. **Never stub silently.** If something is not implemented, it must raise `NotImplementedError` with a message and be listed in the README's "not yet done" section. A silent no-op is worse than a crash.
6. **No dead code, no commented-out blocks, no `TODO` without a tracked entry.**
7. **Every PR-sized change includes its tests.** No exceptions for "simple" changes.
8. **When you finish, self-review against this document** and produce a gap report: what is complete, what is partial, what is missing, and what you would build next. Be specific and honest about the gaps.

## 15. Explicit non-goals for v1

State these in the README so reviewers do not expect them:

- No installed agent on target machines.
- No CredSSP / double-hop delegation support.
- No macOS or Linux *target* backup (Windows 10/11 targets only; the *server* may run on Linux or Windows).
- No bare-metal image / disaster-recovery imaging (files and folders only, not block-level OS imaging).
- No native Windows VSS snapshot browsing UI beyond what restore requires.
- No Azure Files / Google Drive / Dropbox backends.
- No built-in RMM or patch management.

## 16. Acceptance criteria

The build is done when, on a clean machine:

1. `docker compose up` starts the full stack and the UI loads on first boot with seeded demo data.
2. An operator can add a Windows host, add a credential, test connectivity, and see pass/fail for both WinRM and SMB.
3. A Full backup against a reachable Windows host completes, produces a deduplicated, encrypted backup set, and the dashboard reflects it.
4. An Incremental run immediately after copies only the files that actually changed.
5. A Differential copies only files changed since the last Full.
6. A restore of a selected subset of files produces byte-identical output — verified by hash in an automated test.
7. Retention prunes correctly, and never deletes the last known-good full.
8. Killing a worker mid-copy leaves the system consistent; the job resumes or fails cleanly with no orphaned snapshot and no partial chunk leak.
9. A wrong credential fails fast with an actionable message and does not lock out the account.
10. The audit log verifies its own hash chain, and a tampered row is detected.
11. `mypy --strict`, the full test suite, the frontend build, and every CI gate from §12 pass.
12. `docs/OPERATIONS.md` runbooks have each been walked through at least once against the running stack.

---

**Begin by writing `docs/PLAN.md`, then build milestone 1. Do not ask me to restate this spec — it is complete. Where it is genuinely ambiguous, pick the boring standard option, document it, and keep moving.**
