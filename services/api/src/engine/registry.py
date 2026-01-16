"""
Registro de cadenas predefinidas y personalizadas
"""

from typing import Dict, Optional, Type, Callable, Any
from .models import ChainDefinition, ChainConfig
import structlog

logger = structlog.get_logger()


class ChainRegistry:
    """Registro central de cadenas disponibles"""
    
    def __init__(self):
        self._chains: Dict[str, ChainDefinition] = {}
        self._chain_builders: Dict[str, Callable] = {}
    
    def register(
        self,
        chain_id: str,
        definition: ChainDefinition,
        builder: Optional[Callable] = None
    ):
        """Registrar una cadena"""
        self._chains[chain_id] = definition
        if builder:
            self._chain_builders[chain_id] = builder
        logger.info(f"Cadena registrada: {chain_id}", chain_name=definition.name)
    
    def register_builder(self, chain_id: str):
        """Decorador para registrar un builder de cadena"""
        def decorator(func: Callable):
            self._chain_builders[chain_id] = func
            return func
        return decorator
    
    def get(self, chain_id: str) -> Optional[ChainDefinition]:
        """Obtener definición de una cadena"""
        return self._chains.get(chain_id)
    
    def get_builder(self, chain_id: str) -> Optional[Callable]:
        """Obtener el builder de una cadena"""
        return self._chain_builders.get(chain_id)
    
    def list_chains(self) -> list[ChainDefinition]:
        """Listar todas las cadenas registradas"""
        return list(self._chains.values())
    
    def list_chain_ids(self) -> list[str]:
        """Listar IDs de cadenas"""
        return list(self._chains.keys())
    
    def exists(self, chain_id: str) -> bool:
        """Verificar si una cadena existe"""
        return chain_id in self._chains
    
    def unregister(self, chain_id: str) -> bool:
        """Eliminar una cadena del registro"""
        if chain_id in self._chains:
            del self._chains[chain_id]
            if chain_id in self._chain_builders:
                del self._chain_builders[chain_id]
            return True
        return False


# Instancia global del registro
chain_registry = ChainRegistry()
