"""
Brain 2.0 Domain-Specific Tools

Herramientas especializadas organizadas por dominio:
- media: Generación y manipulación de imágenes
- sap: Integración con SAP S/4HANA y BIW
- mail: Gestión de correo electrónico
- office: Creación de documentos Office
"""

from .media import MEDIA_TOOLS

# Exportar todas las herramientas de dominio
DOMAIN_TOOLS = {
    **MEDIA_TOOLS
}

__all__ = ["DOMAIN_TOOLS", "MEDIA_TOOLS"]
