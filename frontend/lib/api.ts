export type Dashboard = {
  demo_mode: boolean;
  tenant_name: string;
  site: string;
  stats: {
    hosts: number;
    protected_bytes: number;
    success_24h_percent: number | null;
    critical: number;
    running_jobs: number;
  };
  activities: {
    id: string;
    host_name: string;
    target_name: string;
    job_type: string;
    progress: number;
    occurred_at: string;
    label: string;
  }[];
  hosts: { name: string; status: string; sample: boolean }[];
  read_mbps: number[];
  write_mbps: number[];
};

export async function getDashboard(signal?: AbortSignal): Promise<Dashboard> {
  const origin = process.env.NODE_ENV === "development" ? "http://localhost:8000" : "";
  const response = await fetch(`${origin}/api/v1/dashboard?site=eu-dublin`, { signal });
  if (!response.ok) {
    throw new Error(`Dashboard request failed (${response.status}). Check API and demo seed.`);
  }
  return (await response.json()) as Dashboard;
}
