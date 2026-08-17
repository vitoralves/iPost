from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "packages").exists():
            return parent
    return Path.cwd()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_repo_root() / ".env", Path.cwd() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    instagram_app_id: str = ""
    instagram_app_secret: str = ""
    instagram_redirect_uri: str = "http://localhost:8000/auth/instagram/callback"
    instagram_api_version: str = "v22.0"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_outbox_bucket: str = "outbox"
    supabase_private_bucket: str = "private"
    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    token_path: str = "data/instagram_token.json"

    @property
    def token_file(self) -> Path:
        path = Path(self.token_path)
        if not path.is_absolute():
            path = _repo_root() / path
        return path

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def instagram_graph_base(self) -> str:
        return f"https://graph.instagram.com/{self.instagram_api_version}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
