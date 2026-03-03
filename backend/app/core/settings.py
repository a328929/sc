from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AppSection(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    auth_token: str = "change-this-token"


class TelegramSection(BaseModel):
    api_id: int = 0
    api_hash: str = ""
    target_channel: str = ""
    session_file: str = "my_session.session"


class UploadSection(BaseModel):
    concurrency: int = 3
    retry_max: int = 5
    retry_backoff_seconds: int = 2
    progress_tick_ms: int = 300
    uploads_dir: str = "./data/uploads"


class DatabaseSection(BaseModel):
    path: str = "./data/uploader.db"


class LoggingSection(BaseModel):
    path: str = "./data/uploader.log"
    level: str = "INFO"


class Settings(BaseModel):
    app: AppSection = Field(default_factory=AppSection)
    telegram: TelegramSection = Field(default_factory=TelegramSection)
    upload: UploadSection = Field(default_factory=UploadSection)
    database: DatabaseSection = Field(default_factory=DatabaseSection)
    logging: LoggingSection = Field(default_factory=LoggingSection)


def _candidate_paths(config_path: str | None) -> list[Path]:
    if config_path:
        return [Path(config_path)]

    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    return [
        Path("config/app.yaml"),
        Path("config/app.example.yaml"),
        repo_root / "config/app.yaml",
        repo_root / "config/app.example.yaml",
    ]


def load_settings(config_path: str | None = None) -> Settings:
    for candidate in _candidate_paths(config_path):
        if candidate.exists():
            return Settings(**yaml.safe_load(candidate.read_text(encoding="utf-8")))
    raise FileNotFoundError("未找到配置文件: config/app.yaml 或 config/app.example.yaml")
