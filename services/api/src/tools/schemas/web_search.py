"""
Configuration Schema for web_search tool

Soporta múltiples proveedores de búsqueda web:
- OpenAI (usa Bing, mejor integración)
- Tavily (optimizado para AI)
- Serper (Google Search API)
- DuckDuckGo (gratis, con rate limiting)
"""

from .base import (
    ToolConfigurableSchema,
    ConfigFieldSchema,
    ConfigFieldType,
    SelectOption,
    VisibilityCondition,
    ValidationRule,
)


WEB_SEARCH_SCHEMA = ToolConfigurableSchema(
    id="web_search",
    display_name="Búsqueda Web",
    description="Busca información actualizada en internet usando múltiples proveedores",
    icon="search",
    category="web",
    requires_api_key=True,
    supported_providers=["openai", "tavily", "serper", "duckduckgo"],
    
    config_schema=[
        ConfigFieldSchema(
            key="provider",
            label="Proveedor",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("openai", "OpenAI (usa Bing - recomendado)"),
                SelectOption("tavily", "Tavily (optimizado para AI)"),
                SelectOption("serper", "Serper (Google Search)"),
                SelectOption("duckduckgo", "DuckDuckGo (gratis, rate-limited)")
            ],
            default="openai",
            hint="OpenAI usa Bing y tiene mejor integración con LLMs. DuckDuckGo es gratis pero tiene límites.",
            order=1
        ),
        
        ConfigFieldSchema(
            key="api_key",
            label="API Key",
            type=ConfigFieldType.PASSWORD,
            default="",
            visible_when=VisibilityCondition(field="provider", values=["tavily", "serper"]),
            hint="API key del proveedor (Tavily o Serper). OpenAI usa la key de LLM providers.",
            placeholder="Introduce tu API key...",
            order=2
        ),
        
        ConfigFieldSchema(
            key="max_results",
            label="Resultados máximos",
            type=ConfigFieldType.NUMBER,
            default=5,
            validation=ValidationRule(min=1, max=20),
            hint="Número máximo de resultados por búsqueda (1-20)",
            order=3
        ),
        
        ConfigFieldSchema(
            key="search_depth",
            label="Profundidad de búsqueda",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("basic", "Básica (más rápida)"),
                SelectOption("advanced", "Avanzada (más completa)")
            ],
            default="basic",
            visible_when=VisibilityCondition(field="provider", value="tavily"),
            hint="Solo para Tavily. Avanzada incluye más contexto pero es más lenta.",
            group="Tavily",
            order=10
        ),
        
        ConfigFieldSchema(
            key="include_domains",
            label="Dominios incluidos",
            type=ConfigFieldType.TEXT,
            default="",
            visible_when=VisibilityCondition(field="provider", values=["tavily", "serper"]),
            hint="Dominios a incluir en la búsqueda (separados por coma). Ej: wikipedia.org,github.com",
            placeholder="wikipedia.org, github.com",
            group="Filtros",
            order=20
        ),
        
        ConfigFieldSchema(
            key="exclude_domains",
            label="Dominios excluidos",
            type=ConfigFieldType.TEXT,
            default="",
            visible_when=VisibilityCondition(field="provider", values=["tavily", "serper"]),
            hint="Dominios a excluir de la búsqueda (separados por coma)",
            placeholder="pinterest.com, facebook.com",
            group="Filtros",
            order=21
        ),
    ],
    
    default_config={
        "provider": "openai",
        "api_key": "",
        "max_results": 5,
        "search_depth": "basic",
        "include_domains": "",
        "exclude_domains": ""
    }
)
