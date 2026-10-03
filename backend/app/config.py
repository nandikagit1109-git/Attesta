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
    app_name: str = "Attesta"
    environment: str = "development"
    # >=32 bytes; set SECRET_KEY in production.
    secret_key: str = "dev-only-secret-change-me-3f9a2c7e51d84b06a1f4"
    database_url: str = "sqlite:///./attesta.db"
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
    # Shared config written by blockchain/scripts/deploy.ts (fallback for
    # contract_address). Relative to the repo root.
    chain_config_path: str = "../data/chain.json"
    # Contract ABI from the Hardhat build (relative to the repo root).
    chain_abi_path: str = (
        "../blockchain/artifacts/contracts/"
        "VerifiableCredentialRegistry.sol/VerifiableCredentialRegistry.json"
    )
    # Demo-ONLY issuer signing key. The default is Hardhat's well-known test
    # account #0 (public, worthless outside the local node). Override with a
    # funded testnet key only for Sepolia.
    demo_issuer_private_key: str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

    # Repo root is used to resolve chain_config_path / chain_abi_path and to
    # locate the blockchain package for auto-start/auto-deploy.
    repo_root: str = ".."

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Demo-mode wildcard for hosted previews (JWT travels in the
        # Authorization header, never cookies). Wildcard + credentials is
        # invalid per the CORS spec, so credentials are disabled then.
        return ["*"] if origins == ["*"] else origins

    @property
    def allowed_extension_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_base_url and self.llm_model and self.llm_api_key)

    def resolve(self, rel_path: str) -> str:
        """Resolve a repo-relative path against the repo root."""
        import os

        return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", rel_path))


@lru_cache
def get_settings() -> Settings:
    return Settings()
