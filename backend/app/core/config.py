from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "The World's Take"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/worldstake"

    # Gemini AI
    gemini_api_key: str = ""
    gemini_embedding_model: str = "models/text-embedding-004"
    gemini_model: str = "models/gemini-2.0-flash"

    # Embedding dimensions (Gemini text-embedding-004 outputs 768)
    embedding_dimensions: int = 768

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
