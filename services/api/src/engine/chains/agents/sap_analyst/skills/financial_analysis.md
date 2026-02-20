# Análisis Financiero KH Lloreda - P&L y Márgenes

## Queries P&L disponibles

| Query | Medidas | Mejor para |
|---|---|---|
| `MKT_CUENTA_RES_CP_OPT_DPCT` | 78 | P&L mensual vista marketing, todos los márgenes |
| `POWER_BI_PYG` | 60 | P&L completo desde tarifa hasta margen operativo |
| `MKT_CUENTA_RES_PBI` | 80 | P&L para Power BI |
| `MKT_CUENTA_RES_PBI_ZMSCOPA` | 86 | Variante multicubo |

**CRÍTICO**: Todas requieren `"0VERSION": "#"` para datos reales.

## Estructura del P&L (cascada de márgenes)

```
Venta Tarifa
 - Descuentos
 = VTA FACTURADA
 - Rappel + Cargos
 = Venta Neta (~54M€ anual)
 - Coste de Venta
 = Margen Bruto (~55%)
 - Transporte Total
 = Margen Distribución
 - Promo Trade
 - Marketing
 = Margen Comercial (~33%)
```

## Medidas clave P&L (MKT_CUENTA_RES_CP_OPT_DPCT)

| ID técnico | Concepto |
|---|---|
| `00O2TOVQWROHDSV8YPN5T1S36` | Venta tarifa |
| `00O2TOVQWROH5JGC3Z8OM9PGT` | Descuentos |
| `00O2TOVQWROHDSV9SBR7263MV` | VTA FACTURADA |
| `00O2TOVQWROGPV468P733YSMA` | Rappel + Cargos |
| `00O2TOVQWROHDSV6GFY652O65` | Venta Neta |
| `00O2TOVQWROHDNZD5X3AMUFZ5` | Coste Venta |
| `00O2TOVQWROHDNZHL9NKWNV3C` | Margen Bruto |
| `00O2TOVQWROGXNTYY6Q9MF36L` | Transporte Total |
| `00O2TOVQWROHDNZHL9NKWO1EW` | Margen Distribución |
| `00O2TOVQWROGPV468P7344EW2` | Promo Trade |
| `00O2TOVQWROGPV468P7345AHU` | Marketing |
| `00O2TOVQWROHDNZHL9NKWO7QG` | Margen Comercial |

## Análisis de P&L mensual

Usa dimensión `0CALMONTH2` para desglose mensual dentro de un año:
```
bi_execute_query(
  query="ZBOKCOPA/MKT_CUENTA_RES_CP_OPT_DPCT",
  measures=["00O2TOVQWROHDSV6GFY652O65", "00O2TOVQWROHDNZHL9NKWNV3C", "00O2TOVQWROHDNZHL9NKWO7QG"],
  dimension="0CALMONTH2",
  filters={"0CALYEAR": "2025", "0VERSION": "#"}
)
```
La variable VINTMES se auto-expande a meses 01:12.

## Comparativas financieras

### YoY (año vs año)
Dos llamadas con mismo set de medidas, diferentes filtros de año. Calcular:
- Variación absoluta: actual - anterior
- Variación %: (actual - anterior) / |anterior| × 100

### MoM (mes vs mes)
Dos llamadas con diferentes `0CALMONTH`. Útil para detectar estacionalidad.

### Real vs Objetivo vs Previsión
En queries de ventas (Q002): medidas separadas para real, previsión y objetivo.
En queries P&L: filtrar `0VERSION` a `#` (real), `000` (previsión), `001` (objetivo) en llamadas separadas.

## Rentabilidad por cliente

Query `BO_RENT_CLIENTE` (27 medidas): márgenes por cliente individual.
Útil para análisis Pareto, identificar clientes de alta/baja rentabilidad.

## Indicadores de referencia KH Lloreda

- VN anual: ~54M€
- Margen Bruto: ~55%
- Margen Comercial: ~33%
- Marca dominante: KH-7 (88% ingresos)
- Segmento principal: NACIONAL
