from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
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
        populate_by_name=True,
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
    bedrock_model_id: str = "us.amazon.nova-pro-v1:0"
    bedrock_region: str = "us-west-2"
    bedrock_image_model_id: str = Field(
        default="stability.sd3-5-large-v1:0",
        validation_alias=AliasChoices("BEDROCK_IMAGE_MODEL_ID", "BEDROCK_CANVAS_MODEL_ID"),
    )
    openai_api_key: str = ""
    openai_image_model_id: str = "gpt-image-2"
    ipost_mock_bedrock: bool = False
    supabase_db_url: str = ""
    supabase_db_region: str = "sa-east-1"
    critic_pass_score: float = 7.0
    max_attempts: int = 3
    alert_email: str = "email@gmail.com"
    resend_api_key: str = ""
    resend_from: str = "iPost <onboarding@resend.dev>"

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
