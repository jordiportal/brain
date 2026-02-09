"""
Base classes for Tool Configuration Schemas

Define las estructuras estándar para describir la configuración
de herramientas de forma que el frontend pueda renderizar
dinámicamente los campos de configuración.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ConfigFieldType(str, Enum):
    """Tipos de campo soportados en la UI de configuración"""
    TEXT = "text"
    SELECT = "select"
    MULTISELECT = "multiselect"
    NUMBER = "number"
    BOOLEAN = "boolean"
    PASSWORD = "password"
    TEXT_ARRAY = "text_array"


@dataclass
class VisibilityCondition:
    """
    Condición para mostrar/ocultar un campo.
    
    Ejemplos:
        - {"field": "provider", "value": "gemini"}  -> visible si provider == gemini
        - {"field": "provider", "values": ["tavily", "serper"]}  -> visible si provider en lista
        - {"field": "provider", "not_value": "duckduckgo"}  -> visible si provider != duckduckgo
    """
    field: str
    value: Optional[str] = None
    values: Optional[List[str]] = None
    not_value: Optional[str] = None
    not_values: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"field": self.field}
        if self.value is not None:
            result["value"] = self.value
        if self.values is not None:
            result["values"] = self.values
        if self.not_value is not None:
            result["not_value"] = self.not_value
        if self.not_values is not None:
            result["not_values"] = self.not_values
        return result


@dataclass
class ValidationRule:
    """
    Regla de validación para un campo.
    
    Ejemplos:
        - {"min": 1, "max": 100}  -> número entre 1 y 100
        - {"pattern": "^[a-z]+$"}  -> regex
        - {"min_length": 3, "max_length": 50}  -> longitud de texto
    """
    min: Optional[float] = None
    max: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    pattern_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.min is not None:
            result["min"] = self.min
        if self.max is not None:
            result["max"] = self.max
        if self.min_length is not None:
            result["min_length"] = self.min_length
        if self.max_length is not None:
            result["max_length"] = self.max_length
        if self.pattern is not None:
            result["pattern"] = self.pattern
        if self.pattern_message is not None:
            result["pattern_message"] = self.pattern_message
        return result


@dataclass
class SelectOption:
    """Opción para campos select/multiselect"""
    value: str
    label: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"value": self.value, "label": self.label}


@dataclass
class ConfigFieldSchema:
    """
    Schema de un campo de configuración.
    
    Describe cómo renderizar y validar un campo en la UI de configuración.
    
    Attributes:
        key: Identificador único del campo (usado como key en el dict de config)
        label: Etiqueta visible en la UI
        type: Tipo de campo (text, select, number, boolean, password, etc.)
        
        options: Lista de opciones para select/multiselect
        options_depend_on: Key del campo del que dependen las opciones dinámicas
        dynamic_options: Dict de opciones indexadas por valor del campo padre
        
        default: Valor por defecto
        hint: Texto de ayuda mostrado bajo el campo
        placeholder: Placeholder para inputs de texto
        
        required: Si el campo es obligatorio
        visible_when: Condición para mostrar/ocultar el campo
        validation: Reglas de validación
        
        group: Nombre del grupo/sección (para agrupar campos relacionados)
        admin_only: Si solo admins pueden ver/editar este campo
        order: Orden de aparición (menor = primero)
    """
    key: str
    label: str
    type: ConfigFieldType
    
    # Opciones para select/multiselect
    options: Optional[List[SelectOption]] = None
    options_depend_on: Optional[str] = None
    dynamic_options: Optional[Dict[str, List[SelectOption]]] = None
    
    # Valores y ayuda
    default: Any = None
    hint: Optional[str] = None
    placeholder: Optional[str] = None
    
    # Validación y visibilidad
    required: bool = False
    visible_when: Optional[VisibilityCondition] = None
    validation: Optional[ValidationRule] = None
    
    # Organización
    group: Optional[str] = None
    admin_only: bool = False
    order: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict para serialización JSON"""
        result = {
            "key": self.key,
            "label": self.label,
            "type": self.type.value if isinstance(self.type, ConfigFieldType) else self.type,
        }
        
        # Opciones
        if self.options:
            result["options"] = [opt.to_dict() if hasattr(opt, 'to_dict') else opt for opt in self.options]
        if self.options_depend_on:
            result["options_depend_on"] = self.options_depend_on
        if self.dynamic_options:
            result["dynamic_options"] = {
                k: [opt.to_dict() if hasattr(opt, 'to_dict') else opt for opt in v]
                for k, v in self.dynamic_options.items()
            }
        
        # Valores
        if self.default is not None:
            result["default"] = self.default
        if self.hint:
            result["hint"] = self.hint
        if self.placeholder:
            result["placeholder"] = self.placeholder
        
        # Validación
        result["required"] = self.required
        if self.visible_when:
            result["visible_when"] = self.visible_when.to_dict() if hasattr(self.visible_when, 'to_dict') else self.visible_when
        if self.validation:
            result["validation"] = self.validation.to_dict() if hasattr(self.validation, 'to_dict') else self.validation
        
        # Organización
        if self.group:
            result["group"] = self.group
        result["admin_only"] = self.admin_only
        result["order"] = self.order
        
        return result


@dataclass
class ToolConfigurableSchema:
    """
    Schema completo para una herramienta configurable.
    
    Define toda la información necesaria para que el frontend
    pueda renderizar dinámicamente la UI de configuración.
    
    Attributes:
        id: ID de la herramienta (debe coincidir con el ID en tool_registry)
        display_name: Nombre legible para mostrar en la UI
        description: Descripción de la herramienta
        icon: Nombre del icono Material (ej: "image", "search", "code")
        category: Categoría (media, web, execution, filesystem, ai)
        
        config_schema: Lista de campos de configuración
        default_config: Valores por defecto para la configuración
        
        requires_api_key: Si necesita API key de algún proveedor
        supported_providers: Lista de proveedores soportados (si aplica)
        
        admin_only: Si toda la herramienta es solo para admins
        enabled_by_default: Si está habilitada por defecto
    """
    id: str
    display_name: str
    description: str
    icon: str
    category: str
    
    config_schema: List[ConfigFieldSchema]
    default_config: Dict[str, Any]
    
    requires_api_key: bool = False
    supported_providers: Optional[List[str]] = None
    
    admin_only: bool = False
    enabled_by_default: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a dict para serialización JSON"""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "config_schema": [f.to_dict() for f in self.config_schema],
            "default_config": self.default_config,
            "requires_api_key": self.requires_api_key,
            "supported_providers": self.supported_providers,
            "admin_only": self.admin_only,
            "enabled_by_default": self.enabled_by_default
        }
    
    def get_field(self, key: str) -> Optional[ConfigFieldSchema]:
        """Obtiene un campo por su key"""
        for field in self.config_schema:
            if field.key == key:
                return field
        return None
    
    def get_fields_by_group(self) -> Dict[str, List[ConfigFieldSchema]]:
        """Agrupa campos por grupo/sección"""
        groups: Dict[str, List[ConfigFieldSchema]] = {}
        for field in sorted(self.config_schema, key=lambda f: f.order):
            group_name = field.group or "General"
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(field)
        return groups
