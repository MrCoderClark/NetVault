# Security and trust boundaries

**Status: proposed controls, not certification or implementation.** Target baseline: OWASP ASVS L2, WCAG 2.2 AA for UI. No secrets in code, stored config, environment dumps, built frontend assets, audit payloads, logs or traces. Reference [WINDOWS-SETUP](WINDOWS-SETUP.md) for unverified target-specific rights.

## Threat model (STRIDE)

| Threat | Boundary and planned mitigation | Evidence gate |
| --- | --- | --- |
| Spoofing | Operator/API-key identity, OIDC discovery/signature/audience/nonce, LDAP TLS, WinRM certificate and Kerberos/NTLMv2 validation | Auth/provider/invalid-cert tests |
| Tampering | Immutable authenticated manifests, AES-GCM chunk tags, tenant-scoped audit hash chain, job transition checks | Restore hash and tamper-detection tests |
| Repudiation | Actor/service principal, purpose, before/after redacted fields, target, tenant, correlation ID on every mutation and secret read | Audit completeness tests |
| Information disclosure | RLS + repository tenant guards, secret refs, write-only UI, log/trace redaction, per-tenant/repository keys, constrained exports | Cross-tenant, synthetic-secret and object access tests |
| Denial of service | Auth lockout, request/rate/queue limits, credential login budgets, host/session caps and bounded job deadlines | Throttle/backpressure tests |
| Privilege escalation | Resource-scoped RBAC, no Domain Admin baseline, allowlisted WinRM templates, no raw SQL or shell interpolation, path confinement | Endpoint permission matrix and injection tests |

## Identity, sessions and authorization

Local Argon2id password hashing, TOTP MFA/recovery codes and WebAuthn/passkeys; OIDC with group-to-role mapping for Entra/Okta/Keycloak, LDAP/AD with StartTLS or LDAPS. `AuthProvider` interface leaves SAML as an optional extension. Verify provider metadata/keys and group sync in integration environments; none is currently operational. Roles: `Viewer`, `Operator`, `BackupAdmin`, `SecurityAdmin`, `Auditor`, `SuperAdmin`, each with resource-scoped site/tag/host permissions, checked on every REST/SSE/export route and in workers. API keys are scoped, expiring, shown once and stored hashed; machine identities are separate from humans.

Use short-lived memory-only access tokens with secure HttpOnly SameSite refresh cookies, rotating refresh hashes, idle/absolute expiry, device list/revoke and anti-CSRF token for cookie-authenticated mutations. Strict CSP without `unsafe-inline` in production, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` and narrow same-origin CORS. Do not place bearer credentials in localStorage. Rate-limit auth and expensive endpoints; lockout and alerts have safe reset workflows.

## Credential and transport policy

`Credential` metadata includes name/kind, username/domain, scopes, tags, rotation due and usage; secret bytes live in `SecretBackend`: Vault preferred, AWS Secrets Manager, Azure Key Vault, or envelope-encrypted DB fallback with KEK outside the DB. Resolve **job override → source override → host policy → credential group → global default**; share credentials may be independent of host credentials. Normalize `DOMAIN\user` and UPN forms without conflating identities. Log selected credential ID and reason, never the value. Audit every read including scheduler reads; fetch fresh on next run after rotation, support an explicitly time-limited grace version. Global/per-host authentication-failure budgets halt retries before account lockout; health probes include WinRM/SMB, applicable Kerberos, expiry and disabled/locked state.

WinRM defaults to HTTPS/5986 with certificate validation; HTTP/5985, Basic over HTTPS or certificate-auth exceptions require per-host policy and audit. No Basic over HTTP, no CredSSP. Limit sessions per host; classify throttle/quota, auth, certificate and transport errors. WinRM PowerShell is an internal template registry only (snapshot/USN/robocopy/service/disk/host info), with typed encoded parameters and no user-controlled command concatenation. SMB over TCP/445 refuses SMB1; 3.1.1 preferred, 2.1 minimum; NTLMv2 and Kerberos; support required signing/encryption policies, record negotiated dialect, distinguish transient disconnect from terminal authentication/denial/share-not-found. Target calls have connect/read timeouts and overall deadline; fail closed if policies cannot be met. Least-privilege target accounts need explicit share/NTFS/VSS rights, not Domain Admin by default.

## Data, keys and isolation

Per-tenant encryption boundary, per-repository AES-256-GCM data key (DEK) wrapped by KEK managed outside backup DB; documented escrow, rotation and tested loss recovery. Unique nonce per encrypted object/version; authenticate metadata; encrypted storage and TLS 1.2 minimum (1.3 preferred). Repository creation requires a recoverable key strategy. Chunk IDs and refs cannot cross tenants; per-tenant retention defaults and audit chains. Tenant context mandatory in repository methods and DB RLS, including worker/background and export paths; composite tenant FKs prevent cross-tenant associations. Scrub verifies integrity; restore drill proves custody.

Path confinement on backup and restore rejects `..`, absolute/UNC/device paths, case-collision, symlink/junction escapes, Windows short-name aliases and zip-slip. Default not to follow symlinks/reparse points. Do not put arbitrary remote command strings into queue jobs. Log filter redacts password/token/credential ref/UNC paths according to policy; filenames and extracted text are sensitive, indexing off by default. Set an audited option before logging filenames or enabling content search. OpenRouter has no access to credentials, file content or metadata by default.

## Audit and assurance

Append-only per-tenant hash chain covers every mutation and secret read; `netvault audit verify` recomputes and reports gaps/tampering. Hash chains detect local alteration but do not prevent a privileged operator from replacing the entire chain; plan external anchoring/backups for stronger evidence. Block CI on high-severity dependency/image findings, secret scan, unsafe license and OpenAPI/permission drift. Document any ASVS exception with owner and compensating control. Security runbooks and incident actions are in [OPERATIONS](OPERATIONS.md).
