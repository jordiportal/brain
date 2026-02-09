# SAP Analyst Agent

Subagente especializado en análisis de datos SAP S/4HANA, ECC y BI/BW.

## Características

- **Extracción de datos**: Conecta a SAP vía RFC, OData APIs o queries
- **Análisis estadístico**: Tendencias, correlaciones, anomalías, forecasting
- **Múltiples módulos**: Soporte para FI/CO, SD, MM, PP, HR
- **Reportes ejecutivos**: Genera insights y recomendaciones accionables
- **Sistema de skills**: Carga conocimiento especializado según el tipo de análisis

## Uso

### Desde el Adaptive Agent

El agente principal puede delegar tareas de análisis SAP:

```python
result = await delegate(
    agent="sap_analyst",
    task="Análisis de ventas del último trimestre por región"
)
```

### Directamente

```python
from src.engine.chains.agents import SAPAnalystAgent

analyst = SAPAnalystAgent()
result = await analyst.execute(
    task='{"task": "Análisis de inventario MM", "module": "MM", "period": {"type": "last_month"}}',
    context="connection_config"
)
```

## Estructura de la Tarea

La tarea puede ser un string simple o un JSON estructurado:

```json
{
  "task": "Descripción del análisis requerido",
  "module": "SD|FI|CO|MM|PP|HR",
  "tables": ["VBAK", "VBAP"],
  "fields": ["vbeln", "erdat", "netwr"],
  "period": {
    "type": "last_month|last_quarter|last_year|custom",
    "from": "20240101",
    "to": "20241231"
  },
  "filters": {
    "vkorg": ["1000", "2000"],
    "vtweg": ["10"]
  },
  "analysis_type": "descriptive|forecasting|comparative|correlation|anomaly_detection|abc_analysis",
  "output_format": "report|excel|csv|json",
  "comparison": true,
  "group_by": ["region", "product"],
  "metrics": ["revenue", "quantity", "margin"]
}
```

## Skills Disponibles

1. **financial_analysis**: Análisis de FI/CO (balances, cash flow, cost centers)
2. **sales_analysis**: Análisis de SD (ventas, clientes, forecasting)
3. **inventory_analysis**: Análisis de MM (stock, movimientos, ABC)
4. **procurement_analysis**: Análisis de compras (POs, vendors, compliance)
5. **production_analysis**: Análisis de PP (eficiencia, OEE, scrap)
6. **hr_analysis**: Análisis de HR (headcount, turnover, costes)
7. **sap_query_advanced**: Técnicas avanzadas de extracción SAP
8. **statistical_methods**: Métodos estadísticos (regresión, forecasting, etc.)

## Arquitectura

### Flujo de Ejecución

1. **Parseo**: Extrae parámetros de la tarea
2. **Validación**: Verifica requisitos mínimos
3. **Carga de skills**: Determina y carga skills relevantes
4. **Extracción**: Ejecuta código Python para extraer datos de SAP
5. **Análisis**: Procesa datos según el tipo de análisis solicitado
6. **Reporte**: Genera reporte estructurado con hallazgos y recomendaciones

### Tipos de Análisis Soportados

- **descriptive**: Estadísticas descriptivas básicas (media, sumas, distribuciones)
- **forecasting**: Proyecciones y tendencias futuras
- **comparative**: Comparativas período vs período
- **correlation**: Análisis de correlaciones entre variables
- **anomaly_detection**: Detección de outliers y anomalías
- **abc_analysis**: Clasificación ABC/Pareto

## Ejemplos de Uso

### Análisis de Ventas

```python
task = {
    "task": "Análisis de ventas del Q4 2024",
    "module": "SD",
    "period": {"type": "custom", "from": "20241001", "to": "20241231"},
    "analysis_type": "descriptive",
    "group_by": ["region", "sales_rep"]
}
```

### Forecasting de Inventario

```python
task = {
    "task": "Predicción de necesidades de stock para próximo trimestre",
    "module": "MM",
    "analysis_type": "forecasting",
    "metrics": ["stock_quantity", "stock_value", "turnover_rate"]
}
```

### Análisis Financiero Comparativo

```python
task = {
    "task": "Comparativa P&L 2024 vs 2023",
    "module": "FI",
    "analysis_type": "comparative",
    "comparison": True,
    "output_format": "excel"
}
```

## Notas de Implementación

- **Datos simulados**: La implementación actual usa datos simulados para demostración
- **Conexión real SAP**: Para producción, implementar conectores pyrfc/pyodata
- **Seguridad**: No incluir credenciales SAP en las tareas, usar contexto seguro
- **Performance**: Las extracciones grandes deben hacerse por bloques (chunking)

## Dependencias

El agente utiliza las siguientes tools del sistema:
- `execute_code`: Ejecutar scripts de extracción/análisis
- `filesystem`: Lectura/escritura de archivos
- `web_search`: Consultar documentación SAP

## Extensión

Para agregar nuevos tipos de análisis:

1. Crear skill en `skills/`
2. Agregar a `SAP_ANALYST_SKILLS` en `agent.py`
3. Implementar lógica en `_generate_analysis_code()`
4. Actualizar `_generate_report()` para el nuevo formato

## Testing

Ejecutar tests:
```bash
cd services/api
python -m pytest tests/agents/test_sap_analyst.py -v
```

## Changelog

### v1.0.0
- Implementación inicial del SAP Analyst Agent
- Soporte para 6 módulos SAP (FI, CO, SD, MM, PP, HR)
- 8 skills especializados
- 6 tipos de análisis estadísticos
- Generación de reportes en formato Markdown
