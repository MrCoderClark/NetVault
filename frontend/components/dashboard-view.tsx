"use client";

import {
  AlertCircle,
  Bell,
  CalendarDays,
  ChevronDown,
  Database,
  FileClock,
  FileText,
  Folder,
  HardDrive,
  Info,
  KeyRound,
  LayoutDashboard,
  Network,
  RotateCcw,
  Search,
  Settings,
  ShieldCheck,
  TrendingUp,
  Upload,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { getDashboard, type Dashboard } from "@/lib/api";

type NavItem = { label: string; icon: LucideIcon; active?: boolean };

const navigation: NavItem[] = [
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
  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  const tier = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** tier).toFixed(1)} ${units[tier]}`;
}

function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-10 hidden w-56 flex-col border-r border-slate-800/70 bg-slate-900/80 backdrop-blur lg:flex">
      <div className="flex h-14 items-center gap-2 border-b border-slate-800/70 px-5">
        <div className="grid size-7 place-items-center rounded-md bg-sky-500/20 font-serif text-base text-sky-300">
          N
        </div>
        <span className="text-sm font-semibold tracking-[0.18em] text-slate-100">NETVAULT</span>
      </div>
      <nav className="flex-1 space-y-0.5 px-2 py-3" aria-label="Main navigation">
        {navigation.map(({ label, icon: Icon, active }) => (
          <div
            key={label}
            className={cn(
              "flex h-9 items-center gap-2.5 rounded-md px-3 text-sm transition-colors",
              active
                ? "border-l-2 border-sky-400 bg-slate-800/80 pl-[10px] text-white"
                : "cursor-default text-slate-400 hover:bg-slate-800/40 hover:text-slate-200",
            )}
            title={active ? undefined : "Planned feature"}
          >
            <Icon className="size-4" strokeWidth={1.75} aria-hidden />
            <span>{label}</span>
            {!active && (
              <span className="ml-auto text-[10px] uppercase tracking-wide text-slate-500">
                Soon
              </span>
            )}
          </div>
        ))}
      </nav>
      <div className="border-t border-slate-800/70 px-5 py-3 text-[11px] text-slate-500">
        Milestone 1 · Demo
      </div>
    </aside>
  );
}

function Topbar({ data }: { data?: Dashboard }) {
  return (
    <header className="sticky top-0 z-10 flex h-14 items-center justify-between gap-4 border-b border-slate-800/70 bg-slate-900/40 px-6 backdrop-blur">
      <div className="flex min-w-0 items-center gap-3">
        <span className="whitespace-nowrap text-sm font-medium text-slate-100">
          Site: EU-Dublin
        </span>
        <Separator orientation="vertical" className="!h-5 bg-slate-700" />
        <button
          type="button"
          className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-800/40 px-2.5 py-1.5 text-xs text-slate-200 transition-colors hover:bg-slate-800/70"
          title="Tenant switching is planned"
        >
          <span>{data?.tenant_name ?? "Example tenant"}</span>
          <ChevronDown className="size-3.5 text-slate-400" aria-hidden />
        </button>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden w-56 items-center gap-2 rounded-md border border-slate-700 bg-slate-800/50 px-3 py-1.5 text-xs text-slate-500 md:flex">
          <Search className="size-3.5" aria-hidden />
          <span>Search (planned)</span>
        </div>
        <Badge className="rounded-md bg-amber-400 font-semibold text-slate-950 hover:bg-amber-400">
          {data?.stats.running_jobs ?? 0} JOBS RUNNING
        </Badge>
        <Button
          size="icon-sm"
          variant="ghost"
          aria-label="Notifications (planned)"
          className="text-slate-300"
        >
          <Bell className="size-4" />
        </Button>
        <Avatar className="size-8 border border-slate-700">
          <AvatarFallback className="bg-slate-800 text-[11px] text-slate-300">NV</AvatarFallback>
        </Avatar>
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
      value:
        data.stats.success_24h_percent === null
          ? "No data"
          : `${data.stats.success_24h_percent.toFixed(1)}%`,
      note: "No actual runs",
    },
    { label: "CRITICAL", value: data.stats.critical.toString(), note: "Verified alerts" },
  ];
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <Card
          key={card.label}
          className="border border-slate-800/70 bg-gradient-to-br from-slate-900/80 to-slate-900/50 ring-0"
        >
          <CardContent className="flex flex-col gap-1.5 p-5">
            <span className="text-3xl font-semibold tracking-tight tabular-nums text-white">
              {card.value}
            </span>
            <span className="text-[11px] font-semibold tracking-wider text-slate-400">
              {card.label}
            </span>
            <span className="text-[11px] text-slate-500">{card.note}</span>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ActivityTable({ data }: { data: Dashboard }) {
  return (
    <Card className="overflow-hidden border border-slate-800/70 bg-slate-900/60 ring-0">
      <CardHeader className="flex flex-row items-center justify-between gap-2 border-b border-slate-800/70">
        <div className="flex flex-col gap-1">
          <CardTitle className="text-sm text-slate-100">Example activity</CardTitle>
          <p className="text-xs text-slate-500">
            Illustrative rows only. No backup jobs have run.
          </p>
        </div>
        <Badge
          variant="outline"
          className="border-sky-500/40 bg-sky-500/10 text-[10px] tracking-wider text-sky-200"
        >
          DEMO DATA
        </Badge>
      </CardHeader>
      <CardContent className="overflow-x-auto p-0">
        <Table>
          <TableHeader>
            <TableRow className="border-slate-800/70 hover:bg-transparent">
              <TableHead className="text-[10px] uppercase tracking-wider text-slate-400">
                Status
              </TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider text-slate-400">
                Job
              </TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider text-slate-400">
                Type
              </TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider text-slate-400">
                Host
              </TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider text-slate-400">
                Target
              </TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider text-slate-400">
                Progress
              </TableHead>
              <TableHead className="whitespace-nowrap text-[10px] uppercase tracking-wider text-slate-400">
                Sample time
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.activities.map((row) => (
              <TableRow key={row.id} className="border-slate-800/70 hover:bg-slate-800/30">
                <TableCell>
                  <Badge
                    variant="secondary"
                    className="border border-slate-700 bg-slate-800 text-sky-200"
                  >
                    Sample
                  </Badge>
                </TableCell>
                <TableCell className="text-slate-200">Backup preview</TableCell>
                <TableCell>
                  <Badge
                    className={cn(
                      "text-[10px] font-semibold tracking-wider",
                      row.job_type === "FULL" &&
                        "bg-sky-500/20 text-sky-200 hover:bg-sky-500/20",
                      row.job_type === "INCR" &&
                        "bg-emerald-500/20 text-emerald-200 hover:bg-emerald-500/20",
                      row.job_type === "DIFF" &&
                        "bg-violet-500/20 text-violet-200 hover:bg-violet-500/20",
                    )}
                  >
                    {row.job_type}
                  </Badge>
                </TableCell>
                <TableCell className="font-medium text-white">{row.host_name}</TableCell>
                <TableCell className="text-slate-300">{row.target_name}</TableCell>
                <TableCell>
                  <div className="flex min-w-[160px] items-center gap-3">
                    <Progress
                      value={row.progress}
                      aria-label={`Example progress for ${row.host_name}`}
                      className="h-1.5 bg-slate-800 [&>div]:bg-sky-400"
                    />
                    <span className="w-10 text-xs tabular-nums text-slate-300">
                      {row.progress}%
                    </span>
                  </div>
                </TableCell>
                <TableCell className="whitespace-nowrap text-xs text-slate-400">
                  {new Date(row.occurred_at).toLocaleString()}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {data.activities.length === 0 && (
          <p className="p-6 text-sm text-slate-400">No sample activity for this site.</p>
        )}
      </CardContent>
    </Card>
  );
}

function ThroughputCard({ data }: { data: Dashboard }) {
  const hasSamples = data.read_mbps.length > 0 || data.write_mbps.length > 0;
  return (
    <Card className="border border-slate-800/70 bg-slate-900/60 ring-0">
      <CardHeader className="flex flex-row items-center justify-between border-b border-slate-800/70">
        <CardTitle className="text-sm text-slate-100">Live throughput</CardTitle>
        <TrendingUp className="size-4 text-slate-400" aria-hidden />
      </CardHeader>
      <CardContent className="p-4">
        <div className="relative grid h-32 place-items-center rounded-md border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950/50 text-xs text-slate-500">
          {hasSamples ? "Chart (planned)" : "Awaiting live backup data"}
        </div>
        <div className="mt-3 flex items-center justify-end gap-4 text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <i className="inline-block h-0.5 w-3 bg-sky-400" aria-hidden /> Read: 0 B/s
          </span>
          <span className="flex items-center gap-1.5">
            <i className="inline-block h-0.5 w-3 bg-cyan-300" aria-hidden /> Write: 0 B/s
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function ReachabilityCard({ data }: { data: Dashboard }) {
  return (
    <Card className="overflow-hidden border border-slate-800/70 bg-slate-900/60 ring-0">
      <CardHeader className="flex flex-row items-center justify-between border-b border-slate-800/70">
        <CardTitle className="text-sm text-slate-100">Host reachability</CardTitle>
        <Network className="size-4 text-slate-400" aria-hidden />
      </CardHeader>
      <CardContent className="p-0">
        <div className="flex justify-between border-b border-slate-800/70 bg-slate-900/80 px-4 py-2 text-[10px] uppercase tracking-wider text-slate-400">
          <span>Hostname</span>
          <span>Status</span>
        </div>
        <ul className="divide-y divide-slate-800/70">
          {data.hosts.map((host) => (
            <li
              key={host.name}
              className="flex items-center justify-between px-4 py-2 text-xs text-slate-200"
            >
              <span className="font-medium">{host.name}</span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="size-2 rounded-full bg-slate-500" aria-hidden />
                Unknown
              </span>
            </li>
          ))}
        </ul>
        {data.hosts.length === 0 && (
          <p className="p-4 text-xs text-slate-400">No hosts in this site.</p>
        )}
        <p className="border-t border-slate-800/70 px-4 py-2 text-[11px] text-slate-500">
          Connectivity has not been tested. Names are samples.
        </p>
      </CardContent>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 bg-slate-800/50" />
        ))}
      </div>
      <Skeleton className="h-96 bg-slate-800/50" />
    </div>
  );
}

export function DashboardView() {
  const { data, error, isPending, refetch, isFetching } = useQuery({
    queryKey: ["dashboard", "eu-dublin"],
    queryFn: ({ signal }) => getDashboard(signal),
    refetchInterval: 30_000,
  });

  return (
    <div className="min-h-screen bg-slate-950 bg-[radial-gradient(ellipse_at_top_right,_rgba(35,56,90,0.35),transparent_55%)] text-slate-100">
      <Sidebar />
      <div className="flex min-h-screen flex-col lg:ml-56">
        <Topbar data={data} />
        <main className="flex-1 space-y-4 p-4 md:p-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="mb-1 text-[10px] font-bold tracking-[0.18em] text-sky-300">
                FLEET OVERVIEW · EU-DUBLIN
              </p>
              <h1 className="text-xl font-semibold text-white">Dashboard</h1>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <ShieldCheck className="size-4" aria-hidden />
              Demo environment
            </div>
          </div>
          <Alert className="border-sky-500/30 bg-sky-500/10 text-slate-200">
            <Info className="size-4 text-sky-300" />
            <AlertTitle className="text-slate-100">Demo workspace</AlertTitle>
            <AlertDescription className="text-slate-400">
              Inventory and activity are examples. No real backup, connectivity test, or restore has run.
            </AlertDescription>
          </Alert>
          {isPending ? (
            <LoadingSkeleton />
          ) : error ? (
            <Alert variant="destructive" className="border-red-900/60 bg-red-950/40">
              <AlertCircle className="size-4" />
              <AlertTitle>Could not load dashboard</AlertTitle>
              <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
                <span>{error.message}</span>
                <Button variant="outline" size="sm" onClick={() => void refetch()}>
                  <RotateCcw className="size-3.5" /> Retry
                </Button>
              </AlertDescription>
            </Alert>
          ) : (
            <>
              <KpiCards data={data} />
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
                <ActivityTable data={data} />
                <div className="space-y-4">
                  <ThroughputCard data={data} />
                  <ReachabilityCard data={data} />
                </div>
              </div>
              <p className="text-right text-[11px] text-slate-500" aria-live="polite">
                {isFetching ? "Refreshing dashboard..." : "Dashboard refreshes every 30 seconds"}
              </p>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
