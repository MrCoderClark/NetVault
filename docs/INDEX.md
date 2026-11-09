# NetVault documentation

**Status: proposed design only.** This repository currently contains the original brief, UI mock, and these documents. No service, backup engine, migrations, benchmark, CI pipeline, or Windows integration has been implemented or verified. “Must” below expresses an implementation requirement, not current behavior.

The authoritative product brief is [the source prompt](mocks/backup-orchestrator-ai-code-prompt.md); the [dashboard screenshot](mocks/ui-mock.png) is a visual reference. The user's stack choices take precedence over the prompt's frontend-tooling preference: Next.js static export, TypeScript, shadcn/ui and Tailwind CSS; Python 3.12+ managed with uv for backend/workers. OpenRouter is optional and not part of backup execution.

| Document | Purpose |
| --- | --- |
| [PLAN](PLAN.md) | Module layout, milestones, requirements and acceptance gates |
| [ARCHITECTURE](ARCHITECTURE.md) | Boundaries, topology, data flows, recovery |
| [ERD](ERD.md) | Proposed relational model and migrations |
| [API](API.md) | Versioned HTTP, authorization and event contracts |
| [BACKUP-AND-RESTORE](BACKUP-AND-RESTORE.md) | Source selection, copy, chunking, retention and restore |
| [SCHEDULING-AND-WORKFLOWS](SCHEDULING-AND-WORKFLOWS.md) | Queue, states, calendars, automation and DAGs |
| [SECURITY](SECURITY.md) | Threat model, secrets, auth and isolation |
| [UI-SPEC](UI-SPEC.md) | Screenshot-based interface and accessibility |
| [DEPLOYMENT](DEPLOYMENT.md) | Local, on-prem and Kubernetes target topology |
| [WINDOWS-SETUP](WINDOWS-SETUP.md) | Target and worker prerequisites and validation |
| [OPERATIONS](OPERATIONS.md) | Runbooks and disaster recovery |
| [TEST-PLAN](TEST-PLAN.md) | Test pyramid and acceptance mapping |
| [BENCHMARKS](BENCHMARKS.md) | Reproducible performance protocol; no fabricated results |
| [DECISIONS](DECISIONS.md) | Design choices, alternatives and validation risks |

## Reading rules

- Planned commands, endpoints and tables are contracts for future implementation, **not available features**.
- External Windows, identity-provider and cloud-provider details must be validated on the target environment before production use.
- A completion claim requires executable evidence against the [test plan](TEST-PLAN.md); a diagram or mock is not evidence.
- The source prompt's explicit v1 non-goals remain: no target agent, CredSSP, macOS/Linux targets, bare-metal image backup, standalone VSS browsing, Azure Files/Drive/Dropbox repositories, or RMM/patch management.
