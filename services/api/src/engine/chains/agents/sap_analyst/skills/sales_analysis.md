# Análisis de Ventas SAP (SD)

## Objetivo
Análisis de ventas y distribución desde el módulo SD de SAP.

## Tablas Clave

- **VBAK**: Cabecera de pedidos de venta
- **VBAP**: Posiciones de pedidos de venta
- **VBRK**: Cabecera de facturas
- **VBRP**: Posiciones de facturas
- **KNA1**: Datos maestros de clientes
- **MARA**: Datos maestros de materiales
- **TVKBT**: Textos de grupos de clientes

## Métricas de Ventas Clave

### 1. Análisis de Volumen
```python
# KPIs básicos
total_revenue = df['amount'].sum()
total_orders = len(df)
avg_order_value = total_revenue / total_orders
total_quantity = df['quantity'].sum()
```

### 2. Análisis Temporal
- Ventas por mes/año
- Comparativa YoY (Year over Year)
- Comparativa MoM (Month over Month)
- Tendencias estacionales

### 3. Análisis de Clientes
- Top N clientes (Pareto 80/20)
- Distribución ABC de clientes
- Customer Lifetime Value (CLV)
- Churn rate de clientes

### 4. Análisis de Productos
- Top N productos
- Mix de productos por cliente
- Penetración de categorías
- Análisis de canibalización

### 5. Análisis Geográfico
- Ventas por región/país
- Densidad de clientes
- Análisis de territorios

## Segmentación Común

### Por Dimensiones
- **Temporal**: Día, Semana, Mes, Trimestre, Año
- **Geográfico**: Región, País, Ciudad, Territorio
- **Producto**: Categoría, Familia, SKU
- **Cliente**: Tipo, Segmento, Canal, Grupo
- **Comercial**: Vendedor, Equipo, Organización de ventas

## Forecasting de Ventas

### Métodos
1. **Promedio móvil**: Suavizado de series temporales
2. **Tendencia lineal**: Regresión simple
3. **Seasonal ARIMA**: Para datos con estacionalidad
4. **Holt-Winters**: Triple suavizado exponencial

### Métricas de Precisión
- MAE (Mean Absolute Error)
- MAPE (Mean Absolute Percentage Error)
- RMSE (Root Mean Square Error)

## Mejores Prácticas

1. **Limpiar cancelaciones**: Excluir pedidos cancelados
2. **Tratar devoluciones**: Considerar facturas de crédito
3. **Moneda consistente**: Convertir a moneda base
4. **Validar duplicados**: Asegurar integridad referencial

## Reportes Típicos
- Sales Performance Dashboard
- Pipeline Analysis
- Win/Loss Analysis
- Customer Segmentation
- Territory Performance
