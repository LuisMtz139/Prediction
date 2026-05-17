from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "cambia-esto-por-una-clave-muy-segura-en-produccion"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_HOURS: int = 24
    HOST: str = "0.0.0.0"
    PORT: int = 8005
    BASE_URL: str = "http://localhost:8005"

    model_config = {"env_file": ".env"}


settings = Settings()
