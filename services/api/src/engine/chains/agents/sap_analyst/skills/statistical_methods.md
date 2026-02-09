# Métodos Estadísticos para Análisis de Datos

## 1. Estadísticas Descriptivas

### Medidas de Tendencia Central
- **Media**: Promedio aritmético
- **Mediana**: Valor central (resistente a outliers)
- **Moda**: Valor más frecuente

### Medidas de Dispersión
- **Rango**: Max - Min
- **Varianza**: σ² = Σ(x - μ)² / N
- **Desviación estándar**: σ = √varianza
- **IQR** (Rango Intercuartílico): Q3 - Q1

### Medidas de Forma
- **Asimetría (Skewness)**: Si > 0, cola derecha; < 0, cola izquierda
- **Curtosis**: > 3 distribución leptocúrtica (colas pesadas)

## 2. Análisis de Tendencias

### Suavizado Exponencial Simple
```python
# EMA (Exponential Moving Average)
alpha = 0.3  # Factor de suavizado
ema = [series[0]]
for value in series[1:]:
    ema.append(alpha * value + (1 - alpha) * ema[-1])
```

### Regresión Lineal
```python
import numpy as np

# y = mx + b
m, b = np.polyfit(x, y, 1)
trend_line = m * x + b

# R² - Coeficiente de determinación
r_squared = 1 - (sum((y - trend_line)²) / sum((y - mean(y))²))
```

### Decomposición de Series Temporales
```python
from statsmodels.tsa.seasonal import seasonal_decompose

# Descomponer en: tendencia + estacional + residual
result = seasonal_decompose(series, model='additive', period=12)
trend = result.trend
seasonal = result.seasonal
residual = result.resid
```

## 3. Análisis de Correlación

### Correlación de Pearson
```python
# r = cov(X,Y) / (σX * σY)
# r ∈ [-1, 1]
# 0.7-1.0: Fuerte positiva
# 0.4-0.7: Moderada
# 0.0-0.4: Débil

correlation_matrix = df.corr(method='pearson')
```

### Correlación de Spearman
- No paramétrica (rangos)
- Resistente a outliers
- Útil para relaciones no lineales monotónicas

## 4. Análisis ABC / Pareto

### Clasificación ABC
```python
def abc_analysis(values):
    """
    Clasifica items en A (80%), B (15%), C (5%)
    """
    sorted_values = sorted(values, reverse=True)
    total = sum(sorted_values)
    cumulative = np.cumsum(sorted_values)
    cumulative_pct = cumulative / total * 100
    
    classification = []
    for pct in cumulative_pct:
        if pct <= 80:
            classification.append('A')
        elif pct <= 95:
            classification.append('B')
        else:
            classification.append('C')
    
    return classification
```

### Curva de Pareto
```python
# Gráfico combinado: barras (valores) + línea (% acumulado)
pareto_data = values.sort_values(ascending=False)
pareto_cum_pct = pareto_data.cumsum() / pareto_data.sum() * 100
```

## 5. Detección de Anomalías

### Método IQR
```python
Q1 = data.quantile(0.25)
Q3 = data.quantile(0.75)
IQR = Q3 - Q1

# Outliers: < Q1 - 1.5*IQR o > Q3 + 1.5*IQR
lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

outliers = data[(data < lower_bound) | (data > upper_bound)]
```

### Z-Score
```python
z_scores = np.abs((data - data.mean()) / data.std())
anomalies = data[z_scores > 3]  # > 3 desviaciones estándar
```

### Isolation Forest
```python
from sklearn.ensemble import IsolationForest

model = IsolationForest(contamination=0.1, random_state=42)
anomaly_labels = model.fit_predict(data.reshape(-1, 1))
# -1 = anomalía, 1 = normal
```

## 6. Forecasting

### Promedio Móvil
```python
# SMA (Simple Moving Average)
def moving_average(series, window):
    return series.rolling(window=window).mean()

# EMA (Exponential Moving Average)
ema = series.ewm(span=window, adjust=False).mean()
```

### Holt-Winters (Triple Suavizado Exponencial)
```python
from statsmodels.tsa.holtwinters import ExponentialSmoothing

model = ExponentialSmoothing(
    series,
    trend='add',
    seasonal='add',
    seasonal_periods=12
).fit()

forecast = model.forecast(steps=12)
```

### ARIMA
```python
from statsmodels.tsa.arima.model import ARIMA

# ARIMA(p,d,q)
# p: orden autoregresivo
# d: diferenciaciones
# q: orden de media móvil

model = ARIMA(series, order=(1, 1, 1))
results = model.fit()
forecast = results.forecast(steps=12)
```

## 7. Métricas de Evaluación de Modelos

### Para Forecasting
```python
# MAE (Mean Absolute Error)
mae = np.mean(np.abs(actual - forecast))

# MAPE (Mean Absolute Percentage Error)
mape = np.mean(np.abs((actual - forecast) / actual)) * 100

# RMSE (Root Mean Square Error)
rmse = np.sqrt(np.mean((actual - forecast) ** 2))

# Bias (Sesgo)
bias = np.mean(forecast - actual)
```

## 8. Test Estadísticos

### Test t de Student
```python
from scipy import stats

# Comparar medias de dos grupos
t_stat, p_value = stats.ttest_ind(group_a, group_b)
# p < 0.05: diferencia significativa
```

### Test Chi-Cuadrado
```python
# Test de independencia entre variables categóricas
chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
```

### Test de Normalidad (Shapiro-Wilk)
```python
stat, p_value = stats.shapiro(data)
# p > 0.05: datos siguen distribución normal
```

## 9. Segmentación

### Clustering K-Means
```python
from sklearn.cluster import KMeans

# Encontrar grupos naturales en datos
kmeans = KMeans(n_clusters=3, random_state=42)
clusters = kmeans.fit_predict(data)

# Método del codo para elegir k
inertias = []
for k in range(1, 10):
    kmeans = KMeans(n_clusters=k, random_state=42)
    kmeans.fit(data)
    inertias.append(kmeans.inertia_)
```

## 10. Mejores Prácticas

1. **Limpiar outliers**: Evaluar si son errores o valores reales
2. **Normalizar**: Escalar variables para comparación justa
3. **Validar supuestos**: Verificar normalidad, homocedasticidad
4. **Cross-validation**: No evaluar en datos de entrenamiento
5. **Interpretabilidad**: Preferir modelos simples explicables
6. **Documentar**: Registrar métodos, parámetros, resultados
