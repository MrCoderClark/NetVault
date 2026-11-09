# User interface specification

**Status: visual and interaction design only.** Source: [ui-mock.png](mocks/ui-mock.png), a dark desktop dashboard with a narrow left sidebar, top utility bar, four KPI cards, dense jobs table and right-hand throughput/reachability panels. The example numbers and machine names in the image are **not live data**. Accessibility goal: WCAG 2.2 AA. Implement with Next.js App Router static export, TypeScript strict, Tailwind CSS, shadcn/ui, TanStack Query and a typed API client.

## Visual system

- Dark slate/navy surface with subtly separated cards and thin borders; white/high-contrast primary text, cool-blue progress and chart accents, green success, amber warning and red critical/error states. Color must never be the only status indicator; include icon and text.
- Desktop: persistent collapsible sidebar (~200 px reference), topbar with brand, active site and tenant selector, search, running-job count, notifications and user menu. Main area: four responsive metrics (`Hosts`, `Protected`, `Success 24h`, `Critical`), then table/insights in an approximate 3:1 split. Layout adapts to viewport; table scrolls horizontally without clipping cells; charts and side panels stack on tablet/mobile. Do not reproduce the browser frame/URL in the screenshot as application UI.
- Typographic hierarchy: readable system sans, compact labels/table rows but minimum accessible size; consistent tabular digits for metrics. Default theme dark per mock; light mode optional with equivalent contrast. Prefer shadcn primitives with theme tokens instead of hard-coded one-off colors.
- Every metric is tenant/site scoped and has explicit loading, stale, empty and error presentation; no fabricated production numbers. Live throughput chart has axes/units, accessible text summary and fallback table. Reachability list uses named host and status text; distinguish `unknown` from `unreachable`.

## Route and feature inventory

For static export use **stable page paths** (e.g. `/jobs/detail?id=...`), not arbitrary runtime dynamic filesystem segments; FastAPI must serve deep-link fallback to exported HTML. Navigation targets:

| Route | View | Primary actions |
| --- | --- | --- |
| `/dashboard` | Fleet health, running progress, upcoming schedule, recent failures, storage/credential warnings | Filter site/tenant, inspect run |
| `/hosts` | Inventory, OS, reachability, last successful set, VSS/WinRM capabilities/tags | Add/edit/test connection, pause |
| `/credentials` | Name, scope, health, rotation due, usage map; secret never revealed | Add/replace secret, probe, rotate |
| `/repositories` | Backends, capacity, dedup/integrity and last scrub | Configure key strategy, scrub |
| `/jobs` | Templates separate from instances, progress/logs/metrics | Create, trigger, cancel, retry |
| `/schedules` | Calendar, blackout windows, next-30-day simulation | Edit/preview |
| `/workflows` | Visual DAG and run history | Add nodes/edges, validate, dry run |
| `/restore` | Backup-set tree, selection, destination, overwrite wizard | Preview/confirm/request restore |
| `/console` | Live run logs, levels/search/download | Filter and export |
| `/reports` | Success/duration/bytes/dedup/storage/failing hosts/MTTR | Date filters, CSV/JSON export |
| `/audit` | Immutable events by actor/target/action/time | Filter, export, verify result |
| `/settings` | Policies, auth, notifications, feature flags, license/telemetry | Scoped administration |
| `/admin/users` | Users, groups, roles/scopes | Grant/revoke and session revoke |

All lists use server-side pagination/sorting/filtering with URL-synchronized controls. Tenant/site switch invalidates query caches and streams; unauthorized scopes do not appear. Permission-aware UI can hide actions but server remains authoritative.

## Interaction and accessibility contract

Login has MFA/recovery/passkey and provider-specific errors; no session secret in exported HTML or localStorage. Destructive action uses a dialog requiring the resource name typed verbatim plus server confirmation; restore overwrite identifies exact destination and conflicts. Optimistic states are labelled `Pending` and reconcile with API outcome; never announce success on click alone.

Jobs show textual state, attempt, step, host, progress bytes/files, deadline and actionable remediation; `PARTIAL` shows per-source breakdown. `smb_only` displays a prominent “Degraded: no VSS/USN” badge. Surface failed credentials without exposing username secret. SSE stream updates progress/logs; reconnect restores snapshot, dedupes event IDs and announces status changes through a polite live region without flooding screen readers.

Use semantic landmarks (`nav`, `main`), table headers/captions, labelled inputs, focus-visible rings, keyboard-operable menus/drag alternatives for DAG editor, escape/return focus on dialogs, sufficient target size, 200% zoom and reflow. Charts have textual equivalents; status colors meet contrast ratios; no animation required to understand progress. Test login → host → job → run/logs → restore with keyboard and automated accessibility checks.
