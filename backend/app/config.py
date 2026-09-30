"""Application settings loaded from environment / backend/.env.

Never hardcode secrets. See ../../.env.example for the full template.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core
    app_name: str = "TrustPass"
    environment: str = "development"
    secret_key: str = "dev-only-secret-change-me"
    database_url: str = "sqlite:///./trustpass.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Auth
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12h demo-friendly

    # Uploads
    uploads_dir: str = "uploads"
    max_upload_mb: int = 10
    allowed_extensions: str = ".pdf,.png,.jpg,.jpeg"

    # LLM (OpenAI-compatible). Empty -> deterministic fallback only.
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""

    # Extraction
    tesseract_cmd: str = ""

    # Blockchain
    chain_rpc_url: str = "http://127.0.0.1:8545"
    chain_id: int = 31337
    contract_address: str = ""
    deployer_private_key: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Demo-mode wildcard for hosted previews (JWT travels in the Authorization
        # header, never cookies). Tighten to explicit origins for real use.
        return ["*"] if origins == ["*"] else origins

    @property
    def allowed_extension_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_model and self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
