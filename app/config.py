from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Values here can be overridden by environment variables or a .env file.
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    google_credentials_file: str = "credentials.json"
    google_token_file: str = "token.json"
    gmail_query: str = "newer_than:30d (has:attachment OR http)"
    gmail_max_results: int = 50

    database_url: str = "sqlite:///data/email_research.db"
    chroma_path: str = "data/chroma"
    attachment_dir: str = "data/attachments"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def sqlite_path(self) -> Path:
        # The app stores summaries in SQLite. This converts sqlite:///data/file.db
        # into the actual filesystem path data/file.db.
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("This prototype expects DATABASE_URL to start with sqlite:///")
        return Path(self.database_url.replace("sqlite:///", "", 1))


@lru_cache
def get_settings() -> Settings:
    # lru_cache means Settings is created once and reused.
    settings = Settings()

    # Create local data folders before the rest of the app tries to use them.
    Path(settings.attachment_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
