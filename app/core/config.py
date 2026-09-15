from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="dev")
    log_level: str = Field(default="INFO")

    google_api_key: str = Field(default="changeme", alias="GOOGLE_API_KEY")
    gemini_text_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_TEXT_MODEL")

    gemini_image_model: str = Field(default="gemini-2.5-flash-image", alias="GEMINI_IMAGE_MODEL")

    gemini_draft_image_model: str = Field(
        default="gemini-3.1-flash-image", alias="GEMINI_DRAFT_IMAGE_MODEL"
    )
    gemini_hero_image_model: str = Field(
        default="gemini-3-pro-image", alias="GEMINI_HERO_IMAGE_MODEL"
    )
    gemini_sheet_image_model: str = Field(
        default="gemini-3-pro-image", alias="GEMINI_SHEET_IMAGE_MODEL"
    )


    critic_pass_threshold: float = Field(default=0.75, alias="CRITIC_PASS_THRESHOLD")
    critic_max_retries: int = Field(default=2, alias="CRITIC_MAX_RETRIES")


    max_ref_images: int = Field(default=14, alias="MAX_REF_IMAGES")
    max_char_refs: int = Field(default=5, alias="MAX_CHAR_REFS")
    max_style_refs: int = Field(default=3, alias="MAX_STYLE_REFS")
    max_prev_frames: int = Field(default=3, alias="MAX_PREV_FRAMES")


    max_pro_calls_per_book: int = Field(default=0, alias="MAX_PRO_CALLS_PER_BOOK")

    database_url: str = Field(
        default="postgresql+asyncpg://comicly:comicly@localhost:5432/comicly",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    s3_endpoint_url: str = Field(default="http://localhost:9000", alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin-change-me-in-prod", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="comicly", alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_public_url: str = Field(default="http://localhost:9000/comicly", alias="S3_PUBLIC_URL")

    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")
    max_upload_mb: int = Field(default=50, alias="MAX_UPLOAD_MB")
    mock_generation: bool = Field(default=False, alias="MOCK_GENERATION")

    auth_secret: str = Field(default="dev-only-change-me", alias="AUTH_SECRET")
    access_token_minutes: int = Field(default=60, alias="ACCESS_TOKEN_MINUTES")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
