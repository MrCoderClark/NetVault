# Design decisions and open validations

**Status: proposed choices.** Revisit decisions with evidence before implementation; do not silently change a security boundary. The [source prompt](mocks/backup-orchestrator-ai-code-prompt.md) is authoritative except for the user's explicit stack changes.

| ID | Choice and rationale | Trade-off / validation |
| --- | --- | --- |
| D01 | Next.js App Router with static export, Tailwind/shadcn and TanStack Query replaces Vite/React Router. FastAPI serves files and API from one origin to satisfy the SPA/static-asset requirement. | No Next server actions, middleware, SSR, request-time dynamic routes or server-only auth. Client routes requiring arbitrary IDs need export-compatible routing (e.g. stable page routes with query parameters); confirm deep-link refresh behavior. |
| D02 | PostgreSQL `FOR UPDATE SKIP LOCKED` for leased, at-least-once work; advisory lock for singleton schedule ticks. Transactional ownership avoids another broker until proven necessary. | DB load and fair scheduling need benchmark/priority tests. Never rely on exactly-once delivery. |
| D03 | Windows worker + robocopy to scratch is the recommended default where source/snapshot UNC access is verified; Linux worker uses an explicit SMB-client copy strategy, not imaginary robocopy. | A VSS snapshot is not automatically reachable via an existing SMB share. Validate exposure and rights; fail preflight rather than silently copying live files. No CredSSP/double-hop. |
| D04 | Hash content using SHA-256 IDs; variable-size FastCDC-style chunking with zstd compression and AES-256-GCM authenticated encryption. | Use maintained, vetted implementations; verify deterministic chunk boundaries, nonce uniqueness and integrity. Encryption may defeat byte-level ciphertext dedup unless tenant/repository scoped chunk identity and key strategy are designed together. |
| D05 | Dedup scope is per tenant and repository; shared content is never inferred across tenants. Storage keys are opaque and plaintext hashes never exposed in user-facing APIs. | Lower cross-tenant dedup, but prevents existence leaks and key-sharing complications. |
| D06 | Secret backend interface with Vault as default, AWS Secrets Manager/Azure Key Vault/encrypted-DB fallback. Secrets fetched just-in-time for execution and redacted; not copied into job payloads. | Provider integrations require separate conformance tests; encrypted-DB requires externally protected KEK. |
| D07 | Authentication uses secure, HttpOnly, SameSite cookies for session refresh with CSRF tokens on state-changing cookie requests; short-lived access tokens kept in memory, never localStorage. | Same-origin static UI simplifies CORS; session refresh and SSE auth require careful cookie semantics. OIDC, LDAP and WebAuthn need provider-level tests. |
| D08 | PostgreSQL tenant-scoped repository guard plus RLS with request/worker tenant context and cross-tenant FK constraints, to defend against missing filters. | Privileged maintenance roles require separate audited access and bypass review. |
| D09 | A nonexistent DST local time is skipped; a repeated local time fires once at the earlier offset. Store the occurrence key `(schedule_id, local_date_time)` to dedupe. | Operator-facing 30-day preview must show skipped/repeated behavior; choose once to avoid duplicate work. |
| D10 | Separate migration job with PostgreSQL advisory lock; API/worker readiness rejects schema mismatch rather than racing upgrades. | Deployment sequencing needs documented rollback/expand-contract migrations. |
| D11 | Relative source patterns use glob syntax with `**`; do not follow symlinks/reparse points by default. Exclusion and normalization occur before copying and on restore. | Windows 8.3 aliases, DFS, Unicode/case collisions and non-UTF8 names demand platform tests. |
| D12 | OpenRouter is not required for backup correctness; only consider explicit opt-in, audited, redacted features after core acceptance. | Never upload credentials, file content, paths or tenant inventory to a model by default. |
| D13 | A `smb_only` host is explicitly degraded: VSS/USN/remote tasks unavailable; do not claim a crash-consistent NTFS backup. | Requires operator-visible acceptance of reduced consistency, or blocking the job under policy. |
| D14 | Default production networking is HTTPS WinRM with certificate verification, SMB signing and SMB1 rejection; HTTP and weaker SMB policy require explicit, audited exceptions. | Exact Kerberos/NTLM, DFS and certificate behavior must be tested in representative domains. |

## Unresolved ownership and environment decisions

- **License:** repository owner must choose before publishing a LICENSE; enterprise software is not automatically open source.
- **Key custody:** pick and test an escrow/restore authority and KEK loss procedure for each deployment. A sealed-data backup without recoverable keys is not a valid backup.
- **Windows infrastructure:** confirm Windows 10/11 editions, domain versus local accounts, SMB share access to VSS view, supported VSS provider, source ACL fidelity, robocopy behavior, and credentials that are not Domain Admin.
- **External providers:** Entra/Keycloak OIDC, LDAP/AD, AWS/Azure secret stores, S3-compatible vendors and notification endpoints require test tenants and operator approval.
- **Benchmark numbers and container-size budget:** set measured baselines only after running reproducible workloads; do not invent them.
