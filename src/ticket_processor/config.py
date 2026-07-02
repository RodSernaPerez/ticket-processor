"""Centralized application settings."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmProvider(StrEnum):
    OPENROUTER = "openrouter"
    GROQ = "groq"


FREE_GROQ_MODELS = {"groq/compound", "groq/compound-mini"}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    gmail_refresh_token: str = Field(..., description="OAuth refresh token for Gmail and Sheets")
    gmail_client_id: str = Field(..., description="Google OAuth client id")
    gmail_client_secret: SecretStr = Field(..., description="Google OAuth client secret")
    gmail_account: str = Field(..., description="Gmail account to monitor")
    gmail_processed_label: str = Field(default="TP_PROCESSED")
    gmail_search_query: str = Field(
        default="has:attachment -label:TP_PROCESSED category:primary",
        description="Gmail query used for polling",
    )
    gmail_poll_interval_seconds: int = Field(default=60, ge=10, le=3600)
    gmail_reply_from_name: str = Field(default="Ticket Processor")

    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: SecretStr = Field(..., description="Supabase service role key")
    supabase_table: str = Field(default="tickets_gastos")

    sheet_id: str = Field(..., description="Google Sheets spreadsheet id")
    sheet_range: str = Field(default="A:I", description="Append range for purchase rows")

    llm_provider: LlmProvider = Field(default=LlmProvider.OPENROUTER)
    llm_model: str = Field(default="openai/gpt-oss-120b:free")
    llm_timeout_seconds: int = Field(default=60, ge=10, le=300)
    llm_temperature: float = Field(default=0.0, ge=0.0, le=1.0)

    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    groq_api_key: SecretStr | None = None
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")
    llm_fallback_provider: LlmProvider | None = Field(default=LlmProvider.GROQ)
    llm_fallback_model: str | None = Field(default="groq/compound-mini")

    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json", description="json or console")
    environment: str = Field(default="development")

    @model_validator(mode="after")
    def validate_llm_configuration(self) -> Settings:
        if self.llm_provider == LlmProvider.OPENROUTER:
            if self.openrouter_api_key is None:
                raise ValueError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")
            if not self.llm_model.endswith(":free"):
                raise ValueError(
                    "OpenRouter primary model must be a free model ending with ':free'"
                )
        elif self.llm_provider == LlmProvider.GROQ:
            if self.groq_api_key is None:
                raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
            if self.llm_model not in FREE_GROQ_MODELS:
                raise ValueError(
                    f"Groq primary model must be one of {sorted(FREE_GROQ_MODELS)}"
                )

        if self.llm_fallback_provider == LlmProvider.OPENROUTER:
            if self.openrouter_api_key is None:
                raise ValueError(
                    "OPENROUTER_API_KEY is required when LLM_FALLBACK_PROVIDER=openrouter"
                )
            if self.llm_fallback_model is None or not self.llm_fallback_model.endswith(":free"):
                raise ValueError("OpenRouter fallback model must end with ':free'")
        elif self.llm_fallback_provider == LlmProvider.GROQ:
            if self.groq_api_key is None:
                raise ValueError("GROQ_API_KEY is required when LLM_FALLBACK_PROVIDER=groq")
            if self.llm_fallback_model not in FREE_GROQ_MODELS:
                raise ValueError(
                    f"Groq fallback model must be one of {sorted(FREE_GROQ_MODELS)}"
                )

        return self


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


def override_settings(settings: Settings | None) -> None:
    """Override cached settings, mainly for tests."""
    global _settings
    _settings = settings
