import os
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Core application settings
    APP_NAME: str = "BHIV Central Payment Service"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./payments.db")

    # Payment Provider configuration
    PAYMENT_PROVIDER: str = "razorpay"
    RAZORPAY_KEY_ID: str = Field(default="")
    RAZORPAY_KEY_SECRET: str = Field(default="")
    RAZORPAY_WEBHOOK_SECRET: str = Field(default="")

    # Master administrative API key
    ADMIN_API_KEY: str = Field(default="bhiv_admin_dev_secret_key_2026")

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    def validate_production_guards(self) -> None:
        """Enforces critical security guards before starting in production."""
        if self.is_production:
            if not self.RAZORPAY_KEY_ID.startswith("rzp_live_"):
                raise ValueError(
                    "Production safety violation: APP_ENV is 'production' but RAZORPAY_KEY_ID "
                    "does not start with 'rzp_live_'. Live transactions require approved live credentials."
                )
            if not self.RAZORPAY_KEY_SECRET or len(self.RAZORPAY_KEY_SECRET) < 16:
                raise ValueError(
                    "Production safety violation: Valid RAZORPAY_KEY_SECRET is mandatory in production."
                )
            if not self.RAZORPAY_WEBHOOK_SECRET:
                raise ValueError(
                    "Production safety violation: RAZORPAY_WEBHOOK_SECRET is mandatory in production."
                )
            if self.ADMIN_API_KEY == "bhiv_admin_dev_secret_key_2026":
                raise ValueError(
                    "Production safety violation: Default ADMIN_API_KEY cannot be used in production."
                )
            if self.is_sqlite:
                raise ValueError(
                    "Production safety violation: SQLite is not permitted for durable production records. "
                    "Configure a production PostgreSQL instance via DATABASE_URL."
                )


settings = Settings()
# Execute runtime safety validation
settings.validate_production_guards()
