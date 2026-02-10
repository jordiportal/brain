# Extracción de Datos SAP BIW

## Objetivo
Extracción eficiente de datos desde SAP BW/BI (Business Intelligence Warehouse) usando las herramientas específicas.

## Estructura de Datos BIW

### InfoCubes (Cubos OLAP)
Los InfoCubes son estructuras multidimensionales optimizadas para reporting:
- **Características (Characteristics)**: Dimensiones de análisis (ej: Sociedad, Centro, Producto)
- **Ratios (Key Figures)**: Medidas cuantitativas (ej: Ventas, Cantidad, Coste)
- **Jerarquías**: Navegación estructurada (ej: Año → Trimestre → Mes)

### DSOs (DataStore Objects)
Almacenamiento de datos a nivel de registro:
- **DSO Estándar**: Datos maestros con sobrescrita
- **DSO Write-Optimized**: Carga rápida sin sobrescrita
- **DSo Direct Update**: Actualización directa

### Queries BEx (Business Explorer)
Consultas estructuradas predefinidas:
- **Filtros**: Restricciones iniciales
- **Variables**: Parámetros de selección
- **Selecciones**: Filtros adicionales dinámicos

## Proceso de Extracción

### 1. Identificar el Origen de Datos
```
Determinar según la necesidad:
- InfoCube → Análisis multidimensional complejo
- DSO → Datos detallados o maestros
- Query BEx → Reporte estructurado predefinido
```

### 2. Definir Características y Ratios
```json
{
  "caracteristicas": ["ZCE_SOC", "ZCE_CENTRO", "ZCE_PRODUCTO", "ZCE_FECHA"],
  "ratios": ["ZKF_VENTAS", "ZKF_CANTIDAD", "ZKF_COSTE"],
  "jerarquias": ["ZHI_CALENDARIO", "ZHI_GEOGRAFIA"]
}
```

### 3. Aplicar Filtros
```json
{
  "filtros": {
    "ZCE_SOC": ["1000", "2000"],
    "ZCE_AÑO": ["2024"],
    "ZCE_MES": ["01", "02", "03"]
  }
}
```

### 4. Navegación Multidimensional
Técnicas comunes:
- **Drill-down**: De general a específico (Año → Mes → Día)
- **Roll-up**: Agregar niveles superiores
- **Slice**: Fijar una dimensión (solo Q1)
- **Dice**: Subconjunto de dimensiones

## Mejores Prácticas

1. **Selección de Granularidad**: 
   - InfoCube para agregaciones
   - DSO para datos detallados

2. **Optimización de Filtros**:
   - Filtros obligatorios en la query
   - Evitar traer datos innecesarios

3. **Jerarquías**:
   - Usar para navegación estructurada
   - Niveles intermedios para drill-down

4. **Variables**:
   - Parametrizar períodos, sociedades
   - Facilitar reutilización

## Ejemplo Completo

```python
# Extracción de ventas por región y producto
request = {
    "info_cube": "ZC_SALES_C01",
    "caracteristicas": ["ZCE_REGION", "ZCE_PRODUCTO", "ZCE_MES"],
    "ratios": ["ZKF_VENTAS_NETAS", "ZKF_CANTIDAD"],
    "filtros": {
        "ZCE_AÑO": ["2024"],
        "ZCE_SOC": ["1000"]
    },
    "jerarquia_tiempo": "ZHI_CALENDARIO",
    "nivel": "MES"
}

# Resultado: Matriz multidimensional lista para análisis
```
