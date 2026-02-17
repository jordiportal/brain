# SAP BIW Analyst Agent v3.0

Subagente especializado en análisis de datos SAP BIW (Business Intelligence Warehouse).
Conecta directamente al proxy-biw via HTTP, leyendo configuración de `openapi_connections`.

## Arquitectura

```
SAPAnalystAgent → Herramientas bi_* → HTTP → proxy-biw :3000 → RFC → SAP BIW
                                                ↑
                                    openapi_connections (slug=sap-biw)
                                    → base_url + auth_token
```

## Herramientas Disponibles

| Herramienta | Descripción |
|---|---|
| `bi_list_catalogs` | Lista catálogos (InfoCubes/MultiProviders) |
| `bi_list_queries` | Lista queries BIW por catálogo o texto |
| `bi_get_metadata` | Dimensiones y medidas de una query |
| `bi_get_dimension_values` | Valores posibles de una dimensión |
| `bi_execute_query` | Ejecuta query estructurada (genera MDX internamente) |
| `bw_execute_mdx` | Ejecuta MDX directo (avanzado) |
| `generate_spreadsheet` | Genera Excel con datos |
| `filesystem` | Lectura/escritura de archivos |
| `execute_code` | Análisis avanzado con Python |

## Configuración

1. Asegurarse de que existe la conexión OpenAPI con slug `sap-biw`
2. Configurar `base_url` apuntando al proxy-biw (ej: `http://host.docker.internal:3000`)
3. Configurar `auth_token` con el token Bearer del proxy
4. Marcar la conexión como activa

## Skills

| Skill | Descripción |
|---|---|
| `sap_biw_analyst` | **Principal**: queries KH Lloreda, dimensiones, medidas, versiones, ejemplos |
| `biw_data_extraction` | Técnicas de extracción BIW |
| `financial_analysis` | P&L, márgenes, ratios financieros |
| `sales_analysis` | Ventas por segmento, canal, marca |

## Uso

### Desde el Adaptive Agent

```python
result = await delegate(
    agent="sap_analyst",
    task="¿Cómo fueron las ventas en enero 2026 por segmento?"
)
```

## Changelog

### v3.0.0
- Herramientas HTTP directas al proxy-biw (sin mocks)
- Nuevas tools: bi_list_catalogs, bi_list_queries, bi_get_metadata, bi_get_dimension_values, bi_execute_query, bw_execute_mdx
- Skill `sap_biw_analyst` con conocimiento de dominio KH Lloreda
- Conexión via openapi_connections (slug=sap-biw)
- Eliminado: mocks, detección OpenAPI, herramientas biw_get_*

### v2.2.0
- Loop multi-turno con LLM
- Detección automática de tools OpenAPI SAP

### v1.0.0
- Implementación inicial
