# Skill: Visualización de Datos

Este skill proporciona conocimiento para crear gráficos, charts e infografías efectivas.

## Principios de Data Visualization

### Claridad sobre Decoración
- El dato es el protagonista, no el diseño
- Elimina elementos que no aportan información (chartjunk)
- Un gráfico = una idea principal

### Selección del Gráfico Correcto

| Propósito | Tipo de Gráfico |
|-----------|-----------------|
| Comparar cantidades | Barras (horizontal o vertical) |
| Mostrar tendencia temporal | Líneas |
| Partes de un todo | Donut (no pie - más moderno) |
| Distribución | Histograma, Box plot |
| Correlación | Scatter plot |
| Ranking | Barras horizontales ordenadas |
| Progreso/Meta | Barra de progreso, gauge |

## SVG Charts Modernos

### Gráfico de Barras
```html
<svg viewBox="0 0 400 200" class="chart-bars">
  <style>
    .bar { fill: url(#gradient); transition: all 0.3s; }
    .bar:hover { filter: brightness(1.2); }
    .label { font-size: 12px; fill: #64748b; }
    .value { font-size: 14px; fill: #f8fafc; font-weight: 600; }
  </style>
  <defs>
    <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#6366f1"/>
      <stop offset="100%" style="stop-color:#8b5cf6"/>
    </linearGradient>
  </defs>
  
  <!-- Barras -->
  <rect class="bar" x="30" y="40" width="50" height="120" rx="4"/>
  <rect class="bar" x="100" y="60" width="50" height="100" rx="4"/>
  <rect class="bar" x="170" y="20" width="50" height="140" rx="4"/>
  <rect class="bar" x="240" y="80" width="50" height="80" rx="4"/>
  <rect class="bar" x="310" y="50" width="50" height="110" rx="4"/>
  
  <!-- Labels -->
  <text class="label" x="55" y="180" text-anchor="middle">Ene</text>
  <text class="label" x="125" y="180" text-anchor="middle">Feb</text>
  <text class="label" x="195" y="180" text-anchor="middle">Mar</text>
  <text class="label" x="265" y="180" text-anchor="middle">Abr</text>
  <text class="label" x="335" y="180" text-anchor="middle">May</text>
  
  <!-- Values -->
  <text class="value" x="55" y="32" text-anchor="middle">85</text>
  <text class="value" x="125" y="52" text-anchor="middle">70</text>
  <text class="value" x="195" y="12" text-anchor="middle">98</text>
  <text class="value" x="265" y="72" text-anchor="middle">55</text>
  <text class="value" x="335" y="42" text-anchor="middle">78</text>
</svg>
```

### Gráfico Donut
```html
<svg viewBox="0 0 200 200" class="chart-donut">
  <style>
    .donut-segment { transition: all 0.3s; transform-origin: center; }
    .donut-segment:hover { transform: scale(1.05); }
    .donut-center { font-size: 24px; fill: #f8fafc; font-weight: 700; }
    .donut-label { font-size: 12px; fill: #94a3b8; }
  </style>
  
  <!-- Segmentos (usar stroke-dasharray para crear arcos) -->
  <circle cx="100" cy="100" r="70" fill="none" stroke="#6366f1" stroke-width="30"
          stroke-dasharray="176 440" stroke-dashoffset="0" class="donut-segment"/>
  <circle cx="100" cy="100" r="70" fill="none" stroke="#ec4899" stroke-width="30"
          stroke-dasharray="110 440" stroke-dashoffset="-176" class="donut-segment"/>
  <circle cx="100" cy="100" r="70" fill="none" stroke="#06b6d4" stroke-width="30"
          stroke-dasharray="88 440" stroke-dashoffset="-286" class="donut-segment"/>
  <circle cx="100" cy="100" r="70" fill="none" stroke="#22c55e" stroke-width="30"
          stroke-dasharray="66 440" stroke-dashoffset="-374" class="donut-segment"/>
  
  <!-- Centro -->
  <text class="donut-center" x="100" y="95" text-anchor="middle">78%</text>
  <text class="donut-label" x="100" y="115" text-anchor="middle">Completado</text>
</svg>

<!-- Leyenda -->
<div class="chart-legend">
  <span class="legend-item"><span class="dot" style="background:#6366f1"></span> Ventas (40%)</span>
  <span class="legend-item"><span class="dot" style="background:#ec4899"></span> Marketing (25%)</span>
  <span class="legend-item"><span class="dot" style="background:#06b6d4"></span> Desarrollo (20%)</span>
  <span class="legend-item"><span class="dot" style="background:#22c55e"></span> Operaciones (15%)</span>
</div>
```

### Gráfico de Líneas
```html
<svg viewBox="0 0 400 200" class="chart-line">
  <style>
    .grid-line { stroke: #334155; stroke-width: 1; stroke-dasharray: 4; }
    .data-line { fill: none; stroke: url(#line-gradient); stroke-width: 3; stroke-linecap: round; }
    .data-area { fill: url(#area-gradient); }
    .data-point { fill: #6366f1; stroke: #f8fafc; stroke-width: 2; }
  </style>
  <defs>
    <linearGradient id="line-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#6366f1"/>
      <stop offset="100%" style="stop-color:#ec4899"/>
    </linearGradient>
    <linearGradient id="area-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#6366f1;stop-opacity:0.3"/>
      <stop offset="100%" style="stop-color:#6366f1;stop-opacity:0"/>
    </linearGradient>
  </defs>
  
  <!-- Grid lines -->
  <line class="grid-line" x1="40" y1="40" x2="380" y2="40"/>
  <line class="grid-line" x1="40" y1="80" x2="380" y2="80"/>
  <line class="grid-line" x1="40" y1="120" x2="380" y2="120"/>
  <line class="grid-line" x1="40" y1="160" x2="380" y2="160"/>
  
  <!-- Area fill -->
  <path class="data-area" d="M40,120 L108,80 L176,100 L244,40 L312,60 L380,30 L380,180 L40,180 Z"/>
  
  <!-- Line -->
  <path class="data-line" d="M40,120 L108,80 L176,100 L244,40 L312,60 L380,30"/>
  
  <!-- Points -->
  <circle class="data-point" cx="40" cy="120" r="5"/>
  <circle class="data-point" cx="108" cy="80" r="5"/>
  <circle class="data-point" cx="176" cy="100" r="5"/>
  <circle class="data-point" cx="244" cy="40" r="5"/>
  <circle class="data-point" cx="312" cy="60" r="5"/>
  <circle class="data-point" cx="380" cy="30" r="5"/>
</svg>
```

### Barra de Progreso
```html
<div class="progress-bar">
  <div class="progress-track">
    <div class="progress-fill" style="width: 72%"></div>
  </div>
  <div class="progress-info">
    <span class="progress-label">Objetivo Q4</span>
    <span class="progress-value">72%</span>
  </div>
</div>

<style>
.progress-bar {
  width: 100%;
  max-width: 400px;
}

.progress-track {
  height: 12px;
  background: #1e293b;
  border-radius: 100px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #ec4899);
  border-radius: 100px;
  transition: width 1s ease-out;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 14px;
}

.progress-label {
  color: #94a3b8;
}

.progress-value {
  color: #f8fafc;
  font-weight: 600;
}
</style>
```

## Colores para Datos

### Paleta Secuencial (valores crecientes)
```
#dbeafe → #93c5fd → #60a5fa → #3b82f6 → #2563eb → #1d4ed8
```

### Paleta Divergente (positivo/negativo)
```
#ef4444 (negativo) ← #fca5a5 ← #fef2f2 → #dcfce7 → #86efac → #22c55e (positivo)
```

### Paleta Categórica (diferentes grupos)
```
#6366f1, #ec4899, #06b6d4, #22c55e, #f59e0b, #8b5cf6
```

## Accesibilidad en Gráficos

- No depender solo del color (usar patrones o etiquetas)
- Contraste mínimo 4.5:1 para texto
- Incluir valores numéricos, no solo visual
- Etiquetas claras y descriptivas
