"""
Configurable Tools Registry

Centraliza todos los schemas de herramientas configurables.
Proporciona métodos para obtener schemas individuales o todos a la vez.
"""

from typing import Dict, List, Optional
import structlog

from .base import ToolConfigurableSchema
from .generate_image import GENERATE_IMAGE_SCHEMA
from .generate_video import GENERATE_VIDEO_SCHEMA
from .web_search import WEB_SEARCH_SCHEMA
from .analyze_image import ANALYZE_IMAGE_SCHEMA
from .execution import (
    PYTHON_EXEC_SCHEMA,
    JAVASCRIPT_EXEC_SCHEMA,
    SHELL_EXEC_SCHEMA
)

logger = structlog.get_logger()


class ConfigurableToolsRegistry:
    """
    Registry de herramientas configurables.
    
    Almacena y proporciona acceso a los schemas de configuración
    de todas las herramientas configurables del sistema.
    """
    
    def __init__(self):
        self._schemas: Dict[str, ToolConfigurableSchema] = {}
        self._register_defaults()
    
    def _register_defaults(self):
        """Registra los schemas por defecto"""
        # Media tools
        self.register(GENERATE_IMAGE_SCHEMA)
        self.register(GENERATE_VIDEO_SCHEMA)
        self.register(ANALYZE_IMAGE_SCHEMA)
        
        # Web tools
        self.register(WEB_SEARCH_SCHEMA)
        
        # Execution tools (admin only)
        self.register(PYTHON_EXEC_SCHEMA)
        self.register(JAVASCRIPT_EXEC_SCHEMA)
        self.register(SHELL_EXEC_SCHEMA)
        
        logger.info(f"📋 ConfigurableToolsRegistry initialized with {len(self._schemas)} tools")
    
    def register(self, schema: ToolConfigurableSchema) -> None:
        """Registra un schema de herramienta"""
        self._schemas[schema.id] = schema
        logger.debug(f"Registered configurable tool schema: {schema.id}")
    
    def get(self, tool_id: str) -> Optional[ToolConfigurableSchema]:
        """Obtiene el schema de una herramienta por ID"""
        return self._schemas.get(tool_id)
    
    def get_all(self, include_admin: bool = False) -> List[ToolConfigurableSchema]:
        """
        Obtiene todos los schemas.
        
        Args:
            include_admin: Si True, incluye herramientas admin_only
            
        Returns:
            Lista de schemas
        """
        if include_admin:
            return list(self._schemas.values())
        
        return [s for s in self._schemas.values() if not s.admin_only]
    
    def get_by_category(self, category: str, include_admin: bool = False) -> List[ToolConfigurableSchema]:
        """
        Obtiene schemas filtrados por categoría.
        
        Args:
            category: Categoría a filtrar (media, web, execution, ai, filesystem)
            include_admin: Si True, incluye herramientas admin_only
            
        Returns:
            Lista de schemas de la categoría
        """
        schemas = self.get_all(include_admin)
        return [s for s in schemas if s.category == category]
    
    def list_ids(self, include_admin: bool = False) -> List[str]:
        """Lista los IDs de todas las herramientas configurables"""
        schemas = self.get_all(include_admin)
        return [s.id for s in schemas]
    
    def to_dict_list(self, include_admin: bool = False) -> List[Dict]:
        """
        Convierte todos los schemas a lista de dicts para serialización.
        
        Args:
            include_admin: Si True, incluye herramientas admin_only
            
        Returns:
            Lista de dicts con todos los schemas
        """
        schemas = self.get_all(include_admin)
        return [s.to_dict() for s in schemas]
    
    def get_categories(self) -> List[str]:
        """Obtiene lista de categorías únicas"""
        categories = set(s.category for s in self._schemas.values())
        return sorted(list(categories))


# Instancia global del registry
configurable_tools_registry = ConfigurableToolsRegistry()


def get_all_configurable_schemas(include_admin: bool = False) -> List[ToolConfigurableSchema]:
    """Helper function para obtener todos los schemas"""
    return configurable_tools_registry.get_all(include_admin)


def get_configurable_schema(tool_id: str) -> Optional[ToolConfigurableSchema]:
    """Helper function para obtener un schema específico"""
    return configurable_tools_registry.get(tool_id)
