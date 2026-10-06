from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Holding Control Plane"
    environment: str = "production"
    database_url: str = "postgresql+psycopg://holding:holding@localhost:5432/holding"
    api_prefix: str = "/api/v1"
    require_verified_identity: bool = True
    verified_identity_audience: str = "holding-control-plane"

    # AgentOS is introduced behind a fail-closed migration switch. Production
    # enablement requires an AgentOS authentication source and its own acceptance gate.
    agentos_enabled: bool = False
    agentos_scheduler_enabled: bool = True
    agentos_durable_queue_enabled: bool = True
    agentos_db_schema: str = "agentos"

    obsidian_vault_path: str | None = None
    # Compatibility name retained during migration. This location is an intake
    # queue owned by the external Second Brain, never a canonical Holding store.
    obsidian_knowledge_root: str = "00 - Segundo Cerebro/00 - Inbox/Holding"


settings = Settings()
