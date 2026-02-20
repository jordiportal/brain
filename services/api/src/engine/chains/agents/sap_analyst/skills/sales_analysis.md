# Análisis de Ventas KH Lloreda

## Selección de query según la pregunta

| Tipo de pregunta | Query | Notas |
|---|---|---|
| Ventas del mes/año actual | `PBI_SEG_CLI_VNE_Q002` | Tiene 2026, VN estimada |
| Ventas históricas con detalle | `PBI_SEG_CLI_VNE_Q004` | Sin 2026, pero más medidas detalladas |
| Cierre de ventas con márgenes | `PBI_CIERRE_VN` | VN real/obj/prev + márgenes. Variable mes obligatoria |
| Evolución anual rápida | `CO_EVOL_VENTAS_ANUAL_OPT` | 5 medidas, multi-año |
| Histórico mensual (unidades) | `VTAS_HIST_MENS_OPT` | 3 medidas: unidades, facturado, PM |
| Año cerrado (post-cierre) | `PBI_SEG_CLI_VNE_Q005` | Solo disponible tras cierre fiscal |

## Medidas clave de ventas (Q002)

Las 21 medidas incluyen:
- `ZVNETAEST` — VN estimada del mes (incluye estimación del mes abierto)
- `PBI_VNETA_ACUM_MC` — VN acumulada mes actual
- `PBI_PREV_MESACT` — Previsión mes actual
- `PBI_OBJ_MESACT` — Objetivo mes actual
- `PBI_UD_FACT_ACUM` — Unidades facturadas acumuladas
- `PBI_UD_OBJ_ACUM` — Unidades objetivo acumuladas

## Dimensiones de análisis de ventas

### Por segmento de mercado
`dimension="ZSEGMEN"` → NACIONAL, EXPORTACION, DISTRIBUCION, USA

### Por marca
`dimension="0MATERIAL__YCOPAPH1"` → KH-7, CIF, DOMESTOS

### Por sub-marca
`dimension="0MATERIAL__YCOPAPH2"` → Quitagrasas, Sin Manchas, Antical, etc.

### Por grupo de cliente
`dimension="0CUST_SALES__0CUST_GROUP"` → SUPER, HIPER, DISCOUNT, MERCADONA, etc.

### Por mes (dentro de un año)
`dimension="0CALMONTH2"` → 01, 02, ..., 12

## Patrones de análisis

### Análisis de mes actual
```
bi_execute_query(
  query="ZBOKCOPA/PBI_SEG_CLI_VNE_Q002",
  measures=["ZVNETAEST", "PBI_PREV_MESACT", "PBI_OBJ_MESACT"],
  filters={"0CALMONTH": "YYYYMM"}
)
```
Compara VN estimada vs previsión y objetivo. Calcula % cumplimiento.

### Evolución mensual del año
```
bi_execute_query(
  query="ZBOKCOPA/PBI_SEG_CLI_VNE_Q002",
  dimension="0CALMONTH",
  filters={"0CALYEAR": "2026"}
)
```

### Top-down analysis
1. **Totales** → ¿cómo va el mes?
2. **Por segmento** → ¿quién contribuye más/menos?
3. **Por marca** (filtrado al segmento destacado) → ¿qué marca impulsa/frena?
4. **Por cliente** → ¿quién compra más/menos?

### Mes abierto vs mes cerrado
- **Mes cerrado**: Datos definitivos, se puede desglosar por todas las dimensiones
- **Mes abierto (actual)**: Solo `ZVNETAEST` tiene estimación total. Las unidades parciales (`PBI_UD_FACT_ACUM`) sí se desglosan. La VN en EUR NO se puede desglosar por dimensiones en mes abierto.

## Cierre de ventas (PBI_CIERRE_VN)

Para análisis de cierre con márgenes incluidos:
```
bi_execute_query(
  query="ZBOKCOPA/PBI_CIERRE_VN",
  dimension="ZSEGMEN",
  filters={"0CALYEAR": "2025", "0CALMONTH2": "06"}
)
```
El filtro `0CALMONTH2` indica "hasta qué mes" va el cierre. Se auto-enruta a la variable SAP `MESOBLI`.

## Stock e Inventario

Query `0IC_C03/PBI_ST_001` (4 medidas): unidades y valor en stock.
Útil para contrastar con datos de ventas (rotación, cobertura).

## Contexto de negocio para interpretar datos

- KH-7 domina con 88% de ingresos → cualquier variación en KH-7 impacta fuertemente al total
- NACIONAL es el segmento principal → EXPORTACION puede tener mayor crecimiento %
- Estacionalidad: Q1 y Q3 suelen ser más fuertes en limpieza doméstica
- MERCADONA (ZD) y SUPER (Z2) son los canales de mayor volumen
