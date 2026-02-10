# Reporting y Analytics BIW

## Objetivo
Creación de reportes estructurados y dashboards desde datos SAP BW/BI.

## Tipos de Reportes

### 1. Reportes Tabulares
Estructura filas-columnas tradicional:
```
| Producto | Q1 2024 | Q2 2024 | Q3 2024 | Total |
|----------|---------|---------|---------|-------|
| Prod A   | 100K    | 120K    | 110K    | 330K  |
| Prod B   | 80K     | 95K     | 105K    | 280K  |
```

### 2. Reportes Cruzados (Crosstab)
Análisis bidimensional:
```
          | Norte  | Sur   | Este  | Oeste | Total
----------|--------|-------|-------|-------|-------
Q1        | 100K   | 80K   | 90K   | 70K   | 340K
Q2        | 110K   | 85K   | 95K   | 75K   | 365K
Q3        | 120K   | 90K   | 100K  | 80K   | 390K
Total     | 330K   | 255K  | 285K  | 225K  | 1095K
```

### 3. Reportes Jerárquicos
Navegación estructurada:
```
2024 (Total: 1095K)
├── Q1 (340K)
│   ├── Enero (110K)
│   ├── Febrero (115K)
│   └── Marzo (115K)
├── Q2 (365K)
└── Q3 (390K)
```

## Componentes de un Reporte BIW

### Filtros Globales
Restricciones aplicables a todo el reporte:
```python
filtros_globales = {
    "ZCE_AÑO": ["2024"],
    "ZCE_SOC": ["1000", "2000"],
    "ZCE_ESTATUS": ["ACTIVO"]
}
```

### Filas y Columnas
Estructura del reporte:
```python
estructura = {
    "filas": ["ZCE_PRODUCTO", "ZCE_REGION"],
    "columnas": ["ZCE_TRIMESTRE"],
    "ratios": ["ZKF_VENTAS", "ZKF_BENEFICIO"]
}
```

### Ordenamientos
```python
orden = {
    "campo": "ZKF_VENTAS",
    "direccion": "DESC",
    "secundario": {"campo": "ZCE_PRODUCTO", "direccion": "ASC"}
}
```

### Formato Condicional
Resaltar valores importantes:
```python
formato = {
    "ratios": {
        "ZKF_MARGEN": [
            {"condicion": "< 0.05", "color": "rojo", "icono": "warning"},
            {"condicion": "> 0.20", "color": "verde", "icono": "check"}
        ],
        "ZKF_VENTAS": [
            {"condicion": "TOP_10", "negrita": True}
        ]
    }
}
```

## KPIs y Dashboards

### Indicadores Clave
```python
kpis = [
    {
        "nombre": "Ventas Totales",
        "ratio": "ZKF_VENTAS",
        "agregacion": "SUM",
        "formato": "moneda",
        "comparativa": "YoY"
    },
    {
        "nombre": "Margen Medio",
        "ratio": "ZKF_MARGEN",
        "agregacion": "AVG",
        "formato": "porcentaje",
        "target": 0.15
    },
    {
        "nombre": "Nº Clientes",
        "ratio": "ZKF_CLIENTES",
        "agregacion": "COUNT_DISTINCT",
        "formato": "numero"
    }
]
```

### Dashboard Layout
```
┌─────────────────────────────────────────┐
│  [KPI 1: Ventas]  [KPI 2: Margen]      │
│      ↓ 12%              ↑ 3%           │
├─────────────────────────────────────────┤
│         [Gráfico Tendencias]            │
│   (Ventas mensuales último año)        │
├─────────────────────────────────────────┤
│  [Tabla Top Productos] │ [Mapa Calor]   │
│                       │  (Ventas x Reg) │
└─────────────────────────────────────────┘
```

## Formato de Salida

### Excel
```python
excel_config = {
    "formato": "xlsx",
    "hojas": [
        {"nombre": "Resumen", "tipo": "dashboard"},
        {"nombre": "Detalle", "tipo": "datos"}
    ],
    "formatos_condicionales": True,
    "pivot_tables": True
}
```

### PDF
```python
pdf_config = {
    "formato": "pdf",
    "orientacion": "landscape",
    "encabezado": {
        "titulo": "Reporte de Ventas",
        "subtitulo": "Q1 2024",
        "logo": True
    },
    "pie": {
        "paginacion": True,
        "fecha_generacion": True
    }
}
```

### JSON (para APIs)
```python
json_output = {
    "metadata": {
        "titulo": "Ventas Q1 2024",
        "fecha_generacion": "2024-04-15",
        "registros": 1500
    },
    "resumen": {
        "total_ventas": 1095000,
        "total_productos": 45,
        "mejor_mes": "Marzo"
    },
    "datos": [
        {"producto": "Prod A", "mes": "Ene", "ventas": 100000},
        # ...
    ]
}
```

## Mejores Prácticas

1. **Título y Contexto**: Siempre incluir período, alcance y criterios
2. **Consistencia**: Mismo formato para reportes similares
3. **Agregaciones**: Mostrar totales y subtotales
4. **Comparativas**: Incluir YoY, MoM cuando aplique
5. **Visualizaciones**: Gráficos para tendencias, tablas para detalles
6. **Drill-down**: Permitir navegación desde resumen a detalle

## Ejemplo Completo

```python
# Configuración de reporte de ventas
reporte_ventas = {
    "titulo": "Análisis de Ventas por Producto y Región",
    "periodo": "Q1 2024",
    "origen_datos": {
        "cube": "ZC_SALES_C01",
        "query": "ZQ_SALES_BY_PRODUCT"
    },
    "estructura": {
        "filas": ["ZCE_REGION", "ZCE_PRODUCTO"],
        "columnas": ["ZCE_MES"],
        "ratios": ["ZKF_VENTAS", "ZKF_CANTIDAD", "ZKF_BENEFICIO"]
    },
    "formato": {
        "moneda": ["ZKF_VENTAS", "ZKF_BENEFICIO"],
        "numero": ["ZKF_CANTIDAD"],
        "porcentaje": ["ZKF_MARGEN"]
    },
    "destacados": {
        "top_5": True,
        "variaciones": True
    },
    "exportar": {
        "excel": True,
        "pdf": True,
        "json": True
    }
}
```
