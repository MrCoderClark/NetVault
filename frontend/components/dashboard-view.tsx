"use client";

import {
  Activity,
  Bell,
  CalendarDays,
  ChevronDown,
  CircleHelp,
  Database,
  FileClock,
  FileText,
  Folder,
  HardDrive,
  KeyRound,
  LayoutDashboard,
  Menu,
  Network,
  RotateCcw,
  Search,
  Settings,
  ShieldCheck,
  Upload,
  Workflow,
  X,
  type LucideIcon,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getDashboard, type Dashboard } from "@/lib/api";

const navigation: { label: string; icon: LucideIcon; active?: boolean }[] = [
  { label: "Dashboard", icon: LayoutDashboard, active: true },
  { label: "Hosts", icon: HardDrive },
  { label: "Credentials", icon: KeyRound },
  { label: "Repositories", icon: Database },
  { label: "Jobs", icon: Folder },
  { label: "Schedules", icon: CalendarDays },
  { label: "Workflows", icon: Workflow },
  { label: "Restore", icon: Upload },
  { label: "Reports", icon: FileText },
  { label: "Audit Log", icon: FileClock },
  { label: "Settings", icon: Settings },
];

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const tier = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** tier).toFixed(1)} ${units[tier]}`;
}

function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      {open && (
        <button
          type="button"
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={onClose}
        />
      )}
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">N</div>
          <span>NETVAULT</span>
          <button
            type="button"
            className="mobile-close"
            aria-label="Close navigation"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>
        <nav className="nav-items" aria-label="Main navigation">
          {navigation.map(({ label, icon: Icon, active }) =>
            active ? (
              <Link
                key={label}
                href="/dashboard/"
                aria-current="page"
                className="nav-link nav-link-active"
                onClick={onClose}
              >
                <Icon size={17} strokeWidth={1.6} aria-hidden="true" />
                <span>{label}</span>
              </Link>
            ) : (
              <span key={label} className="nav-link nav-link-planned" title="Planned feature">
                <Icon size={17} strokeWidth={1.6} aria-hidden="true" />
                <span>{label}</span>
                <span className="nav-soon">Soon</span>
              </span>
            ),
          )}
        </nav>
        <div className="sidebar-footer">
          <CircleHelp size={16} aria-hidden="true" />
          <span>Milestone 1 / Demo</span>
        </div>
      </aside>
    </>
  );
}

function Topbar({ data, onMenu }: { data?: Dashboard; onMenu: () => void }) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <Button
          size="icon"
          variant="ghost"
          className="menu-button"
          aria-label="Open navigation"
          onClick={onMenu}
        >
          <Menu size={20} />
        </Button>
        <span className="site-name">Site: EU-Dublin</span>
        <span className="topbar-divider" aria-hidden="true" />
        <span className="tenant-label" title="Tenant switching is planned">
          {data?.tenant_name ?? "Example tenant"}
          <ChevronDown size={14} aria-hidden="true" />
        </span>
      </div>
      <div className="topbar-right">
        <span className="search-placeholder" title="Search is planned">
          <Search size={17} aria-hidden="true" />
          <span>Search (soon)</span>
        </span>
        <span className="running-pill">{data?.stats.running_jobs ?? 0} JOBS RUNNING</span>
        <span className="header-icon" title="Notifications are planned">
          <Bell size={18} aria-hidden="true" />
        </span>
        <span className="avatar" aria-label="Demo workspace">NV</span>
      </div>
    </header>
  );
}

function KpiCards({ data }: { data: Dashboard }) {
  const cards = [
    { label: "HOSTS", value: data.stats.hosts.toLocaleString(), note: "Sample inventory" },
    { label: "PROTECTED", value: formatBytes(data.stats.protected_bytes), note: "Real backups only" },
    {
      label: "SUCCESS 24H",
      value: data.stats.success_24h_percent === null
        ? "No data"
        : `${data.stats.success_24h_percent.toFixed(1)}%`,
      note: "No actual runs",
    },
    { label: "CRITICAL", value: data.stats.critical.toString(), note: "Verified alerts" },
  ];
  return (
    <div className="kpi-grid">
      {cards.map((card) => (
        <Card key={card.label} className="kpi-card">
          <span className="kpi-value">{card.value}</span>
          <span className="kpi-label">{card.label}</span>
          <span className="kpi-note">{card.note}</span>
        </Card>
      ))}
    </div>
  );
}

function ActivityTable({ data }: { data: Dashboard }) {
  return (
    <Card className="activity-panel" aria-labelledby="activity-title">
      <div className="panel-heading">
        <div>
          <h2 id="activity-title">Example activity</h2>
          <p>Illustrative rows only. No backup jobs have run.</p>
        </div>
        <span className="demo-tag">DEMO DATA</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">STATUS</th>
              <th scope="col">JOB</th>
              <th scope="col">TYPE</th>
              <th scope="col">HOST</th>
              <th scope="col">TARGET</th>
              <th scope="col">PROGRESS</th>
              <th scope="col">EXAMPLE TIME</th>
            </tr>
          </thead>
          <tbody>
            {data.activities.map((row) => (
              <tr key={row.id}>
                <td><span className="sample-status">Sample</span></td>
                <td>Backup preview</td>
                <td><span className="type-badge">{row.job_type}</span></td>
                <td className="cell-strong">{row.host_name}</td>
                <td>{row.target_name}</td>
                <td>
                  <div className="progress-cell">
                    <div
                      className="progress-track"
                      role="progressbar"
                      aria-label={`Example progress for ${row.host_name}`}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={row.progress}
                    >
                      <span style={{ width: `${row.progress}%` }} />
                    </div>
                    <span>{row.progress}%</span>
                  </div>
                </td>
                <td>{new Date(row.occurred_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data.activities.length === 0 && (
          <p className="empty-table">No sample activity for this site.</p>
        )}
      </div>
    </Card>
  );
}

function ThroughputPanel({ data }: { data: Dashboard }) {
  const hasSamples = data.read_mbps.length > 0 || data.write_mbps.length > 0;
  return (
    <Card className="side-panel" aria-labelledby="throughput-title">
      <div className="side-panel-header">
        <h2 id="throughput-title">Live throughput</h2>
        <Activity size={16} aria-hidden="true" />
      </div>
      <div className="chart-wrap">
        <div className="chart-y-axis" aria-hidden="true">
          <span>200 MB/s</span><span>150 MB/s</span><span>100 MB/s</span>
          <span>50 MB/s</span><span>0 B/s</span>
        </div>
        <div className="chart-grid" role="img" aria-label="No live throughput yet">
          {!hasSamples && <span className="chart-empty">Awaiting live backup data</span>}
        </div>
      </div>
      <div className="chart-legend">
        <span><i className="legend-read" /> Read: 0 B/s</span>
        <span><i className="legend-write" /> Write: 0 B/s</span>
      </div>
    </Card>
  );
}

function ReachabilityPanel({ data }: { data: Dashboard }) {
  return (
    <Card className="side-panel" aria-labelledby="reachability-title">
      <div className="side-panel-header">
        <h2 id="reachability-title">Host reachability</h2>
        <Network size={16} aria-hidden="true" />
      </div>
      <div className="mini-table-head"><span>HOSTNAME</span><span>STATUS</span></div>
      {data.hosts.map((host) => (
        <div className="host-row" key={host.name}>
          <span>{host.name}</span>
          <span className="unknown-status"><span className="unknown-dot" aria-hidden="true" /> Unknown</span>
        </div>
      ))}
      {data.hosts.length === 0 && <p className="host-empty">No hosts in this site.</p>}
      <p className="panel-footnote">Connectivity has not been tested. Names are samples.</p>
    </Card>
  );
}

export function DashboardView() {
  const [navOpen, setNavOpen] = useState(false);
  const { data, error, isPending, refetch, isFetching } = useQuery({
    queryKey: ["dashboard", "eu-dublin"],
    queryFn: ({ signal }) => getDashboard(signal),
    refetchInterval: 30_000,
  });

  return (
    <div className="app-shell">
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      <div className="workspace">
        <Topbar data={data} onMenu={() => setNavOpen(true)} />
        <main id="main-content" className="dashboard-content">
          <div className="page-intro">
            <div>
              <p className="eyebrow">FLEET OVERVIEW / EU-DUBLIN</p>
              <h1>Dashboard</h1>
            </div>
            <span className="connection-label">
              <ShieldCheck size={16} aria-hidden="true" />
              Demo environment
            </span>
          </div>
          <div className="demo-notice" role="status">
            <span className="notice-icon">i</span>
            <span><strong>Demo workspace.</strong> Inventory and activity are examples. No real backup, connectivity test or restore has run.</span>
          </div>
          {isPending ? (
            <div className="page-message" role="status">Loading dashboard data...</div>
          ) : error ? (
            <div className="page-message error-message" role="alert">
              <p>{error.message}</p>
              <Button variant="outline" size="sm" onClick={() => void refetch()}>
                <RotateCcw size={15} /> Retry
              </Button>
            </div>
          ) : (
            <>
              <KpiCards data={data} />
              <div className="content-grid">
                <ActivityTable data={data} />
                <div className="side-stack">
                  <ThroughputPanel data={data} />
                  <ReachabilityPanel data={data} />
                </div>
              </div>
              <p className="refresh-note" aria-live="polite">
                {isFetching ? "Refreshing dashboard..." : "Dashboard refreshes every 30 seconds"}
              </p>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
