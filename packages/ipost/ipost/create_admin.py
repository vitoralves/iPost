from __future__ import annotations

import argparse

from ipost.auth import upsert_user
from ipost.errors import ConfigError
from ipost.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the admin user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    get_settings.cache_clear()
    try:
        username = upsert_user(args.username, args.password)
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"admin user saved: {username}")


if __name__ == "__main__":
    main()
