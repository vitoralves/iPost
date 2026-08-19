from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from ipost.errors import ConfigError
from ipost.settings import Settings, get_settings
from ipost.storage import StorageError, supabase_client

LAMBDA_GB_SECOND_USD = 0.0000166667
LAMBDA_REQUEST_USD = 0.0000002


class SchedulerRun(BaseModel):
    id: str
    action: str
    status: str
    source: str = "lambda"
    job_type: str | None = None
    job_id: str | None = None
    message: str = ""
    duration_ms: int = 0
    memory_mb: int = 0
    estimated_cost_usd: float = 0
    request_id: str | None = None
    created_at: str = Field(default="")


def _client(settings: Settings | None):
    settings = settings or get_settings()
    try:
        return supabase_client(settings)
    except StorageError as exc:
        raise ConfigError(str(exc)) from exc


def _table_missing(exc: Exception) -> bool:
    text = str(exc).lower()
    return "could not find the table" in text or "schema cache" in text or ("42p01" in text)


def estimate_lambda_cost_usd(memory_mb: int, duration_ms: int) -> float:
    if memory_mb <= 0 or duration_ms <= 0:
        return 0.0
    gb_seconds = (memory_mb / 1024) * (duration_ms / 1000)
    return round(gb_seconds * LAMBDA_GB_SECOND_USD + LAMBDA_REQUEST_USD, 6)


def save_run(run: SchedulerRun, settings: Settings | None = None) -> SchedulerRun:
    if not run.created_at:
        run.created_at = datetime.now(timezone.utc).isoformat()
    client = _client(settings)
    try:
        client.table("scheduler_runs").upsert({"id": run.id, "payload": run.model_dump()}).execute()
    except Exception as exc:
        if _table_missing(exc):
            raise ConfigError(
                "Supabase tables are missing. Run: uv run --package ipost python -m ipost.migrate"
            ) from exc
        raise ConfigError(str(exc)) from exc
    return run


def list_runs(settings: Settings | None = None, limit: int = 50) -> list[SchedulerRun]:
    client = _client(settings)
    try:
        rows = (
            client.table("scheduler_runs")
            .select("payload")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        if _table_missing(exc):
            raise ConfigError(
                "Supabase tables are missing. Run: uv run --package ipost python -m ipost.migrate"
            ) from exc
        raise ConfigError(str(exc)) from exc
    return [SchedulerRun.model_validate(row["payload"]) for row in rows]


def record_run(
    *,
    action: str,
    status: str,
    settings: Settings | None = None,
    source: str = "lambda",
    job_type: str | None = None,
    job_id: str | None = None,
    message: str = "",
    duration_ms: int = 0,
    memory_mb: int = 0,
    request_id: str | None = None,
) -> SchedulerRun | None:
    run = SchedulerRun(
        id=f"run-{uuid4().hex[:12]}",
        action=action,
        status=status,
        source=source,
        job_type=job_type,
        job_id=job_id,
        message=message[:2000],
        duration_ms=duration_ms,
        memory_mb=memory_mb,
        estimated_cost_usd=estimate_lambda_cost_usd(memory_mb, duration_ms),
        request_id=request_id,
    )
    try:
        return save_run(run, settings)
    except ConfigError:
        return None
