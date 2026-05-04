"""Configuration loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pureservice MCP configuration.

    All settings can be provided via environment variables with the
    `PURESERVICE_` prefix, e.g. PURESERVICE_TENANT=vanylven
    """

    model_config = SettingsConfigDict(
        env_prefix="PURESERVICE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # The subdomain of your Pureservice instance: <tenant>.pureservice.com
    tenant: str

    # API key from Pureservice → Administration → Security → API keys
    api_key: str

    # Rate limit: docs state 100/min for SaaS. We stay under it.
    requests_per_minute: int = 90

    # Default page size when listing entities (API max is 500)
    default_page_size: int = 100

    # HTTP timeout in seconds
    timeout_seconds: float = 30.0

    # If true, write tools (create/update/assign) are NOT exposed.
    # Default true so a fresh deploy is safe; set to false to enable writes.
    read_only: bool = True

    # API base path. Standard er /agent/api for agent-API-nøklar.
    # Bruk /api for offentleg API om instansen din støttar det.
    api_base_path: str = "/agent/api"

    # Optional gateway token: if set, incoming HTTP requests must include
    # the matching value in the X-MCP-Auth header (or whatever header name
    # the upstream client uses). Leave empty to disable auth (NOT recommended
    # for production deploys).
    gateway_token: str = ""

    @property
    def base_url(self) -> str:
        return f"https://{self.tenant}.pureservice.com{self.api_base_path}"


settings = Settings()  # type: ignore[call-arg]
