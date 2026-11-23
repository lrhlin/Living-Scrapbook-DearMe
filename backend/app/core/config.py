from pathlib import Path

from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
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
        if self.bob_api_key.strip():
            return self.bob_api_key.strip()
        try:
            key = Path(self.bob_key_file).read_text().strip()
        except OSError:
            return ""
        return key if "\n" not in key else ""


settings = Settings()
