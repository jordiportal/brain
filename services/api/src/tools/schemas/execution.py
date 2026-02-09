"""
Configuration Schemas for execution tools (shell, python, javascript)

Estas herramientas tienen configuración de seguridad y recursos.
La mayoría de campos son admin_only.
"""

from .base import (
    ToolConfigurableSchema,
    ConfigFieldSchema,
    ConfigFieldType,
    SelectOption,
    ValidationRule,
)


# ============================================
# Python Execution
# ============================================

PYTHON_EXEC_SCHEMA = ToolConfigurableSchema(
    id="python",
    display_name="Ejecución Python",
    description="Ejecuta código Python en contenedor Docker con paquetes científicos",
    icon="code",
    category="execution",
    admin_only=True,
    
    config_schema=[
        ConfigFieldSchema(
            key="enabled",
            label="Habilitado",
            type=ConfigFieldType.BOOLEAN,
            default=True,
            hint="Habilita o deshabilita la ejecución de Python",
            admin_only=True,
            order=1
        ),
        
        ConfigFieldSchema(
            key="image",
            label="Imagen Docker",
            type=ConfigFieldType.TEXT,
            default="brain-python:science",
            hint="Imagen Docker a usar. brain-python:science incluye numpy, pandas, matplotlib, etc.",
            placeholder="python:3.11-slim",
            admin_only=True,
            group="Docker",
            order=10
        ),
        
        ConfigFieldSchema(
            key="memory_limit",
            label="Límite de memoria",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("256m", "256 MB"),
                SelectOption("512m", "512 MB"),
                SelectOption("1g", "1 GB"),
                SelectOption("2g", "2 GB"),
                SelectOption("4g", "4 GB")
            ],
            default="1g",
            hint="Memoria máxima que puede usar el contenedor",
            admin_only=True,
            group="Recursos",
            order=20
        ),
        
        ConfigFieldSchema(
            key="cpu_limit",
            label="Límite de CPU",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("0.5", "0.5 cores"),
                SelectOption("1.0", "1 core"),
                SelectOption("2.0", "2 cores"),
                SelectOption("4.0", "4 cores")
            ],
            default="2.0",
            hint="Número máximo de CPU cores",
            admin_only=True,
            group="Recursos",
            order=21
        ),
        
        ConfigFieldSchema(
            key="timeout",
            label="Timeout (segundos)",
            type=ConfigFieldType.NUMBER,
            default=60,
            validation=ValidationRule(min=10, max=300),
            hint="Tiempo máximo de ejecución (10-300 segundos)",
            admin_only=True,
            group="Recursos",
            order=22
        ),
        
        ConfigFieldSchema(
            key="network_enabled",
            label="Permitir red",
            type=ConfigFieldType.BOOLEAN,
            default=False,
            hint="Permite acceso a internet desde el contenedor. CUIDADO: riesgo de seguridad",
            admin_only=True,
            group="Seguridad",
            order=30
        ),
    ],
    
    default_config={
        "enabled": True,
        "image": "brain-python:science",
        "memory_limit": "1g",
        "cpu_limit": "2.0",
        "timeout": 60,
        "network_enabled": False
    }
)


# ============================================
# JavaScript Execution
# ============================================

JAVASCRIPT_EXEC_SCHEMA = ToolConfigurableSchema(
    id="javascript",
    display_name="Ejecución JavaScript",
    description="Ejecuta código JavaScript/Node.js en contenedor Docker",
    icon="javascript",
    category="execution",
    admin_only=True,
    
    config_schema=[
        ConfigFieldSchema(
            key="enabled",
            label="Habilitado",
            type=ConfigFieldType.BOOLEAN,
            default=True,
            hint="Habilita o deshabilita la ejecución de JavaScript",
            admin_only=True,
            order=1
        ),
        
        ConfigFieldSchema(
            key="image",
            label="Imagen Docker",
            type=ConfigFieldType.TEXT,
            default="node:20-slim",
            hint="Imagen Docker de Node.js a usar",
            placeholder="node:20-slim",
            admin_only=True,
            group="Docker",
            order=10
        ),
        
        ConfigFieldSchema(
            key="memory_limit",
            label="Límite de memoria",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("256m", "256 MB"),
                SelectOption("512m", "512 MB"),
                SelectOption("1g", "1 GB"),
                SelectOption("2g", "2 GB")
            ],
            default="512m",
            hint="Memoria máxima que puede usar el contenedor",
            admin_only=True,
            group="Recursos",
            order=20
        ),
        
        ConfigFieldSchema(
            key="cpu_limit",
            label="Límite de CPU",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("0.5", "0.5 cores"),
                SelectOption("1.0", "1 core"),
                SelectOption("2.0", "2 cores")
            ],
            default="1.0",
            hint="Número máximo de CPU cores",
            admin_only=True,
            group="Recursos",
            order=21
        ),
        
        ConfigFieldSchema(
            key="timeout",
            label="Timeout (segundos)",
            type=ConfigFieldType.NUMBER,
            default=30,
            validation=ValidationRule(min=5, max=120),
            hint="Tiempo máximo de ejecución (5-120 segundos)",
            admin_only=True,
            group="Recursos",
            order=22
        ),
        
        ConfigFieldSchema(
            key="network_enabled",
            label="Permitir red",
            type=ConfigFieldType.BOOLEAN,
            default=False,
            hint="Permite acceso a internet desde el contenedor",
            admin_only=True,
            group="Seguridad",
            order=30
        ),
    ],
    
    default_config={
        "enabled": True,
        "image": "node:20-slim",
        "memory_limit": "512m",
        "cpu_limit": "1.0",
        "timeout": 30,
        "network_enabled": False
    }
)


# ============================================
# Shell Execution
# ============================================

SHELL_EXEC_SCHEMA = ToolConfigurableSchema(
    id="shell",
    display_name="Ejecución Shell",
    description="Ejecuta comandos shell en el sistema host",
    icon="terminal",
    category="execution",
    admin_only=True,
    
    config_schema=[
        ConfigFieldSchema(
            key="enabled",
            label="Habilitado",
            type=ConfigFieldType.BOOLEAN,
            default=True,
            hint="Habilita o deshabilita la ejecución de comandos shell",
            admin_only=True,
            order=1
        ),
        
        ConfigFieldSchema(
            key="timeout",
            label="Timeout (segundos)",
            type=ConfigFieldType.NUMBER,
            default=30,
            validation=ValidationRule(min=5, max=300),
            hint="Tiempo máximo de ejecución (5-300 segundos)",
            admin_only=True,
            group="Recursos",
            order=10
        ),
        
        ConfigFieldSchema(
            key="workspace_root",
            label="Directorio de trabajo",
            type=ConfigFieldType.TEXT,
            default="/workspace",
            hint="Directorio base para ejecución de comandos",
            placeholder="/workspace",
            admin_only=True,
            group="Rutas",
            order=20
        ),
        
        ConfigFieldSchema(
            key="blacklist_commands",
            label="Comandos prohibidos",
            type=ConfigFieldType.TEXT,
            default="rm -rf /, mkfs, dd if=",
            hint="Comandos o patrones prohibidos (separados por coma)",
            placeholder="rm -rf /, mkfs, dd if=",
            admin_only=True,
            group="Seguridad",
            order=30
        ),
    ],
    
    default_config={
        "enabled": True,
        "timeout": 30,
        "workspace_root": "/workspace",
        "blacklist_commands": "rm -rf /, mkfs, dd if="
    }
)
