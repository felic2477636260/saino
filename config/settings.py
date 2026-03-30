from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Saino"
    database_path: Path = Field(default=BASE_DIR / "db" / "saino.db", alias="DATABASE_PATH")
    data_raw_dir: Path = Field(default=BASE_DIR / "data" / "raw", alias="DATA_RAW_DIR")
    ark_api_key: str = Field(default="", alias="ARK_API_KEY")
    ark_base_url: str = Field(default="https://ark.cn-beijing.volces.com/api/v3", alias="ARK_BASE_URL")
    model_name: str = Field(default="doubao-seed-2-0-pro-260215", alias="MODEL_NAME")
    ark_timeout_seconds: int = Field(default=30, alias="ARK_TIMEOUT_SECONDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
