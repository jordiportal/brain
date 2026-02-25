# Skill: Análisis de Datos Tabulares

Conocimiento para analizar archivos Excel, CSV y datos tabulares usando Python en el sandbox.

## Librerías disponibles en el sandbox

- `pandas` - Lectura, transformación y análisis de datos
- `openpyxl` - Lectura/escritura de archivos Excel (.xlsx)
- `xlrd` - Lectura de archivos Excel legacy (.xls)
- `matplotlib` / `seaborn` - Generación de gráficos
- `numpy` - Operaciones numéricas
- `scipy` / `scikit-learn` - Análisis estadístico y ML

## Lectura de archivos

### Excel
```python
import pandas as pd

# Leer archivo del workspace (subido por el usuario)
df = pd.read_excel('/workspace/uploads/archivo.xlsx')

# Leer hoja específica
df = pd.read_excel('/workspace/uploads/archivo.xlsx', sheet_name='Ventas')

# Listar hojas disponibles
xl = pd.ExcelFile('/workspace/uploads/archivo.xlsx')
print(xl.sheet_names)

# Leer todas las hojas
all_sheets = pd.read_excel('/workspace/uploads/archivo.xlsx', sheet_name=None)
for name, df in all_sheets.items():
    print(f"Hoja: {name}, Filas: {len(df)}")
```

### CSV
```python
df = pd.read_csv('/workspace/uploads/datos.csv')

# Con separador diferente
df = pd.read_csv('/workspace/uploads/datos.csv', sep=';', encoding='utf-8-sig')

# Especificar tipos de columna
df = pd.read_csv('/workspace/uploads/datos.csv', dtype={'codigo': str})
```

## Exploración rápida

```python
print(f"Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
print(f"\nColumnas: {list(df.columns)}")
print(f"\nTipos de datos:\n{df.dtypes}")
print(f"\nPrimeras filas:\n{df.head()}")
print(f"\nEstadísticas:\n{df.describe()}")
print(f"\nValores nulos:\n{df.isnull().sum()}")
```

## Transformaciones comunes

```python
# Filtrar
df_filtrado = df[df['columna'] > 100]

# Agrupar y agregar
resumen = df.groupby('categoria').agg({
    'ventas': ['sum', 'mean', 'count'],
    'margen': 'mean'
}).round(2)

# Pivot table
pivot = pd.pivot_table(df, values='ventas', index='region', columns='mes', aggfunc='sum')

# Ordenar
df_sorted = df.sort_values('ventas', ascending=False)

# Nuevas columnas calculadas
df['margen_pct'] = (df['margen'] / df['ventas'] * 100).round(2)
```

## Generación de gráficos

Guardar siempre en `/workspace/media/` para que sea accesible como artefacto.

```python
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI

fig, ax = plt.subplots(figsize=(10, 6))
df.groupby('categoria')['ventas'].sum().plot(kind='bar', ax=ax, color='#6366f1')
ax.set_title('Ventas por Categoría', fontsize=14, fontweight='bold')
ax.set_ylabel('Ventas (€)')
plt.tight_layout()
plt.savefig('/workspace/media/chart_ventas.png', dpi=150, bbox_inches='tight')
plt.close()
print("Gráfico guardado en /workspace/media/chart_ventas.png")
```

### Tipos de gráficos recomendados

| Propósito | Tipo | Código |
|-----------|------|--------|
| Comparar cantidades | Barras | `df.plot(kind='bar')` |
| Tendencia temporal | Líneas | `df.plot(kind='line')` |
| Distribución | Histograma | `df['col'].hist(bins=20)` |
| Composición | Donut/Pie | `df.plot(kind='pie')` |
| Correlación | Scatter | `df.plot(kind='scatter', x='a', y='b')` |
| Múltiples métricas | Subplots | `fig, axes = plt.subplots(2, 2)` |

## Exportar resultados

```python
# Guardar como nuevo Excel
df_resultado.to_excel('/workspace/media/analisis_resultado.xlsx', index=False)

# Guardar como CSV
df_resultado.to_csv('/workspace/media/export.csv', index=False)

# Guardar resumen como texto
with open('/workspace/media/resumen.txt', 'w') as f:
    f.write(resumen.to_string())
```

## Flujo recomendado de análisis

1. **Explorar**: Leer archivo, mostrar dimensiones, columnas, tipos, nulos
2. **Resumir**: Estadísticas descriptivas, distribuciones, valores únicos
3. **Analizar**: Agrupaciones, pivots, correlaciones según la pregunta
4. **Visualizar**: Generar gráfico relevante y guardarlo en /workspace/media/
5. **Reportar**: Presentar hallazgos con números concretos y conclusiones

## Notas importantes

- Los archivos subidos por el usuario están en `/workspace/uploads/`
- Los resultados (gráficos, Excel) se guardan en `/workspace/media/`
- Siempre usar `matplotlib.use('Agg')` antes de importar pyplot
- Usar `plt.close()` después de guardar para liberar memoria
- Mostrar siempre las primeras filas al usuario para confirmar que se leyó bien
- Si el archivo tiene múltiples hojas, listarlas y preguntar cuál analizar
