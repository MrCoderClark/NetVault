from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Stats(BaseModel):
    hosts: int
    protected_bytes: int
    success_24h_percent: float | None
    critical: int
    running_jobs: int


class Activity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    host_name: str
    target_name: str
    job_type: str
    progress: int = Field(ge=0, le=100)
    occurred_at: datetime
    label: str = "Example only"


class Reachability(BaseModel):
    name: str
    status: str
    sample: bool


class Dashboard(BaseModel):
    demo_mode: bool
    tenant_name: str
    site: str
    stats: Stats
    activities: list[Activity]
    hosts: list[Reachability]
    read_mbps: list[float]
    write_mbps: list[float]
