# Verification and acceptance plan

**Status: future test plan; zero tests have been run.** Unit and mocks establish deterministic behavior; a real Windows 10/11 target is required to validate SMB/WinRM/VSS and restore claims. No CI pipeline or coverage figures exist yet.

## Test pyramid and gates

| Layer | Planned cases | Gate |
| --- | --- | --- |
| Unit + property | Three change detectors, USN fallback, GFS/DST and last-good Full, path normalization (`..`, UNC, absolute, symlink, 8.3), credential precedence/lockout, crypto nonce/AEAD, chunk/refcount and state transitions; Hypothesis path/retention properties | ≥85% first-party line coverage, 100% for credential/crypto/path-safety/retention modules |
| Integration | Testcontainers Postgres, MinIO, Vault; deterministic mock SMB/WinRM success, disconnect, auth failure, throttle, missing share, locked file, long path, Unicode, snapshot failure and cleanup | No `sleep` timing assumptions; tenant FKs/RLS, migrations and audit chain verified |
| API/contract | Generate OpenAPI 3.1, check schema drift and all endpoint permission dependencies, pagination, mutation/audit, CSRF and SSE replay/isolation | Fail on unguarded route, cross-tenant response or secret exposure |
| Frontend | Component tests (loading/empty/error/permission), keyboard/reflow/contrast; Playwright login → create host → create job → run → logs → restore | strict TS, lint, build/export and WCAG 2.2 AA checks |
| End-to-end mock | Boot full stack; Full → changed-file Incremental → Differential → selected Restore; compare source/destination byte-for-byte | Repeat after worker kill; no leaked partial chunk or orphan snapshot |
| Real Windows | Windows 10/11 target + appropriately privileged scoped account, HTTPS WinRM, SMB and VSS path; test locked/Unicode/long path and actual restore | Signed-off host/worker topology and byte-hash evidence |
| Supply chain / delivery | ruff/format, `mypy --strict`, pytest, frontend typecheck/lint/tests, image build/scan, `pip-audit`/`npm audit`, secrets/license scan, OpenAPI diff, Helm checks | Block high-severity findings and changed contract without review |
| Performance | [BENCHMARKS](BENCHMARKS.md) protocol | Record real throughput and fail >20% regression vs established baseline |

Avoid using real credentials in fixtures. Verify built image layers and emitted logs against synthetic secret patterns. Every mutation must include actor, target, redacted before/after and correlation ID; every secret read including scheduler reads must be audited. Verify resource-scoped RBAC for list/detail/export/stream, every tenant-scoped model, and hash-chain tamper detection. Run smoke tests after each runnable milestone.

## Acceptance criteria from product brief §16

| # | Evidence to collect (all currently **not run**) |
| --- | --- |
| 1 | Fresh `docker compose up`, migrations, seeded labelled dashboard and healthy API |
| 2 | Create host/credential and record independent SMB and WinRM pass/fail |
| 3 | Real Full against reachable Windows host, encrypted dedup set, reflected in dashboard |
| 4 | Incremental copies only changed files after Full |
| 5 | Differential copies changes since last Full, not last Incremental |
| 6 | Selected restore byte hashes match original source |
| 7 | GFS prune preserves last verified Full and all restore dependencies |
| 8 | Kill worker mid-copy; reconcile staging/lease/snapshot, no partial chunk leak |
| 9 | Wrong credential fails quickly with actionable error; lockout budget prevents account lockout |
| 10 | Audit verify passes then detects injected tampering |
| 11 | Strict mypy, entire test suite, frontend build and every CI gate pass |
| 12 | Each [runbook](OPERATIONS.md) exercised on a disposable running stack |

## Release evidence record

For each gate capture commit SHA, target OS/build, worker OS, provider versions, redacted configuration fingerprint, test command/result, trace ID and reviewer. Mark `complete`, `partial`, `blocked` or `missing` with explanation and next step; documentation alone cannot mark any test complete. Maintain per-milestone gap report and changelog entry when code work begins.
