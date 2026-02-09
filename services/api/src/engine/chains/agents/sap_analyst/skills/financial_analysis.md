# Análisis Financiero SAP (FI/CO)

## Objetivo
Análisis de datos financieros y de controlling desde SAP S/4HANA o ECC.

## Tablas Clave

### FI - Finanzas
- **BKPF**: Documentos contables (header)
- **BSEG**: Segmentos de documentos (líneas)
- **BSID**: Documentos de clientes (abonos)
- **BSIK**: Documentos de proveedores (cargos)
- **SKA1**: Plan de cuentas
- **T001**: Sociedades

### CO - Controlling
- **COSP**: Costes CO (totales)
- **COEP**: Costes CO (líneas)
- **CSKS**: Centros de coste
- **CEPC**: Centros de beneficio
- **AUFK**: Órdenes CO

## Métricas Financieras Clave

### 1. Balance General
```sql
-- Activos vs Pasivos
SELECT 
  SUM(CASE WHEN hkont LIKE '1%' THEN dmbtr ELSE 0 END) as activos,
  SUM(CASE WHEN hkont LIKE '2%' THEN dmbtr ELSE 0 END) as pasivos,
  SUM(CASE WHEN hkont LIKE '3%' THEN dmbtr ELSE 0 END) as patrimonio
FROM bseg
WHERE gjahr = [año]
```

### 2. Análisis de Flujo de Caja
- Cash in/out por período
- Días de efectivo disponible
- Proyección de liquidez

### 3. Ratio de Eficiencia
- ROI por centro de coste
- EVA (Economic Value Added)
- Coste por unidad de producción

### 4. Análisis de Varianza
```python
# Comparativo real vs presupuesto
variance_pct = (actual - budget) / abs(budget) * 100
```

## Mejores Prácticas

1. **Validación de datos**: Verificar que los períodos estén cerrados
2. **Conciliación**: Cruzar datos de FI con CO
3. **Segmentación**: Analizar por sociedad, división, área funcional
4. **Currency**: Considerar monedas y conversiones

## Reportes Típicos
- Balance Sheet
- P&L Statement
- Cash Flow Analysis
- Cost Center Reports
- Variance Analysis
