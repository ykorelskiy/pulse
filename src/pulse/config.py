"""Pulse configuration loader and validator using Pydantic Settings."""

import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceItem(BaseModel):
    id: str
    name: str
    url: str
    category: str = "general"
    enabled: bool = True



class SourcesConfig(BaseModel):
    sources: list[dict[str, Any]] = Field(default_factory=list)


class EditorialConfig(BaseModel):
    tone: str = "warm_irony"
    forbidden_topics: list[str] = Field(default_factory=list)
    allegory_rules: list[str] = Field(default_factory=list)


class BriefsmithConfig(BaseModel):
    max_top_words: int = 5
    max_top_news: int = 3
    template_style: str = "assisted_author_brief"


class PricingTier(BaseModel):
    id: str
    name: str
    price: Decimal
    resolution: str = "2K"
    delivery_days: int = 2


class PricingConfig(BaseModel):
    currency: str = "RUB"
    tiers: list[PricingTier] = Field(default_factory=list)


class Settings(BaseSettings):
    """Core application environment settings."""

    PULSE_ENV: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

    # Supabase
    SUPABASE_URL: str = Field(
        default="https://placeholder.supabase.co",
        description="Supabase project URL. Obtain from Supabase Dashboard -> Settings -> API",
    )
    SUPABASE_KEY: str = Field(
        default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.placeholder",
        description="Supabase anon key. Obtain from Supabase Dashboard -> Settings -> API",
    )
    SUPABASE_SERVICE_ROLE_KEY: str | None = Field(
        default=None,
        description="Supabase service role key for admin tasks",
    )

    # Storage (R2)
    R2_ENDPOINT_URL: str = Field(
        default="https://placeholder.r2.cloudflarestorage.com",
        description="Cloudflare R2 Endpoint",
    )
    R2_ACCESS_KEY_ID: str = Field(
        default="placeholder_access_key",
        description="Cloudflare R2 Access Key ID",
    )
    R2_SECRET_ACCESS_KEY: str = Field(
        default="placeholder_secret_key",
        description="Cloudflare R2 Secret Access Key",
    )
    R2_BUCKET_NAME: str = Field(
        default="pulse-assets",
        description="Cloudflare R2 Bucket Name",
    )
    R2_PUBLIC_DOMAIN: str = Field(
        default="https://assets.pulse.art",
        description="Public CDN domain for R2 assets",
    )

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = Field(
        default="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
        description="Telegram Bot API Token from @BotFather",
    )
    ADMIN_CHAT_ID: int = Field(
        default=123456789,
        description="Telegram Chat ID for author notifications",
    )

    CHANNEL_CHAT_ID: int | None = Field(
        default=None,
        description="Target public Telegram channel ID",
    )
    DISCUSSION_GROUP_ID: int | None = Field(
        default=None,
        description="Target Telegram discussion group ID",
    )

    TIMEZONE: str = Field(default="Europe/Moscow")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_yaml_config(filepath: Path) -> dict[str, Any]:
    if not filepath.exists():
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ConfigManager:
    """Central configuration manager combining environment and YAML configs."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.cwd()
        self.config_dir = self.base_dir / "config"

        try:
            self.settings = Settings()
        except Exception as e:
            sys.stderr.write(f"\n[CRITICAL CONFIGURATION ERROR]\n{e}\n")
            sys.stderr.write(
                "\nPlease check .env.example to configure required environment variables.\n\n"
            )
            raise

        self.sources = SourcesConfig(**load_yaml_config(self.config_dir / "sources.yaml"))
        self.editorial = EditorialConfig(
            **load_yaml_config(self.config_dir / "editorial.yaml").get("editorial", {})
        )
        self.briefsmith = BriefsmithConfig(
            **load_yaml_config(self.config_dir / "briefsmith.yaml").get("briefsmith", {})
        )
        self.pricing = PricingConfig(
            **load_yaml_config(self.config_dir / "pricing.yaml").get("pricing", {})
        )

    def print_masked_config(self) -> None:
        """Print current configuration with secrets masked."""
        s_key = self.settings.SUPABASE_KEY
        masked_key = f"{s_key[:6]}...{s_key[-4:]}" if len(s_key) >= 10 else "[MASKED]"
        print("==================================================================")
        print(" PULSE CONFIGURATION CHECK")
        print("==================================================================")
        print(f"Environment:       {self.settings.PULSE_ENV}")
        print(f"Log Level:         {self.settings.LOG_LEVEL}")
        print(f"Timezone:          {self.settings.TIMEZONE}")
        print(f"Supabase URL:      {self.settings.SUPABASE_URL}")
        print(f"Supabase Key:      {masked_key}")

        print(f"R2 Endpoint:       {self.settings.R2_ENDPOINT_URL}")
        print(f"R2 Bucket:         {self.settings.R2_BUCKET_NAME}")
        print(f"Telegram Bot Token: {self.settings.TELEGRAM_BOT_TOKEN[:8]}...[MASKED]")
        print(f"Admin Chat ID:     {self.settings.ADMIN_CHAT_ID}")
        print(f"Sources Count:     {len(self.sources.sources)}")
        print(f"Pricing Tiers:     {len(self.pricing.tiers)}")
        print("==================================================================")
        print(" Status: OK")
        print("==================================================================")


def get_config() -> ConfigManager:
    return ConfigManager()


def main() -> None:
    if "--check" in sys.argv:
        try:
            cfg = ConfigManager()
            cfg.print_masked_config()
            sys.exit(0)
        except Exception:
            sys.exit(1)
    else:
        print("Usage: python -m pulse.config --check")


if __name__ == "__main__":
    main()
