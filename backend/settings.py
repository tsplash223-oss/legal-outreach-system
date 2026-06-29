import logging
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development").strip().lower()
        self.jwt_secret = os.getenv("JWT_SECRET", "").strip()
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256").strip() or "HS256"
        self.jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "720") or 720)
        self.admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "").split(",")
            if origin.strip()
        ]
        # Railway variables for Gmail API JSON values:
        # Drivers Ed profile: GREENLIGHT_GMAIL_CREDENTIALS_JSON / GREENLIGHT_GMAIL_TOKEN_JSON.
        # Hope Foundation profile: HOPE_GMAIL_CREDENTIALS_JSON / HOPE_GMAIL_TOKEN_JSON.
        # Legacy fallback for the Drivers Ed profile remains GMAIL_CREDENTIALS_JSON / GMAIL_TOKEN_JSON.
        self.greenlight_gmail_credentials_json_present = bool(os.getenv("GREENLIGHT_GMAIL_CREDENTIALS_JSON", "").strip())
        self.greenlight_gmail_token_json_present = bool(os.getenv("GREENLIGHT_GMAIL_TOKEN_JSON", "").strip())
        self.hope_gmail_credentials_json_present = bool(os.getenv("HOPE_GMAIL_CREDENTIALS_JSON", "").strip())
        self.hope_gmail_token_json_present = bool(os.getenv("HOPE_GMAIL_TOKEN_JSON", "").strip())

    @property
    def is_production(self):
        return self.environment == "production"

    def validate(self):
        errors = []

        if not self.jwt_secret:
            errors.append("JWT_SECRET is required.")
        elif len(self.jwt_secret) < 32:
            errors.append("JWT_SECRET must be at least 32 characters.")

        if self.is_production and (not self.admin_email or not self.admin_password):
            errors.append("ADMIN_EMAIL and ADMIN_PASSWORD are required for production bootstrap.")

        if errors and self.is_production:
            raise RuntimeError("Invalid production configuration: " + " ".join(errors))

        for error in errors:
            logger.warning("Configuration warning: %s", error)


@lru_cache
def get_settings():
    return Settings()
