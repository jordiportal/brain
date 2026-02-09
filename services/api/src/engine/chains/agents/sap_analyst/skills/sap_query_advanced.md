# Queries SAP Avanzadas

## Técnicas de Extracción Eficiente

### 1. Optimización de Selección

```sql
-- Usar índices correctamente
SELECT * FROM vbak 
WHERE erdat BETWEEN '20240101' AND '20241231'  -- Fecha de creación
  AND auart = 'TA'                              -- Tipo de orden
  AND vkorg = '1000';                           -- Organización de ventas
```

### 2. Joins Optimizados

```sql
-- Pedidos con detalle de cliente
SELECT 
  a.vbeln, a.erdat, a.netwr,
  b.kunnr, b.name1,
  c.maktx
FROM vbak a
INNER JOIN kna1 b ON a.kunnr = b.kunnr
LEFT JOIN makt c ON a.matnr = c.matnr
WHERE a.erdat >= '20240101';
```

### 3. Uso de Variants en Queries

```python
# Ejecutar query con variant predefinido
variant_params = {
    "werks": ["1000", "2000"],      # Plantas
    "lgort": ["0001"],               # Almacenes
    "matnr": [],                      # Todos los materiales
    "date_from": "20240101",
    "date_to": "20241231"
}
```

### 4. Extracción por Bloques

```python
# Para grandes volúmenes, extraer por chunks
def extract_chunked(table, date_field, start_date, end_date, chunk_days=30):
    current = start_date
    while current < end_date:
        chunk_end = min(current + timedelta(days=chunk_days), end_date)
        
        query = f"""
        SELECT * FROM {table}
        WHERE {date_field} BETWEEN '{current:%Y%m%d}' 
          AND '{chunk_end:%Y%m%d}'
        """
        
        yield execute_query(query)
        current = chunk_end
```

### 5. RFC Calls (pyrfc)

```python
from pyrfc import Connection

conn = Connection(
    ashost='sapserver',
    sysnr='00',
    client='100',
    user='user',
    passwd='pass'
)

# Llamar a BAPI
result = conn.call('BAPI_SALESORDER_GETLIST',
    CUSTOMER='0000100000',
    DOCUMENT_DATE='20240101'
)
```

### 6. OData Queries

```python
import requests

# SAP Gateway OData
base_url = "https://sap-server:44300/sap/opu/odata/sap/API_SALES_ORDER_SRV"

# Query con filtros
params = {
    "$filter": "CreationDate ge datetime'2024-01-01T00:00:00'",
    "$select": "SalesOrder,CreationDate,SoldToParty,TotalNetAmount",
    "$top": 100,
    "$orderby": "CreationDate desc"
}

response = requests.get(f"{base_url}/A_SalesOrder", 
                       params=params,
                       auth=('user', 'pass'))
```

## Patrones de Extracción por Módulo

### FI/CO
- Usar períodos contables (F.16 cerrar, F.15 abrir)
- Considerar sociedades y división
- Validar estados de documentos

### SD
- Excluir posiciones eliminadas (loekz = '')
- Considerar tipos de orden relevantes
- Filtrar por organización de ventas

### MM
- Usar vistas de material correctas
- Considerar stocks especiales
- Validar períodos de valoración

### PP
- Incluir órdenes TECO (technical complete)
- Considerar variantes de configuración
- Analizar por centro y orden

## Manejo de Errores

```python
try:
    data = extract_sap_data()
except SAPConnectionError as e:
    logger.error(f"Connection failed: {e}")
    # Retry con backoff
except SAPAuthorizationError as e:
    logger.error(f"Authorization issue: {e}")
    # Notificar a seguridad
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Fallback a caché
```

## Performance Tips

1. **Selección primero**: Siempre filtrar en SAP, no traer todo
2. **Índices**: Usar campos de índice (fecha, sociedad, centro)
3. **Campos necesarios**: Evitar SELECT *, especificar campos
4. **Paralelización**: Para queries independientes, usar threads
5. **Caching**: Cachear datos maestros que no cambian frecuentemente
6. **Batch size**: No extraer más de 10K-50K registros por llamada

## Validación de Datos

```python
def validate_extracted_data(df, expected_schema):
    """Valida integridad de datos extraídos."""
    
    checks = {
        "schema_match": set(df.columns) == set(expected_schema),
        "no_nulls_critical": df[['key_field']].notna().all(),
        "date_range_valid": (df['date'] >= min_date) & (df['date'] <= max_date),
        "referential_integrity": df['foreign_key'].isin(master_data)
    }
    
    return all(checks.values())
```
