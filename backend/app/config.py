"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LM Studio connection
    lm_studio_host: str = "localhost"
    lm_studio_port: int = 1234
    model_name: str = "llava-llama-3-8b-v1_1"

    # Session management
    max_history_length: int = 20
    session_ttl_minutes: int = 30
    session_max_count: int = 50

    # Image validation
    image_max_px: int = 2048
    image_min_px: int = 10

    # Inference
    request_timeout_seconds: int = 120
    max_tokens: int = 500

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        protected_namespaces=("settings_",),
    )

    @property
    def lm_studio_base_url(self) -> str:
        return f"http://{self.lm_studio_host}:{self.lm_studio_port}"


settings = Settings()
