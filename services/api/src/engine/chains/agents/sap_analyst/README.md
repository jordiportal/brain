# SAP BIW Analyst Agent

Subagente especializado en análisis de datos SAP BIW (Business Intelligence Warehouse).

## Características

- **Extracción BIW**: InfoCubes, DSOs, queries BEx, datos maestros
- **Análisis OLAP**: Navegación multidimensional, drill-down, slicing
- **Reportes BIW**: Tabulares, cruzados, jerárquicos, dashboards
- **KPIs y Ratios**: Key Figures, características, jerarquías
- **Sistema de skills**: Conocimiento especializado en BIW/BW

## Uso

### Desde el Adaptive Agent

El agente principal puede delegar tareas de análisis BIW:

```python
result = await delegate(
    agent="sap_analyst",
    task="Análisis de ventas del último trimestre desde el cubo ZC_SALES"
)
```

### Directamente

```python
from src.engine.chains.agents import SAPAnalystAgent

analyst = SAPAnalystAgent()
result = await analyst.execute(
    task='{"task": "Análisis de cubo ZC_COSTS por centro de coste", "period": {"type": "last_quarter"}}',
    context="biw_connection_config"
)
```

## Estructura de la Tarea

La tarea puede ser un string simple o un JSON estructurado:

```json
{
  "task": "Descripción del análisis requerido",
  "info_cube": "ZC_SALES_C01",
  "dso": "ZDSO_SALES",
  "bex_query": "ZQ_SALES_BY_REGION",
  "caracteristicas": ["ZCE_REGION", "ZCE_PRODUCTO"],
  "ratios": ["ZKF_VENTAS", "ZKF_CANTIDAD"],
  "jerarquias": ["ZHI_CALENDARIO"],
  "period": {
    "type": "last_month|last_quarter|last_year|custom",
    "from": "20240101",
    "to": "20240331"
  },
  "filtros": {
    "ZCE_SOC": ["1000", "2000"],
    "ZCE_AÑO": ["2024"]
  },
  "analysis_type": "descriptive|forecasting|comparative|drill_down"
}
```

## Características Principales

### 1. Múltiples Fuentes de Datos

- **InfoCubes**: Cubos OLAP multidimensionales
- **DSOs**: DataStore Objects para datos detallados
- **Queries BEx**: Consultas estructuradas predefinidas

### 2. Análisis Multidimensional

- **Navegación**: Drill-down, roll-up, slice, dice
- **Jerarquías**: Temporales, geográficas, organizativas
- **Agregaciones**: Por múltiples dimensiones simultáneas

### 3. Tipos de Análisis

- **Descriptivo**: Resumen y estadísticas básicas
- **Comparativo**: YoY, MoM, QoQ
- **Forecasting**: Proyecciones y tendencias
- **OLAP**: Navegación interactiva por dimensiones

## Herramientas Disponibles

- `biw_get_cube_data`: Extraer datos de InfoCubes
- `biw_get_dso_data`: Extraer datos de DSOs
- `biw_get_bex_query`: Ejecutar queries BEx
- `biw_get_master_data`: Obtener datos maestros
- `biw_get_hierarchy`: Obtener jerarquías
- `biw_get_texts`: Obtener textos descriptivos
- `biw_get_ratios`: Obtener ratios calculados
- `filesystem`: Lectura/escritura de archivos
- `execute_code`: Análisis estadístico avanzado

## Skills Disponibles

1. **biw_data_extraction**: Extracción de InfoCubes, DSOs, queries
2. **biw_reporting**: Creación de reportes y dashboards
3. **biw_cube_analysis**: Análisis multidimensional OLAP
4. **biw_master_data**: Gestión de datos maestros
5. **sap_query_advanced**: Técnicas avanzadas de extracción
6. **statistical_methods**: Métodos estadísticos

## Ejemplos de Uso

### Análisis de Cubo de Ventas

```python
task = {
    "task": "Análisis de ventas por región y producto Q1 2024",
    "info_cube": "ZC_SALES_C01",
    "caracteristicas": ["ZCE_REGION", "ZCE_PRODUCTO"],
    "ratios": ["ZKF_VENTAS", "ZKF_BENEFICIO"],
    "period": {"type": "custom", "from": "20240101", "to": "20240331"},
    "analysis_type": "comparative",
    "group_by": ["ZCE_REGION"]
}
```

### Extracción de Datos Maestros

```python
task = {
    "task": "Datos maestros de materiales con atributos",
    "dso": "ZDSO_MATERIAL",
    "fields": ["MATNR", "MAKTX", "MTART", "MATKL"],
    "filters": {"ZCE_ESTATUS": ["ACTIVO"]}
}
```

### Query BEx con Filtros

```python
task = {
    "task": "Reporte de margen por cliente y mes",
    "bex_query": "ZQ_MARGIN_ANALYSIS",
    "variables": {
        "ZVA_AÑO": "2024",
        "ZVA_SOC": "1000"
    },
    "output_format": "excel"
}
```

## Arquitectura

### Flujo de Ejecución

1. **Parseo**: Extrae parámetros de la tarea (InfoCube, DSO, query)
2. **Validación**: Verifica requisitos mínimos
3. **Carga de skills**: Determina y carga skills relevantes
4. **Extracción**: Usa herramientas BIW para obtener datos
5. **Análisis**: Procesa según tipo solicitado (OLAP, tendencias, etc.)
6. **Reporte**: Genera output estructurado

## Notas de Implementación

- Las herramientas BIW requieren conexión configurada en Tools → OpenAPI
- Los InfoCubes son multidimensionales: usa jerarquías para navegación
- Las queries BEx pueden tener variables obligatorias
- El agente mantiene compatibilidad hacia atrás con estructura anterior

## Testing

Ejecutar tests:
```bash
cd services/api
python -m pytest tests/agents/test_sap_analyst.py -v
```

## Changelog

### v1.0.0
- Implementación inicial del SAP BIW Analyst Agent
- Soporte para InfoCubes, DSOs y queries BEx
- 6 skills especializados en BIW
- Navegación multidimensional OLAP
- Generación de reportes BIW
