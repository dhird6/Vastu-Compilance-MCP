from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Vastu Compliance MCP Server", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    aps_client_id: str = Field(default="", alias="APS_CLIENT_ID")
    aps_client_secret: str = Field(default="", alias="APS_CLIENT_SECRET")
    aps_auth_url: str = Field(default="https://developer.api.autodesk.com/authentication/v2/token", alias="APS_AUTH_URL")
    aps_api_base_url: str = Field(default="https://developer.api.autodesk.com", alias="APS_API_BASE_URL")

    rules_path: str = Field(default="config/vastu_rules.yaml", alias="RULES_PATH")
    vedic_knowledge_path: str = Field(default="config/vedic_knowledge.yaml", alias="VEDIC_KNOWLEDGE_PATH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    plugin_paths: str = Field(default="", alias="PLUGIN_PATHS")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    report_company_name: str = Field(default="Vastu Compliance", alias="REPORT_COMPANY_NAME")
    report_company_tagline: str = Field(
        default="Professional Vastu Analysis Platform",
        alias="REPORT_COMPANY_TAGLINE",
    )
    report_company_website: str = Field(default="https://vastu-compliance.local", alias="REPORT_COMPANY_WEBSITE")
    report_logo_path: str = Field(default="", alias="REPORT_LOGO_PATH")

    database_url: str = Field(
        default="",
        alias="DATABASE_URL",
        description="postgresql+asyncpg://user:pass@host:5432/vastu (optional)",
    )

    @property
    def resolved_rules_path(self) -> Path:
        return Path(self.rules_path).resolve()

    @property
    def resolved_vedic_knowledge_path(self) -> Path:
        return Path(self.vedic_knowledge_path).resolve()

    @property
    def enabled_plugin_paths(self) -> list[str]:
        if not self.plugin_paths.strip():
            return []
        return [item.strip() for item in self.plugin_paths.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
