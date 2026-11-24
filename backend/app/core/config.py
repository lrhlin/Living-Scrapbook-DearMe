from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    sticker_provider: Literal["openai", "bob"] = "openai"
    openai_api_key: str = ""
    openai_key_file: str = str(PROJECT_ROOT / "oaikey.txt")
    openai_image_model: str = "gpt-image-2.6-sunburst"
    openai_image_quality: str = "high"
    openai_timeout_seconds: int = 300
    bob_api_key: str = ""
    bob_key_file: str = str(PROJECT_ROOT / "bobkey.txt")
    bob_cli_path: str = str(PROJECT_ROOT / "tools/node_modules/.bin/bob")
    bob_max_cost: float = 0.5
    bob_max_turns: int = 10
    bob_timeout_seconds: int = 240
    upload_dir: str = str(PROJECT_ROOT / "backend/uploads")
    max_upload_size_mb: int = 20

    model_config = {"env_file": str(PROJECT_ROOT / "backend/.env"), "extra": "ignore"}

    def read_bob_key(self) -> str:
        return self._read_key(self.bob_api_key, self.bob_key_file)

    def read_openai_key(self) -> str:
        return self._read_key(self.openai_api_key, self.openai_key_file)

    @staticmethod
    def _read_key(value: str, filename: str) -> str:
        if value.strip():
            return value.strip()
        try:
            key = Path(filename).read_text().strip()
        except OSError:
            return ""
        return key if "\n" not in key else ""


settings = Settings()
