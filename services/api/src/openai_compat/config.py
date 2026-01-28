"""
Configuration loader for OpenAI-Compatible API

Carga la configuración desde PostgreSQL directamente.
"""

from typing import Optional, List
from dataclasses import dataclass, field
import structlog

from ..db.repositories import ModelConfigRepository

logger = structlog.get_logger()


@dataclass
class BrainModel:
    """Configuración de un modelo Brain"""
    id: str
    name: str
    description: str
    chain_id: str
    max_tokens: int = 4096
    supports_streaming: bool = True
    supports_tools: bool = False


@dataclass 
class BackendLLM:
    """Configuración del LLM backend"""
    provider: str = "ollama"
    url: str = "http://192.168.7.101:11434"
    model: str = "gpt-oss:120b"
    api_key: Optional[str] = None


@dataclass
class RateLimits:
    """Configuración de rate limits"""
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000


@dataclass
class OpenAICompatConfig:
    """Configuración completa de la API OpenAI-compatible"""
    is_enabled: bool = True
    base_url: str = "/v1"
    default_model: str = "brain-adaptive"
    available_models: List[BrainModel] = field(default_factory=list)
    backend_llm: BackendLLM = field(default_factory=BackendLLM)
    rate_limits: RateLimits = field(default_factory=RateLimits)
    logging_enabled: bool = True


class ConfigLoader:
    """Cargador de configuración desde PostgreSQL"""
    
    def __init__(self):
        self._config: Optional[OpenAICompatConfig] = None
        self._default_models = [
            BrainModel(
                id="brain-adaptive",
                name="Brain Adaptive",
                description="Full agent with tools and subagent delegation",
                chain_id="adaptive",
                max_tokens=4096,
                supports_streaming=True,
                supports_tools=True
            ),
            BrainModel(
                id="brain-chat",
                name="Brain Chat", 
                description="Simple conversational chat without tools",
                chain_id="conversational",
                max_tokens=4096,
                supports_streaming=True,
                supports_tools=False
            ),
            BrainModel(
                id="brain-rag",
                name="Brain RAG",
                description="Chat with document retrieval",
                chain_id="rag",
                max_tokens=4096,
                supports_streaming=True,
                supports_tools=False
            )
        ]
    
    async def load_config(self) -> OpenAICompatConfig:
        """Carga configuración desde PostgreSQL"""
        if self._config:
            return self._config
        
        try:
            db_config = await ModelConfigRepository.get()
            
            if not db_config:
                logger.info("Brain model config not found, using defaults")
                self._config = self._get_default_config()
                return self._config
            
            self._config = self._parse_config(db_config)
            logger.info("OpenAI-compat config loaded from database")
            return self._config
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._config = self._get_default_config()
            return self._config
    
    def _parse_config(self, db_config) -> OpenAICompatConfig:
        """Parsea la configuración desde la BD"""
        # Parsear modelos
        models = []
        for m in (db_config.available_models or []):
            models.append(BrainModel(
                id=m.get("id", "brain-adaptive"),
                name=m.get("name", "Brain Model"),
                description=m.get("description", ""),
                chain_id=m.get("chainId", "adaptive"),
                max_tokens=m.get("maxTokens", 4096),
                supports_streaming=m.get("supportsStreaming", True),
                supports_tools=m.get("supportsTools", False)
            ))
        
        if not models:
            models = self._default_models
        
        # Parsear backend LLM
        backend = db_config.backend_llm or {}
        backend_llm = BackendLLM(
            provider=backend.get("provider", "ollama"),
            url=backend.get("url", "http://192.168.7.101:11434"),
            model=backend.get("model", "gpt-oss:120b"),
            api_key=backend.get("apiKey")
        )
        
        # Parsear rate limits
        limits = db_config.rate_limits or {}
        rate_limits = RateLimits(
            requests_per_minute=limits.get("requestsPerMinute", 60),
            tokens_per_minute=limits.get("tokensPerMinute", 100000)
        )
        
        return OpenAICompatConfig(
            is_enabled=db_config.is_enabled,
            base_url=db_config.base_url or "/v1",
            default_model=db_config.default_model or "brain-adaptive",
            available_models=models,
            backend_llm=backend_llm,
            rate_limits=rate_limits,
            logging_enabled=db_config.logging_enabled
        )
    
    def _get_default_config(self) -> OpenAICompatConfig:
        """Retorna configuración por defecto"""
        return OpenAICompatConfig(
            available_models=self._default_models
        )
    
    def get_model(self, model_id: str) -> Optional[BrainModel]:
        """Obtiene un modelo por ID"""
        if not self._config:
            return None
        
        for model in self._config.available_models:
            if model.id == model_id:
                return model
        
        return None
    
    def reload(self):
        """Fuerza recarga de configuración"""
        self._config = None


# Instancia global
config_loader = ConfigLoader()
