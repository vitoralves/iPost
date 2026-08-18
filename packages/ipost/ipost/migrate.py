from __future__ import annotations

from ipost.config_store import ConfigError, apply_sql, load_brand_kit
from ipost.settings import get_settings


def main() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    if not settings.supabase_db_url:
        raise SystemExit("SUPABASE_DB_URL is missing")
    if settings.supabase_db_url:
        apply_sql(settings)
        print("applied 001_config.sql")
    try:
        kit = load_brand_kit(settings)
        print(f"brand kit ready ({len(kit.refs)} refs)")
    except ConfigError as exc:
        print(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
