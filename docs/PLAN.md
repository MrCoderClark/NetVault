# Build plan

**Status: plan, not implementation.** Scope is the complete [product brief](mocks/backup-orchestrator-ai-code-prompt.md); this documentation-only deliverable does not satisfy any runtime acceptance criterion. Build in vertical slices, ending each with a bootable system, passing tests and a specific gap report. Never substitute simulated target behavior for proof against a real Windows target.

## Proposed module layout

```text
backend/
  pyproject.toml, uv.lock
  netvault/
    api/ auth/ security/ models/ repositories/ connections/
    backup/ storage/ queue/ workers/ scheduler/ workflows/
    notifications/ telemetry/ plugins/ cli/
  alembic/ tests/
frontend/
  app/ components/ lib/ tests/ public/
deploy/
  compose/ helm/ monitoring/
scripts/
docs/
  mocks/ ...design and runbook documents...
```

`backend` uses Python 3.12+, uv, FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic and PostgreSQL 15+. `frontend` uses Next.js App Router **static export**, strict TypeScript, Tailwind, shadcn/ui and TanStack Query. The FastAPI image serves exported assets plus `/api/v1`; the browser fetches authenticated state from FastAPI. The queue is Postgres-backed. Boundaries and supported worker platforms are specified in [ARCHITECTURE](ARCHITECTURE.md).

## Ordered milestones

| Phase | Runnable outcome | Evidence / exit gate |
| --- | --- | --- |
| 1. Foundation | Compose boots API, DB, Vault dev, MinIO, scheduler/worker and static dashboard with clearly labelled seed data | Migrates cleanly; health/readiness; frontend export; smoke tests; initial CI |
| 2. Trust boundary | Tenant-aware CRUD, local login/session, scoped RBAC, auditable writes and vault-backed credential metadata | Cross-tenant denial, auth/session, audit-chain and permission-matrix tests |
| 3. Real vertical slice | Configured Windows host → preflight → VSS-backed Full → encrypted/deduplicated store → verified file restore | Byte-identical restore, snapshot cleanup, deliberate failure tests against a reachable target |
| 4. Policy and resilience | Incremental and Differential, detectors, GFS, leases/reclaim, S3/SMB targets, cancellation, UI operations | Change-only tests, interrupted-copy recovery, retention invariants, live progress |
| 5. Automation and enterprise | Scheduling, workflows/plugins, notification and reporting, OIDC/LDAP/passkeys, credential rotation | DST, DAG/plugin, identity-provider and authorization tests |
| 6. Operational release | Helm, metrics/alerts, self-backup, documented runbooks, benchmark and security gates | Full CI, runbook walkthroughs, real Windows/protocol acceptance, published gaps |

Do not implement optional AI before the core security and restore path works. At every phase, label the feature as complete, partial, untested or missing; no silent stubs.

## Dependency order / contracts

1. Choose tenant identity, permission model, credential/secret separation, encryption key custody and worker topology before making a remote call ([SECURITY](SECURITY.md), [DECISIONS](DECISIONS.md)).
2. Migrate [ERD](ERD.md) tables; implement repository-level tenant guards and transactional audit writes; derive [API](API.md) schemas/OpenAPI and typed client.
3. Build state machine, queue and host adapters; implement staging → verification → atomic commit and recovery ([BACKUP-AND-RESTORE](BACKUP-AND-RESTORE.md), [SCHEDULING-AND-WORKFLOWS](SCHEDULING-AND-WORKFLOWS.md)).
4. Add scheduling and secondary destinations only after the baseline restore is proven. Keep feature availability accurate in the UI ([UI-SPEC](UI-SPEC.md)).
5. Extend deployment and operate/test against a real Windows target; use mocks only for deterministic fault injection.

## Requirements ownership / traceability

| Brief section | Primary specifications | Acceptance evidence |
| --- | --- | --- |
| §1 constraints | ARCHITECTURE, SECURITY, DECISIONS | TEST-PLAN isolation, secrets, worker recovery, accessibility |
| §2 backup/sources/repositories | BACKUP-AND-RESTORE, ARCHITECTURE | Full/Incremental/Differential/Restore byte tests |
| §3 credentials/SMB/WinRM | SECURITY, WINDOWS-SETUP, BACKUP-AND-RESTORE | Probe, lockout, dialect, allowlist and target tests |
| §4 scheduling/workflows/notifications | SCHEDULING-AND-WORKFLOWS | DST, retry, plugin, partial, DAG and notification tests |
| §5 UI/API | UI-SPEC, API | Contract, component, keyboard, WCAG and Playwright tests |
| §6–7 auth/security/tenant | SECURITY, API, ERD | Permission matrix, path/secret/crypto, cross-tenant tests |
| §8 reliability | SCHEDULING-AND-WORKFLOWS, OPERATIONS | Kill/reclaim, poison, pause and cleanup tests |
| §9 telemetry | DEPLOYMENT, OPERATIONS, SECURITY | Metrics/span/log-redaction/alert tests |
| §10 model | ERD | Migration-from-empty, FK/tenant/immutability tests |
| §11 packaging/operations | DEPLOYMENT, WINDOWS-SETUP, OPERATIONS | Clean Compose boot, Helm checks, restore drill |
| §12 quality | TEST-PLAN, BENCHMARKS | Blocking CI and recorded benchmark results |
| §13–15 deliverables/process/non-goals | INDEX, PLAN, DECISIONS | Deliverable inventory and honest gap report |
| §16 acceptance | TEST-PLAN | 12 numbered acceptance gates and evidence links |

## Future implementation deliverables

Source tree, migration history/seed, README, `.env.example`, CLI, Docker/Compose/Helm, dashboards/alerts, CI, CHANGELOG, CONTRIBUTING, LICENSE (ownership decision first) and a gap report. **None of these exist as running deliverables yet.** Milestone one should create a project `AGENTS.md` only if genuinely useful project verification knowledge arises during implementation.
