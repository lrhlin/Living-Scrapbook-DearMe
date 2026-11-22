from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 20

    model_config = {"env_file": ".env"}


settings = Settings()
