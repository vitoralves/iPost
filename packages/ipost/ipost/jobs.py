from __future__ import annotations

from ipost.agents.schemas import JobRecord, JobType
from ipost.errors import ConfigError
from ipost.settings import Settings, get_settings
from ipost.storage import StorageError, supabase_client


def _client(settings: Settings | None):
    settings = settings or get_settings()
    try:
        return supabase_client(settings)
    except StorageError as exc:
        raise ConfigError(str(exc)) from exc


def _table_missing(exc: Exception) -> bool:
    text = str(exc).lower()
    return "could not find the table" in text or "schema cache" in text or ("42p01" in text)


def _missing_tables() -> ConfigError:
    return ConfigError("Supabase tables are missing. Run: uv run --package ipost python -m ipost.migrate")


def save_job(job: JobRecord, settings: Settings | None = None) -> JobRecord:
    client = _client(settings)
    try:
        client.table("jobs").upsert({"id": job.id, "payload": job.model_dump()}).execute()
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    return job


def get_job(job_id: str, settings: Settings | None = None) -> JobRecord | None:
    client = _client(settings)
    try:
        rows = client.table("jobs").select("payload").eq("id", job_id).execute().data or []
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    if not rows:
        return None
    return JobRecord.model_validate(rows[0]["payload"])


def today_job(day: str, job_type: JobType, settings: Settings | None = None) -> JobRecord | None:
    for job in list_jobs(settings):
        if job.date == day and job.type == job_type:
            return job
    return None


def today_story(day: str, settings: Settings | None = None) -> JobRecord | None:
    return today_job(day, "STORY", settings)


def list_jobs(settings: Settings | None = None) -> list[JobRecord]:
    client = _client(settings)
    try:
        rows = client.table("jobs").select("payload").order("created_at", desc=True).execute().data or []
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    return [JobRecord.model_validate(row["payload"]) for row in rows]
