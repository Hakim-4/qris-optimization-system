from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "QRIS Optimization Backend"
    database_url: str = "postgresql://qris:qris_password@postgres:5432/qris_db"
    redis_url: str = "redis://redis:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    class Config:
        env_file = ".env"


settings = Settings()
