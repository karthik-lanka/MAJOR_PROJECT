"""
Core configuration module.
Loads and validates all environment variables using Pydantic Settings.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Gemini AI ---
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001", description="Embedding model identifier"
    )
    gemini_generation_model: str = Field(
        default="gemini-3.5-flash-lite", description="Generation model identifier"
    )
    embedding_dimension: int = Field(
        default=768, description="Embedding vector dimensionality"
    )

    # --- Pinecone ---
    pinecone_api_key: str = Field(..., description="Pinecone API key")
    pinecone_index_name: str = Field(
        default="study-assistant", description="Pinecone index name"
    )
    pinecone_namespace: str = Field(
        default="default", description="Pinecone namespace"
    )

    # --- Document Processing ---
    max_upload_size_mb: int = Field(
        default=25, description="Maximum upload file size in MB"
    )
    chunk_size_tokens: int = Field(
        default=600, description="Target chunk size in tokens"
    )
    chunk_overlap_tokens: int = Field(
        default=80, description="Chunk overlap in tokens"
    )

    # --- Retrieval ---
    retrieval_top_k: int = Field(
        default=10, description="Number of candidate chunks to retrieve"
    )
    final_context_top_k: int = Field(
        default=5, description="Number of chunks to send to LLM"
    )
    similarity_threshold: float = Field(
        default=0.5, description="Minimum similarity score for retrieval"
    )

    # --- Web Search (Optional) ---
    web_search_provider: Optional[str] = Field(
        default=None, description="Web search provider (e.g., 'google')"
    )
    web_search_api_key: Optional[str] = Field(
        default=None, description="Web search API key"
    )
    google_cse_id: Optional[str] = Field(
        default=None, description="Google Custom Search Engine ID"
    )

    # --- Application ---
    app_env: str = Field(default="development", description="Application environment")
    app_host: str = Field(default="0.0.0.0", description="Application host")
    app_port: int = Field(default=8000, description="Application port")
    frontend_url: str = Field(
        default="http://localhost:5173", description="Frontend URL for CORS"
    )
    log_level: str = Field(default="INFO", description="Logging level")

    # --- Derived Paths ---
    @property
    def upload_dir(self) -> Path:
        path = Path(__file__).resolve().parent.parent.parent / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def data_dir(self) -> Path:
        path = Path(__file__).resolve().parent.parent.parent / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def database_url(self) -> str:
        db_path = self.data_dir / "study_assistant.db"
        return f"sqlite+aiosqlite:///{db_path}"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        if not v or v == "your_gemini_api_key_here":
            raise ValueError(
                "GEMINI_API_KEY is required. Get one at https://aistudio.google.com/apikey"
            )
        return v

    @field_validator("pinecone_api_key")
    @classmethod
    def validate_pinecone_key(cls, v: str) -> str:
        if not v or v == "your_pinecone_api_key_here":
            raise ValueError(
                "PINECONE_API_KEY is required. Get one at https://www.pinecone.io/"
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
