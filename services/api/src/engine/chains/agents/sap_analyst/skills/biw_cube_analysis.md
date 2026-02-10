# Cubos OLAP - Análisis Multidimensional

## Objetivo
Análisis avanzado de InfoCubes de SAP BW usando técnicas OLAP (Online Analytical Processing).

## Conceptos Clave

### InfoCube Structure
```
                    [Ratios - Medidas]
                    Ventas | Costes | Beneficio
                          /
    [Características - Dimensiones]
    Tiempo ─── Geografía ─── Producto
       │          │            │
    Año         País         Categoría
    Mes         Región       Familia
    Día         Ciudad       Producto
```

### Navegación Multidimensional

#### Drill-Down (Descenso)
De nivel general a específico:
```
Total Ventas
    └── Europa
            └── España
                    └── Madrid
                            └── Tienda A
```

#### Roll-Up (Ascenso)
Agregar datos a niveles superiores:
```
Producto → Familia → Categoría → Total
```

#### Slice (Corte)
Fijar una dimensión y analizar otras:
```
Análisis: Solo Q1 2024
Tiempo: Q1 (fijo)
Producto: Todos
Geografía: Todas
```

#### Dice (Subconjunto)
Trabajar con subespacio de dimensiones:
```
Dimensiones seleccionadas:
- Productos electrónicos
- Europa occidental
- Últimos 2 años
```

## Operaciones OLAP

### 1. Navegación por Jerarquías
```python
# Ejemplo: Navegar calendario fiscal
hierarchy = {
    "name": "ZHI_CALENDARIO",
    "levels": [
        {"level": 0, "name": "Año fiscal"},
        {"level": 1, "name": "Trimestre"},
        {"level": 2, "name": "Período"},
        {"level": 3, "name": "Día"}
    ]
}

# Drill-down desde Año a Trimestre
drill_result = drill_down(
    cube="ZC_SALES",
    dimension="ZCE_CALENDARIO",
    from_level="AÑO",
    to_level="TRIMESTRE",
    value="2024"
)
```

### 2. Agregaciones
```python
# Agregar ventas por región
aggregation = {
    "operation": "SUM",
    "ratio": "ZKF_VENTAS",
    "group_by": ["ZCE_REGION", "ZCE_MES"],
    "filters": {"ZCE_AÑO": "2024"}
}
```

### 3. Comparativas (YoY, MoM, QoQ)
```python
# Variación YoY (Year-over-Year)
yoy_analysis = {
    "current_period": {"año": "2024", "meses": ["01","02","03"]},
    "previous_period": {"año": "2023", "meses": ["01","02","03"]},
    "ratios": ["ZKF_VENTAS"],
    "var_type": "percentage"
}

# Variación MoM (Month-over-Month)
mom_analysis = {
    "periods": [
        {"año": "2024", "mes": "03"},
        {"año": "2024", "mes": "02"}
    ],
    "ratios": ["ZKF_VENTAS", "ZKF_COSTES"]
}
```

### 4. Rankings y Top N
```python
# Top 10 productos por ventas
top_products = {
    "operation": "TOP_N",
    "n": 10,
    "ratio": "ZKF_VENTAS",
    "dimension": "ZCE_PRODUCTO",
    "order": "DESC",
    "filters": {"ZCE_AÑO": "2024"}
}

# Bottom 5 regiones por beneficio
bottom_regions = {
    "operation": "BOTTOM_N",
    "n": 5,
    "ratio": "ZKF_BENEFICIO",
    "dimension": "ZCE_REGION"
}
```

### 5. Análisis de Contribución
```python
# Porcentaje del total
contribution = {
    "calculation": "PERCENTAGE_OF_TOTAL",
    "ratio": "ZKF_VENTAS",
    "dimension": "ZCE_PRODUCTO",
    "show_total": True
}

# Participación de mercado
market_share = {
    "calculation": "SHARE",
    "numerator": "ZKF_VENTAS_EMPRESA",
    "denominator": "ZKF_VENTAS_MERCADO_TOTAL"
}
```

## Ejemplos Prácticos

### Análisis de Tendencias Temporales
```python
# Ventas mensuales últimos 24 meses
query = {
    "cube": "ZC_SALES_C01",
    "dimensions": ["ZCE_CALENDARIO"],
    "ratios": ["ZKF_VENTAS"],
    "time_range": "LAST_24_MONTHS",
    "granularity": "MONTH"
}

# Resultado: Serie temporal lista para forecasting
```

### Análisis ABC (Pareto)
```python
# Clasificación ABC de clientes
abc_analysis = {
    "cube": "ZC_SALES_C01",
    "dimension": "ZCE_CLIENTE",
    "ratio": "ZKF_VENTAS",
    "classification": "ABC",
    "breakpoints": {
        "A": 80,  # 80% del valor
        "B": 15,  # 15% del valor
        "C": 5    # 5% del valor
    }
}
```

### Matriz de Correlación
```python
# Correlación entre ratios
matrix = {
    "cube": "ZC_SALES_C01",
    "ratios": [
        "ZKF_VENTAS",
        "ZKF_COSTES",
        "ZKF_BENEFICIO",
        "ZKF_CANTIDAD"
    ],
    "filters": {"ZCE_AÑO": "2024"},
    "calculation": "CORRELATION_MATRIX"
}
```

## Técnicas Avanzadas

### 1. Exception Reporting
Identificar valores fuera de rango:
```python
exceptions = {
    "type": "ABOVE_AVERAGE",
    "ratio": "ZKF_VENTAS",
    "threshold": 2,  # 2 desviaciones estándar
    "dimensions": ["ZCE_PRODUCTO", "ZCE_REGION"]
}
```

### 2. Conditional Formatting
Reglas visuales para reportes:
```python
formatting = {
    "ratio": "ZKF_MARGEN",
    "rules": [
        {"condition": "< 0.05", "color": "red", "label": "Bajo"},
        {"condition": "0.05 to 0.15", "color": "yellow", "label": "Medio"},
        {"condition": "> 0.15", "color": "green", "label": "Alto"}
    ]
}
```

### 3. What-If Analysis
Simulaciones de escenarios:
```python
scenario = {
    "base_cube": "ZC_SALES_C01",
    "modifications": {
        "ZKF_PRECIO": "* 1.10",  # +10% precio
        "ZKF_CANTIDAD": "* 0.95"  # -5% cantidad
    },
    "calculate": ["ZKF_VENTAS", "ZKF_BENEFICIO"]
}
```
