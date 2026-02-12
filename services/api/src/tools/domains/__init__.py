"""
Brain 2.0 Domain-Specific Tools

Herramientas especializadas organizadas por dominio:
- media: Generación y manipulación de imágenes
- sap_biw: Integración con SAP BW/BI (Business Intelligence Warehouse)
- mail: Gestión de correo electrónico
- office: Creación de documentos Office
- rag: Recuperación Aumentada (Retrieval Augmented Generation)
"""

from .media import MEDIA_TOOLS
from .sap_biw import BIW_TOOLS
from .rag import RAG_TOOLS

# Exportar todas las herramientas de dominio
DOMAIN_TOOLS = {
    **MEDIA_TOOLS,
    **BIW_TOOLS,
    **RAG_TOOLS
}

__all__ = ["DOMAIN_TOOLS", "MEDIA_TOOLS", "BIW_TOOLS", "RAG_TOOLS"]
