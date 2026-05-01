from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    groq_api_key: str
    sentry_dsn: str = ""
    env: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()