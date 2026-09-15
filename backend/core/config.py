from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "mysql+asyncmy://root:123456@localhost:3306/vocab_app?charset=utf8mb4"
    cors_origins: list[str] = ["http://localhost:5173"]
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
