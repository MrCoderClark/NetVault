# Proposed HTTP and event API

**Status: contract sketch; no endpoint exists.** FastAPI/Pydantic v2 generates OpenAPI 3.1 under `/api/v1/openapi.json` and interactive docs protected as appropriate. All tenant-scoped routes derive effective tenant from verified identity/session and enforce scoped RBAC plus DB isolation. Never trust a client-supplied `tenant_id`. State-changing calls receive a correlation ID, validate CSRF where cookies authenticate, and append an audit event in the mutation transaction. Errors use an operator-readable, typed envelope without secrets.

## Common conventions

- Prefix `/api/v1`; JSON UTF-8, ISO 8601 UTC timestamps in transport, stable opaque IDs; explicit `X-Correlation-ID`; documented pagination `limit` (bounded), `cursor`, `sort`, `order` and field allowlisted filters. Return `items` and `next_cursor`; do not return arbitrary tenant-wide counts to unauthorized users.
- Trigger, restore, credential update and other retryable mutations take `Idempotency-Key`; scope it to tenant, actor, route and payload digest. Replay returns the original result or a conflict on payload mismatch.
- `401` unauthenticated, `403` forbidden, `404` absent/inaccessible resource, `409` conflict/illegal transition, `422` validation, `429` rate limit, `503` dependency not ready. Typed job errors carry `code`, `retryable`, `host_id`, `remediation` and `correlation_id`. Public error messages never echo secrets or raw remote output.
- Permission names use `resource:action`, optionally with site/host/tag scope. All routes below have an explicit permission dependency (including export, streams and child resources); admin roles are not implicit bypasses.

| Route family | Proposed operations | Required permission examples |
| --- | --- | --- |
| `/auth/*` | local login, MFA challenge/recovery, OIDC callback, LDAP login, passkey flow, refresh, logout, session list/revoke | own session; `users:manage` for others |
| `/tenants`, `/users`, `/roles`, `/api-keys`, `/settings` | admin lists, scoped role assignment, one-time API-key issuance/revoke, policy edits | `tenant:manage`, `users:manage`, `settings:manage` |
| `/dashboard` | scoped KPI snapshot, recent jobs, live progress, warnings, upcoming schedule | `dashboard:read` with per-resource filtering |
| `/hosts`, `/hosts/{id}`, `/hosts/{id}/connection-tests` | CRUD, capability/health details, bounded WinRM+SMB probe | `hosts:read/write/test` |
| `/credentials`, `/credentials/{id}/rotate`, `/credentials/{id}/health-checks` | metadata CRUD, write-only secret replacement, usage/health | `credentials:read/write/test` |
| `/repositories`, `/repositories/{id}/scrubs` | backend/capacity, create/update (key strategy mandatory), scrub | `repositories:read/write/scrub` |
| `/job-templates`, `/job-templates/{id}/trigger` | definitions, source/policy/notify config, on-demand run | `jobs:read/write/trigger` |
| `/job-instances`, `/job-instances/{id}`, `/job-instances/{id}/cancel`, `/job-instances/{id}/retry`, `/job-instances/{id}/logs` | execution state, progress, actions, paginated logs/download | `runs:read/cancel/retry` |
| `/schedules`, `/schedules/{id}/simulate`, `/blackout-windows` | cron/interval, next 30 days, maintenance windows | `schedules:read/write` |
| `/workflows`, `/workflow-runs` | versioned DAG CRUD/validate/dry-run/run | `workflows:read/write/run` |
| `/backup-sets`, `/backup-sets/{id}/entries`, `/restores` | set/manifest browser, restore request and status | `backups:read`, `restores:execute` |
| `/reports`, `/reports/export`, `/audit-events`, `/audit-events/export` | date/scoped aggregation, CSV/JSON, filterable audit | `reports:read`, `audit:read/export` |
| `/notification-channels`, `/notification-rules` | channel metadata (secret refs only), rule CRUD | `notifications:manage` |

`GET /healthz` checks process only, `/startupz` startup completion, `/readyz` DB/queue/secret-backend readiness; `/metrics` Prometheus with separate internal access control. Non-tenant liveness must not reveal configuration.

## Representative contracts

```json
{
  "POST /api/v1/job-templates/{id}/trigger": {
    "request": {"source_ids": ["source-id"], "reason": "operator request"},
    "response_202": {"job_instance_id": "run-id", "status": "QUEUED", "correlation_id": "trace-id"}
  }
}
```

```json
{
  "code": "host_unreachable",
  "message": "Preflight could not reach the selected host",
  "host_id": "host-id",
  "retryable": true,
  "remediation": "Verify the host address, network route and configured WinRM/SMB ports",
  "correlation_id": "trace-id"
}
```

Credentials accept `secret` only on create/replace request; GET/list/audit/SSE responses expose **no secret, secret value, vault path, recovery code or bearer token**. Restore creation requires explicit set, selection, target and overwrite policy; destructive overwrite UI confirmation is a separate client action, and server validates both authorization and path safety.

## Live updates

`GET /api/v1/events?topics=dashboard,jobs` is an authenticated SSE stream, scoped to tenant and permissions. Event envelopes have `{id, type, occurred_at, resource_id, correlation_id, data}`; `job.progress`, `job.log`, `job.state`, `host.reachability`, `dashboard.refresh` are planned types. Support `Last-Event-ID` replay within a bounded retention window; outside that window return a snapshot-refresh signal. Redact paths/remote output and enforce the same permissions as REST. Periodic heartbeat prevents idle proxy timeouts. TanStack Query invalidates/refetches on reconnect and reconciles optimistic actions with server truth.

## Contract checks

Generate types from OpenAPI; automated tests compare implementation schemas to the committed/generated specification, check permission dependencies for every endpoint, and verify tenant isolation across list/detail/export/SSE. [TEST-PLAN](TEST-PLAN.md) owns these gates.
