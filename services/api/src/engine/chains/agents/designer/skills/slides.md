# Skill: Presentaciones Modernas

Este skill te proporciona conocimiento avanzado para crear presentaciones HTML profesionales y modernas.

## Principios de Diseño

### Jerarquía Visual
- Títulos grandes y claros (48-72px)
- Subtítulos medianos (24-32px)
- Texto de cuerpo legible (18-22px)
- Máximo 3 niveles de jerarquía por slide

### Espaciado
- Usa generosamente el espacio en blanco
- Padding mínimo de 60px en los bordes
- Gap de 40px entre elementos principales
- El contenido "respira" mejor con más espacio

### Color
- Máximo 3-4 colores por presentación
- Un color de acento para destacar
- Contraste alto para legibilidad (WCAG AA mínimo)
- Gradientes sutiles para fondos modernos

## Layouts Modernos

### Layout Split (50/50)
```html
<div class="slide slide-split">
  <div class="split-content">
    <span class="badge">SECCIÓN</span>
    <h2>Título Principal</h2>
    <p>Descripción o contenido explicativo que complementa la imagen.</p>
    <ul class="features">
      <li>Punto clave uno</li>
      <li>Punto clave dos</li>
    </ul>
  </div>
  <div class="split-visual">
    <img src="imagen.jpg" alt="Descripción" />
  </div>
</div>
```

### Layout Cards Grid
```html
<div class="slide slide-cards">
  <h2>Nuestros Servicios</h2>
  <div class="cards-grid">
    <div class="card">
      <div class="card-icon">🚀</div>
      <h3>Innovación</h3>
      <p>Soluciones de vanguardia para tu negocio.</p>
    </div>
    <div class="card">
      <div class="card-icon">💡</div>
      <h3>Creatividad</h3>
      <p>Ideas frescas que marcan la diferencia.</p>
    </div>
    <div class="card">
      <div class="card-icon">📈</div>
      <h3>Crecimiento</h3>
      <p>Estrategias que impulsan resultados.</p>
    </div>
  </div>
</div>
```

### Layout Stats/Números
```html
<div class="slide slide-stats">
  <h2>Resultados que Hablan</h2>
  <div class="stats-grid">
    <div class="stat">
      <span class="stat-number">98%</span>
      <span class="stat-label">Satisfacción</span>
    </div>
    <div class="stat">
      <span class="stat-number">+500</span>
      <span class="stat-label">Clientes</span>
    </div>
    <div class="stat">
      <span class="stat-number">24/7</span>
      <span class="stat-label">Soporte</span>
    </div>
  </div>
</div>
```

### Layout Quote/Testimonio
```html
<div class="slide slide-quote">
  <blockquote>
    <p>"Esta solución transformó completamente nuestra forma de trabajar. Los resultados superaron todas nuestras expectativas."</p>
    <footer>
      <cite>María García</cite>
      <span>CEO, TechCorp</span>
    </footer>
  </blockquote>
</div>
```

### Layout Timeline
```html
<div class="slide slide-timeline">
  <h2>Nuestra Historia</h2>
  <div class="timeline">
    <div class="timeline-item">
      <span class="timeline-year">2020</span>
      <h3>Fundación</h3>
      <p>Inicio del proyecto con 3 personas.</p>
    </div>
    <div class="timeline-item">
      <span class="timeline-year">2022</span>
      <h3>Expansión</h3>
      <p>Crecimiento a 50 empleados.</p>
    </div>
    <div class="timeline-item">
      <span class="timeline-year">2024</span>
      <h3>Liderazgo</h3>
      <p>Referentes en el sector.</p>
    </div>
  </div>
</div>
```

## CSS Moderno Completo

```css
/* === RESET Y BASE === */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* === VARIABLES DE TEMA === */
:root {
  --primary: #6366f1;
  --primary-dark: #4f46e5;
  --secondary: #ec4899;
  --accent: #06b6d4;
  --dark: #0f172a;
  --dark-soft: #1e293b;
  --light: #f8fafc;
  --gray: #64748b;
  --success: #22c55e;
  --warning: #f59e0b;
  
  --font-display: 'Inter', system-ui, sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;
  
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1);
  --shadow-xl: 0 25px 50px -12px rgba(0,0,0,0.25);
  
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
}

/* === SLIDE BASE === */
.slide {
  width: 100%;
  min-height: 100vh;
  padding: 80px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background: var(--dark);
  color: var(--light);
  font-family: var(--font-body);
  position: relative;
  overflow: hidden;
}

/* Fondo con gradiente sutil */
.slide::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(ellipse at top right, rgba(99, 102, 241, 0.15), transparent 50%),
              radial-gradient(ellipse at bottom left, rgba(236, 72, 153, 0.1), transparent 50%);
  pointer-events: none;
}

.slide > * {
  position: relative;
  z-index: 1;
}

/* === TIPOGRAFÍA === */
h1 {
  font-size: 72px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin-bottom: 24px;
  background: linear-gradient(135deg, var(--light) 0%, var(--gray) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

h2 {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 32px;
  color: var(--light);
}

h3 {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--light);
}

p {
  font-size: 20px;
  line-height: 1.6;
  color: var(--gray);
  max-width: 600px;
}

/* === BADGE === */
.badge {
  display: inline-block;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  color: white;
  border-radius: 100px;
  margin-bottom: 24px;
}

/* === SLIDE SPLIT === */
.slide-split {
  flex-direction: row;
  gap: 80px;
  padding: 60px 80px;
}

.split-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.split-visual {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.split-visual img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: cover;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
}

/* === CARDS === */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 32px;
  margin-top: 48px;
}

.card {
  background: var(--dark-soft);
  padding: 40px;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255,255,255,0.1);
  transition: all 0.3s ease;
}

.card:hover {
  transform: translateY(-8px);
  border-color: var(--primary);
  box-shadow: 0 20px 40px rgba(99, 102, 241, 0.2);
}

.card-icon {
  font-size: 48px;
  margin-bottom: 24px;
}

.card h3 {
  font-size: 24px;
  margin-bottom: 12px;
}

.card p {
  font-size: 16px;
  color: var(--gray);
}

/* === STATS === */
.stats-grid {
  display: flex;
  justify-content: center;
  gap: 80px;
  margin-top: 60px;
}

.stat {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 80px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--primary), var(--accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}

.stat-label {
  display: block;
  font-size: 18px;
  color: var(--gray);
  margin-top: 16px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

/* === QUOTE === */
.slide-quote {
  text-align: center;
  padding: 100px;
}

.slide-quote blockquote {
  max-width: 900px;
  margin: 0 auto;
}

.slide-quote p {
  font-size: 36px;
  font-style: italic;
  line-height: 1.5;
  color: var(--light);
  max-width: none;
}

.slide-quote footer {
  margin-top: 40px;
}

.slide-quote cite {
  display: block;
  font-size: 24px;
  font-weight: 600;
  font-style: normal;
  color: var(--light);
}

.slide-quote footer span {
  font-size: 16px;
  color: var(--gray);
}

/* === TIMELINE === */
.timeline {
  display: flex;
  justify-content: space-between;
  margin-top: 60px;
  position: relative;
}

.timeline::before {
  content: '';
  position: absolute;
  top: 24px;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--primary), var(--secondary));
}

.timeline-item {
  flex: 1;
  text-align: center;
  padding: 0 20px;
}

.timeline-year {
  display: inline-block;
  padding: 12px 24px;
  background: var(--primary);
  color: white;
  font-weight: 700;
  border-radius: 100px;
  margin-bottom: 24px;
  position: relative;
  z-index: 1;
}

.timeline-item h3 {
  font-size: 22px;
  margin-bottom: 12px;
}

.timeline-item p {
  font-size: 16px;
  max-width: none;
}

/* === BULLETS/LISTA === */
.features {
  list-style: none;
  margin-top: 32px;
}

.features li {
  font-size: 18px;
  color: var(--light);
  padding: 12px 0;
  padding-left: 32px;
  position: relative;
}

.features li::before {
  content: '→';
  position: absolute;
  left: 0;
  color: var(--primary);
  font-weight: bold;
}

/* === ANIMACIONES === */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-50px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Aplicar animaciones */
.slide h1, .slide h2 {
  animation: fadeInUp 0.8s ease-out;
}

.slide p, .slide .badge {
  animation: fadeInUp 0.8s ease-out 0.2s both;
}

.card {
  animation: scaleIn 0.6s ease-out;
}

.card:nth-child(2) { animation-delay: 0.1s; }
.card:nth-child(3) { animation-delay: 0.2s; }

.stat {
  animation: fadeInUp 0.8s ease-out;
}

.stat:nth-child(2) { animation-delay: 0.15s; }
.stat:nth-child(3) { animation-delay: 0.3s; }

/* === SLIDE TÍTULO (PORTADA) === */
.slide-title {
  text-align: center;
  justify-content: center;
  align-items: center;
}

.slide-title h1 {
  font-size: 84px;
}

.slide-title .subtitle {
  font-size: 28px;
  color: var(--gray);
  margin-top: 16px;
}

/* === TEMAS ALTERNATIVOS === */

/* Tema Claro */
.theme-light .slide {
  background: var(--light);
  color: var(--dark);
}

.theme-light .slide::before {
  background: radial-gradient(ellipse at top right, rgba(99, 102, 241, 0.1), transparent 50%);
}

.theme-light h1, .theme-light h2, .theme-light h3 {
  color: var(--dark);
}

.theme-light .card {
  background: white;
  border-color: rgba(0,0,0,0.1);
}

/* Tema Gradiente */
.theme-gradient .slide {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.theme-gradient .slide::before {
  display: none;
}

/* Tema Tech */
.theme-tech .slide {
  background: #0a0a0f;
}

.theme-tech .slide::before {
  background: 
    radial-gradient(ellipse at top, rgba(0, 255, 136, 0.1), transparent 50%),
    radial-gradient(ellipse at bottom, rgba(0, 136, 255, 0.1), transparent 50%);
}

.theme-tech .badge {
  background: linear-gradient(135deg, #00ff88, #00aaff);
  color: #0a0a0f;
}

.theme-tech .stat-number {
  background: linear-gradient(135deg, #00ff88, #00aaff);
  -webkit-background-clip: text;
  background-clip: text;
}
```

## Ejemplos de Slides Completas

### Slide de Portada
```html
<div class="slide slide-title">
  <span class="badge">2024</span>
  <h1>Innovación Digital</h1>
  <p class="subtitle">Transformando el futuro de los negocios</p>
</div>
```

### Slide de Problema/Solución
```html
<div class="slide slide-split">
  <div class="split-content">
    <span class="badge">EL DESAFÍO</span>
    <h2>Las empresas pierden el 40% de su tiempo en tareas repetitivas</h2>
    <p>La automatización inteligente puede liberar ese tiempo para lo que realmente importa: innovar y crecer.</p>
    <ul class="features">
      <li>Procesos manuales lentos y propensos a errores</li>
      <li>Datos dispersos sin insights accionables</li>
      <li>Equipos sobrecargados con tareas rutinarias</li>
    </ul>
  </div>
  <div class="split-visual">
    <img src="problem-illustration.jpg" alt="Ilustración del problema" />
  </div>
</div>
```

### Slide de Cierre/CTA
```html
<div class="slide slide-title">
  <span class="badge">PRÓXIMOS PASOS</span>
  <h1>¿Listo para transformar tu negocio?</h1>
  <p class="subtitle">Agenda una demo personalizada y descubre el potencial</p>
  <div style="margin-top: 48px;">
    <a href="#" class="cta-button">Solicitar Demo</a>
  </div>
</div>

<style>
.cta-button {
  display: inline-block;
  padding: 20px 48px;
  font-size: 18px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  border-radius: 100px;
  text-decoration: none;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
}

.cta-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(99, 102, 241, 0.5);
}
</style>
```

## Checklist de Calidad

Antes de generar una presentación, verifica:

- [ ] Jerarquía visual clara (título > subtítulo > contenido)
- [ ] Máximo 3-4 puntos por slide (menos es más)
- [ ] Espacio en blanco generoso (padding mínimo 60-80px)
- [ ] Contraste adecuado entre texto y fondo
- [ ] Animaciones sutiles (no excesivas)
- [ ] Consistencia en colores y tipografía
- [ ] Imágenes de alta calidad cuando se incluyan
- [ ] Call-to-action claro en slide final

## Cuándo Usar Cada Layout

| Tipo de Contenido | Layout Recomendado |
|-------------------|-------------------|
| Título/Portada | slide-title |
| Concepto + Visual | slide-split |
| Lista de servicios/features | slide-cards |
| Métricas/KPIs | slide-stats |
| Testimonio/Cita | slide-quote |
| Historia/Evolución | slide-timeline |
| Puntos clave | slide con bullets (.features) |
