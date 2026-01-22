"""
Configuración de la aplicación Brain API
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración principal de la aplicación"""
    
    # App
    app_name: str = "Brain API"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # Database
    database_url: str = "postgresql://brain:brain_secret@localhost:5432/brain_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Ollama (LLM externo)
    # Por defecto usa host.docker.internal para acceder al Ollama del host desde Docker
    ollama_base_url: str = "http://host.docker.internal:11434"
    default_model: str = "llama3.2"
    default_embedding_model: str = "nomic-embed-text"
    
    # Vector Store
    vector_collection_name: str = "brain_documents"
    vector_embedding_dimensions: int = 768
    
    # CORS - Lista de orígenes permitidos (separados por comas en env var)
    cors_origins: list[str] = ["http://localhost:4200", "http://localhost:1337"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Obtener configuración cacheada"""
    return Settings()
