# Operations runbooks

**Status: proposed runbooks, not executed.** Commands are future CLI contracts, not executable in this repository. Never delete backup data, snapshots, keys or DB records as an automatic “fix.” Capture tenant, job, host, correlation ID and time range first; restrict logs/exports to authorized operators.

## Standard triage

1. Confirm `/healthz`, `/readyz`, `/startupz`, queue depth/lease expiry and worker heartbeats. Check correlation-scoped JSON logs, traces, job steps and sanitized error remediation; distinguish `FAILED`, `PARTIAL`, `CANCELLED`, retrying and quarantined.
2. Check global/host/policy pause, repository free capacity, credential health and last verified Full. Reproduce against a test host before changing authentication/network policy. Audit every remediation action and owner.
3. Resume only after the underlying problem is corrected; use idempotent job retry, not a manual duplicate run with a new key. Confirm checksum-verified restore is still possible.

| Incident | Diagnose | Contain / recover | Verify |
| --- | --- | --- | --- |
| Backup stuck | Compare heartbeat, step checkpoint, host sessions and deadline | Drain/reclaim expired lease; preserve staging until reconciliation; isolate unreachable source | One active lease, consistent checkpoint, no duplicate set |
| Credential lockout | Check global/per-host failure budget, expiry/disabled status and credential selection reason | Pause affected jobs; coordinate authorized reset/rotation in secret backend; avoid automated repeated guesses | One bounded health probe, audit of secret reads, no fleet-wide retries |
| Repository full | Inspect `repository_free_bytes`, scratch usage and retention simulation | Pause new work; expand capacity or execute approved GFS prune without deleting protected chain | Last-good Full/chain retained, scrub and sample restore pass |
| Orphan VSS snapshot | Match provider ID to NetVault ownership, host and expired lease | Run planned `netvault snapshot reap --dry-run`; review then reap owned orphan only | Owned stale snapshot removed; active snapshot untouched |
| Restore failure | Classify missing chunk/key, target ACL, path conflict, hash mismatch | Stop overwrite; retain scratch evidence; recover keys/chunks from backup or choose alternate verified set | Hash-verified restore to isolated destination |
| Worker crash loop | Inspect startup config/schema/provider readiness and recent attempts | Quarantine poison jobs, disable new claims, fix dependency, restart one worker | Heartbeats and lease reclamation normal, no staging leak |
| Database restore | Identify last consistent DB/repository metadata point and key escrow | Isolate writers; restore DB to separate instance, match manifests/objects, validate audit chain; switch via approved procedure | Schema/version, tenant isolation, set hashes and restore drill pass |
| Key rotation | Inventory KEK/DEK versions and retained backup dependencies | Wrap new DEKs/rewrap safely, retain old decrypt keys until all referenced sets migrated; never overwrite sole escrow copy | Old and new sets decrypt/restore, audit event exists |
| Disaster recovery | Assess DB, object store, Vault/KEK, config and network loss | Rebuild isolated stack from signed artifacts; restore DB + repository metadata + secret backend and escrow; compare manifests | Full/Incremental/Differential chain and sample restore on rebuilt system |

## Routine maintenance

Planned CLI surface: `netvault db migrate`, `worker run`, `scheduler run`, `job trigger`, `restore`, `audit verify`, `repo scrub --verify`, `snapshot reap`, `self-backup`, `healthcheck`. All mutating subcommands require tenant/identity and audit record; destructive actions require dry-run and explicit authorization. Weekly verify audit chain and repository scrub; regularly test self-backup **and restore**, not merely archive creation. Review critical alerts and credential expiry. Keep a measured retention window for sanitized job logs; never use log retention as chunk GC.

## Incident evidence and runbook validation

Record symptom, trace/correlation ID, before/after, disposition, operator and final restore validation. Walk every row above on a disposable, isolated environment before declaring §16 runbook acceptance complete. At present no walkthrough has happened.
