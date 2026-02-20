# Patrones de extracción SAP BIW - KH Lloreda

## Uso de bi_execute_query

La herramienta `bi_execute_query` genera MDX internamente. Nunca necesitas escribir MDX. Parámetros:

- **query**: Nombre completo (ej: `ZBOKCOPA/PBI_SEG_CLI_VNE_Q002`)
- **measures**: Array de nombres técnicos. Vacío u omitido = todas las medidas
- **dimension**: Dimensión para desglose de filas (una por llamada)
- **filters**: Pares dimensión:valor (ej: `{"0CALMONTH": "202601"}`)
- **options.maxRecords**: Máximo de filas (default: 10000)

## Manejo automático de variables SAP

El servicio auto-resuelve las variables SAP BW. No necesitas preocuparte por ellas:

- **Variables de intervalo** (como `VINTMES` para meses): Se auto-expanden al rango completo (01:12)
- **Variables obligatorias de valor único** (como `MESOBLI` en PBI_CIERRE_VN): Se resuelven a valores por defecto sensatos (mes 12)
- Si pasas filtros de tiempo en `filters`, se auto-enrutan a la variable SAP correspondiente cuando sea necesario

### PBI_CIERRE_VN — Caso especial

Esta query tiene la variable `MESOBLI` (mes obligatorio). Para consultar un mes específico:
```
bi_execute_query(
  query="ZBOKCOPA/PBI_CIERRE_VN",
  filters={"0CALYEAR": "2025", "0CALMONTH2": "06"}
)
```
El filtro `0CALMONTH2` se auto-enruta a la variable `MESOBLI`. Si se omite, usa mes 12 por defecto.

## Estrategias de selección de medidas

### Cuando hay muchas medidas (queries P&L con 60-86 medidas)
Selecciona solo las relevantes para la pregunta. Medidas clave de P&L:
- `00O2TOVQWROHDSV6GFY652O65` — Venta Neta
- `00O2TOVQWROHDNZHL9NKWNV3C` — Margen Bruto
- `00O2TOVQWROHDNZHL9NKWO1EW` — Margen Distribución
- `00O2TOVQWROHDNZHL9NKWO7QG` — Margen Comercial

### Cuando hay pocas medidas (queries de ventas con 3-21 medidas)
Puedes omitir `measures` para obtener todas.

### Query de Tesorería (1.584 medidas)
**SIEMPRE** especifica medidas concretas. Nunca ejecutes sin filtrar medidas.

## Patrones multi-query

### Comparativa de períodos
Requiere dos llamadas separadas (la cláusula WHERE MDX acepta un valor por dimensión temporal):
```
Llamada 1: filters={"0CALMONTH": "202601"}  // Enero 2026
Llamada 2: filters={"0CALMONTH": "202501"}  // Enero 2025
```
Combina resultados y calcula variaciones (absoluta y %).

### Análisis cruzado de dimensiones
Una dimensión por llamada. Para segmento + marca:
```
Llamada 1: dimension="ZSEGMEN"
Llamada 2: dimension="0MATERIAL__YCOPAPH1"
```
Ambas con los mismos filtros. Combina en la respuesta.

### Drill-down progresivo
1. Totales (sin dimensión) → identificar anomalías
2. Desglose por la dimensión más relevante → localizar contribuyentes
3. Filtrar por el valor destacado + desglosar por otra dimensión

## Uso de bi_get_metadata

Usa `bi_get_metadata` para descubrir medidas y dimensiones antes de ejecutar una query desconocida. Retorna:
- Lista de dimensiones con captions
- Lista de medidas con captions y tipos de datos

Es esencial cuando:
- Primera vez que consultas una query en la conversación
- El usuario pide datos que no sabes si existen en la query
- Necesitas IDs técnicos exactos de medidas
