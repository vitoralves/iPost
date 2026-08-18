from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, urlparse

from ipost.agents.schemas import TopicSpec, TrackSpec
from ipost.brand import BrandKit, StyleRef
from ipost.errors import ConfigError
from ipost.settings import Settings, get_settings
from ipost.storage import StorageError, delete_private_object, supabase_client


def _settings(settings: Settings | None) -> Settings:
    return settings or get_settings()


def _table_missing(exc: Exception) -> bool:
    text = str(exc).lower()
    return "could not find the table" in text or "schema cache" in text or ("42p01" in text)


def _require_client(settings: Settings):
    try:
        return supabase_client(settings)
    except StorageError as exc:
        raise ConfigError(str(exc)) from exc


def _missing_tables() -> ConfigError:
    return ConfigError("Supabase tables are missing. Run: uv run --package ipost python -m ipost.migrate")


PRIVATE_REF_PREFIX = "private:"


def _style_ref_from_row(item: dict) -> StyleRef:
    raw = item.get("url") or ""
    path = ""
    url = raw
    if raw.startswith(PRIVATE_REF_PREFIX):
        path = raw[len(PRIVATE_REF_PREFIX) :]
        url = f"/brand-kit/refs/{item['id']}"
    return StyleRef(
        id=item["id"],
        url=url,
        path=path,
        note=item.get("note") or "",
        topic=item.get("topic_slug") or "",
    )


def _persist_ref_url(ref: StyleRef, existing: dict[str, str]) -> str:
    if ref.path:
        return f"{PRIVATE_REF_PREFIX}{ref.path}"
    if ref.url.startswith("/brand-kit/refs/") and ref.id in existing:
        return existing[ref.id]
    return ref.url


def _sanitize_error(exc: Exception, settings: Settings) -> str:
    text = str(exc)
    url = settings.supabase_db_url
    if url:
        text = text.replace(url, "SUPABASE_DB_URL")
        password = urlparse(url).password
        if password:
            text = text.replace(password, "***")
            text = text.replace(quote(password, safe=""), "***")
    return text


def _direct_project_ref(hostname: str) -> str | None:
    labels = hostname.split(".")
    if len(labels) >= 4 and labels[0] == "db" and labels[-2:] == ["supabase", "co"]:
        return labels[1]
    return None


def _postgres_connect(settings: Settings):
    import psycopg

    parsed = urlparse(settings.supabase_db_url)
    host = parsed.hostname or ""
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or ""
    dbname = (parsed.path or "/postgres").lstrip("/") or "postgres"
    ref = _direct_project_ref(host)
    if ref:
        host = f"aws-0-{settings.supabase_db_region}.pooler.supabase.com"
        port = 5432
        if "." not in user:
            user = f"{user}.{ref}"
    return psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        sslmode="require",
        autocommit=True,
        prepare_threshold=None,
        connect_timeout=15,
    )


def load_brand_kit(settings: Settings | None = None) -> BrandKit:
    settings = _settings(settings)
    client = _require_client(settings)
    try:
        rows = client.table("brand_kit").select("*").eq("id", "default").execute().data or []
        refs = (
            client.table("style_refs")
            .select("*")
            .order("sort_order")
            .execute()
            .data
            or []
        )
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    if not rows:
        return BrandKit()
    row = rows[0]
    return BrandKit(
        voice_tone=row["voice_tone"],
        banned=list(row.get("banned") or []),
        refs=[_style_ref_from_row(item) for item in refs],
    )


def save_brand_kit(kit: BrandKit, settings: Settings | None = None) -> BrandKit:
    settings = _settings(settings)
    client = _require_client(settings)
    try:
        current = client.table("style_refs").select("id,url").execute().data or []
        existing = {item["id"]: item["url"] for item in current}
        client.table("brand_kit").upsert(
            {"id": "default", "voice_tone": kit.voice_tone, "banned": kit.banned}
        ).execute()
        client.table("style_refs").delete().neq("id", "").execute()
        if kit.refs:
            client.table("style_refs").insert(
                [
                    {
                        "id": ref.id,
                        "url": _persist_ref_url(ref, existing),
                        "note": ref.note,
                        "topic_slug": ref.topic.strip() or None,
                        "sort_order": index,
                    }
                    for index, ref in enumerate(kit.refs)
                ]
            ).execute()
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    return load_brand_kit(settings)


def get_brand_ref(ref_id: str, settings: Settings | None = None) -> StyleRef | None:
    settings = _settings(settings)
    client = _require_client(settings)
    try:
        rows = (
            client.table("style_refs")
            .select("*")
            .eq("id", ref_id)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    if not rows:
        return None
    return _style_ref_from_row(rows[0])


def upsert_brand_ref(ref: StyleRef, settings: Settings | None = None) -> StyleRef:
    settings = _settings(settings)
    client = _require_client(settings)
    try:
        current = (
            client.table("style_refs")
            .select("id,url,sort_order")
            .execute()
            .data
            or []
        )
        existing = {item["id"]: item["url"] for item in current}
        sort_order = next((item["sort_order"] for item in current if item["id"] == ref.id), None)
        if sort_order is None:
            sort_order = max((item["sort_order"] for item in current), default=-1) + 1
        client.table("style_refs").upsert(
            {
                "id": ref.id,
                "url": _persist_ref_url(ref, existing),
                "note": ref.note,
                "topic_slug": ref.topic.strip() or None,
                "sort_order": sort_order,
            }
        ).execute()
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    loaded = get_brand_ref(ref.id, settings)
    if loaded is None:
        raise ConfigError("Style ref was not saved")
    return loaded


def delete_brand_ref(ref_id: str, settings: Settings | None = None) -> None:
    settings = _settings(settings)
    ref = get_brand_ref(ref_id, settings)
    if ref is None:
        return
    if ref.path:
        try:
            delete_private_object(settings, ref.path)
        except StorageError:
            pass
    client = _require_client(settings)
    try:
        client.table("style_refs").delete().eq("id", ref_id).execute()
    except Exception as exc:
        raise ConfigError(str(exc)) from exc


def list_topics(settings: Settings | None = None) -> list[TopicSpec]:
    settings = _settings(settings)
    client = _require_client(settings)
    try:
        rows = client.table("topics").select("*").order("name").execute().data or []
        links = client.table("track_topics").select("*").execute().data or []
        refs = client.table("style_refs").select("*").not_.is_("topic_slug", "null").order("sort_order").execute().data or []
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    audio_map: dict[str, list[str]] = {}
    for link in links:
        audio_map.setdefault(link["topic_slug"], []).append(link["track_id"])
    ref_map: dict[str, list[str]] = {}
    for ref in refs:
        mapped = _style_ref_from_row(ref)
        if mapped.url:
            ref_map.setdefault(ref["topic_slug"], []).append(mapped.url)
    return [
        TopicSpec(
            slug=row["slug"],
            name=row["name"],
            weight=row["weight"],
            enabled=row["enabled"],
            last_used=row.get("last_used"),
            audio_ids=audio_map.get(row["slug"], []),
            refs=ref_map.get(row["slug"], []),
        )
        for row in rows
    ]


def upsert_topic(topic: TopicSpec, settings: Settings | None = None) -> TopicSpec:
    settings = _settings(settings)
    client = _require_client(settings)
    try:
        client.table("topics").upsert(
            {
                "slug": topic.slug,
                "name": topic.name,
                "weight": topic.weight,
                "enabled": topic.enabled,
                "last_used": topic.last_used,
            }
        ).execute()
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    return topic


def list_tracks(settings: Settings | None = None) -> list[TrackSpec]:
    settings = _settings(settings)
    client = _require_client(settings)
    try:
        rows = client.table("tracks").select("*").order("title").execute().data or []
        links = client.table("track_topics").select("*").execute().data or []
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    topic_map: dict[str, list[str]] = {}
    for link in links:
        topic_map.setdefault(link["track_id"], []).append(link["topic_slug"])
    return [
        TrackSpec(
            id=row["id"],
            title=row["title"],
            artist=row["artist"],
            duration=row.get("duration") or "",
            last_used=row.get("last_used"),
            path=row.get("storage_path") or "",
            topics=topic_map.get(row["id"], []),
        )
        for row in rows
    ]


def get_track(track_id: str, settings: Settings | None = None) -> TrackSpec | None:
    for track in list_tracks(settings):
        if track.id == track_id:
            return track
    return None


def upsert_track(track: TrackSpec, settings: Settings | None = None) -> TrackSpec:
    settings = _settings(settings)
    client = _require_client(settings)
    try:
        client.table("tracks").upsert(
            {
                "id": track.id,
                "title": track.title,
                "artist": track.artist,
                "duration": track.duration,
                "last_used": track.last_used,
                "storage_path": track.path,
            }
        ).execute()
        client.table("track_topics").delete().eq("track_id", track.id).execute()
        if track.topics:
            client.table("track_topics").insert(
                [{"track_id": track.id, "topic_slug": slug} for slug in track.topics]
            ).execute()
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc
    return track


def delete_track(track_id: str, settings: Settings | None = None) -> None:
    settings = _settings(settings)
    track = get_track(track_id, settings)
    if track is None:
        return
    if track.path:
        try:
            delete_private_object(settings, track.path)
        except StorageError:
            pass
    client = _require_client(settings)
    try:
        client.table("tracks").delete().eq("id", track_id).execute()
    except Exception as exc:
        if _table_missing(exc):
            raise _missing_tables() from exc
        raise ConfigError(str(exc)) from exc


def apply_sql(settings: Settings | None = None) -> None:
    settings = _settings(settings)
    sql_path = Path(__file__).resolve().parent / "sql" / "001_config.sql"
    sql = sql_path.read_text(encoding="utf-8")
    if not settings.supabase_db_url:
        raise ConfigError("SUPABASE_DB_URL is required to apply SQL from the app")
    statements = [part.strip() for part in sql.split(";") if part.strip()]
    try:
        with _postgres_connect(settings) as connection:
            for statement in statements:
                connection.execute(statement)
            connection.execute("notify pgrst, 'reload schema'")
    except ConfigError:
        raise
    except Exception as exc:
        message = _sanitize_error(exc, settings)
        lowered = message.lower()
        if "password authentication failed" in lowered:
            message = (
                "Supabase rejected the database password in SUPABASE_DB_URL. "
                "Copy the Session pooler URI from Database → Connect (port 5432) "
                "and URL-encode special characters in the password."
            )
        elif "nodename nor servname" in lowered or "could not translate host" in lowered:
            message = (
                "Could not reach the database host. Direct db.*.supabase.co URLs are IPv6-only. "
                "Use the Session pooler URI from Database → Connect (port 5432)."
            )
        raise ConfigError(message) from None
