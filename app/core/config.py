from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Holding Control Plane"
    environment: str = "production"
    database_url: str = "postgresql+psycopg://holding:holding@localhost:5432/holding"
    api_prefix: str = "/api/v1"
    require_actor_header: bool = True


settings = Settings()
