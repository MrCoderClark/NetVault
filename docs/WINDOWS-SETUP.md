# Windows target and worker setup design

**Status: review-only example, not validated on a target.** Commands below would change network access and must be reviewed by a Windows administrator, run in an elevated PowerShell session on an approved Windows 10/11 test host, and adapted to local firewall/domain policy. Do not run against production from this document. HTTPS WinRM/5986 with a trusted server certificate and restricted inbound addresses is the default; never disable certificate checks as a convenience. Windows Home/Pro/Enterprise and domain policy differences require a test matrix; do not claim Home WinRM server support without validation.

## Prerequisites to verify

1. Verify edition/version, patch state, NTFS source volume, VSS availability, SMB2+ dialect/signing/encryption policy, DNS or explicitly configured IP, firewall policy and certificate chain/name. Confirm account is not Domain Admin; grant only required WinRM remote-management, share/NTFS read and *specifically approved* VSS/snapshot rights. `SeBackupPrivilege` is powerful: do not grant indiscriminately. Test capabilities in target environment.
2. Verify the copy worker (Windows for robocopy, or Linux with supported SMB strategy) can reach **the chosen VSS snapshot view**. VSS creates a local shadow copy; normal shares do not automatically expose it. Plan a reviewed snapshot-share mechanism or restrict to a validated local Windows worker topology before promising open-file consistency.
3. Ensure outbound Windows worker connectivity to DB, secret backend and repository, and inbound target WinRM/5986 and SMB/445 only from approved worker addresses. No CredSSP; avoid double-hop by performing source read from worker with its own scoped SMB credential.

## Example operator-reviewed target commands

The following shows the **shape** of setup, not a universal hardened script:

```powershell
winrm quickconfig
Enable-PSRemoting -Force
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion
Get-Service WinRM, VSS
Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol, EnableSMB2Protocol, RequireSecuritySignature, EncryptData
Get-NetFirewallRule -DisplayGroup "Windows Remote Management" | Select-Object DisplayName, Enabled, Profile
```

For HTTPS listener, have an administrator provision a trusted **Server Authentication** certificate whose SAN matches the target FQDN, then create/configure a WinRM HTTPS listener with its validated thumbprint, remove or block unintended HTTP exposure, and restrict firewall remote addresses to worker networks. Listener syntax and GPO precedence vary; test with `Test-WSMan -ComputerName <fqdn> -UseSSL` from an approved worker before any backup. Do **not** create a self-signed certificate or turn off TLS validation as an automatic fallback.

Existing shares should be audited rather than recreated blindly. On a **new dedicated source share**, after ACL review, a candidate pattern is:

```powershell
New-SmbShare -Name 'NetVaultSource' -Path 'D:\ApprovedSource' -ReadAccess 'EXAMPLE\svc-netvault'
Get-SmbShareAccess -Name 'NetVaultSource'
Get-Acl 'D:\ApprovedSource' | Format-List
```

Share `ReadAccess` does not grant NTFS file access or VSS privileges: assign the minimal required NTFS permissions separately using the site's approved identity process; do not copy broad `Everyone` permissions. A NAS repository requires a distinct write-scoped credential and ACL. If VSS snapshot exposure requires additional privileged rights or share changes, obtain a documented security approval and test that the worker reads snapshot bytes rather than live files.

## Verification matrix before enabling a host

| Case | Evidence |
| --- | --- |
| Windows 10/11 edition and domain/local mode | Recorded edition/build and explicit WinRM server capability |
| Transport | Validated HTTPS name/chain, HTTP disabled or audited opt-in, firewall restricted |
| SMB | TCP/445 reachable, negotiated dialect >= 2.1 (prefer 3.1.1), signing/encryption policy satisfied, NTLMv2/Kerberos as configured |
| Privilege | Scoped account can list/read selected share and create/delete **owned** VSS snapshot when configured; cannot access unrelated shares |
| Snapshot | Open-file sample read from snapshot via actual worker path; cleanup confirmed on success/failure |
| Edge cases | Unicode, long path, DFS/IP-only resolution, locked file, failed authentication, quota/throttle and safe lockout |

Avoid claiming `robocopy`/snapshot fidelity, registry/ACL completeness, or Home-edition support until these tests have passed. `smb_only` disables VSS/USN/remote scripts and surfaces degraded-consistency status in UI.
