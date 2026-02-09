"""
Tool Configuration Schemas

Define la estructura estándar para herramientas configurables.
Permite al frontend renderizar dinámicamente los campos de configuración.
"""

from .base import (
    ConfigFieldSchema,
    ToolConfigurableSchema,
    ConfigFieldType,
    VisibilityCondition,
    ValidationRule
)
from .registry import configurable_tools_registry, get_all_configurable_schemas

__all__ = [
    "ConfigFieldSchema",
    "ToolConfigurableSchema", 
    "ConfigFieldType",
    "VisibilityCondition",
    "ValidationRule",
    "configurable_tools_registry",
    "get_all_configurable_schemas"
]
