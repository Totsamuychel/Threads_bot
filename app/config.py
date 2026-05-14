"""Application configuration and settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Threads Automation"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str
    
    # Database
    database_url: str = "sqlite:///./threads_automation.db"
    
    # LLM Configuration
    llm_provider: str = "ollama"  # ollama, openai, custom
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: Optional[str] = None
    llm_model: str = "llama2"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 500
    llm_timeout: int = 60
    
    # Threads Publisher
    threads_publisher: str = "mock"  # mock, api, browser
    threads_app_id: Optional[str] = None
    threads_app_secret: Optional[str] = None
    threads_redirect_uri: str = "http://localhost:8000/api/accounts/oauth/callback"

    # Browser publisher
    threads_cookies_path: str = "threads_cookies.json"
    browser_headless: bool = False
    browser_login_timeout: int = 60

    # Vision agent (Qwen VL через Ollama)
    vision_model: str = "qwen2.5vl:7b"
    vision_base_url: str = "http://localhost:11434"
    vision_timeout: int = 60
    
    # Post scheduling variance — random ±N minutes added to each scheduled time
    post_time_variance_minutes: int = 10

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"
    content_plan_days_ahead: int = 7
    generation_hours_before: int = 2
    
    # Retry Configuration
    max_retries: int = 3
    retry_delay_seconds: int = 300
    retry_backoff_multiplier: int = 2
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"
    
    # Admin
    admin_username: str = "admin"
    admin_password: str = ""
    # bcrypt hash of admin password — if set, takes priority over admin_password.
    # Generate with: python hash_password.py <password>
    admin_password_hash: Optional[str] = None

    # Telegram notifications
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")


# Global settings instance
settings = Settings()
