# Skill: Design Critique - Criterios de Auto-Evaluación

Este skill te enseña a evaluar tus propias creaciones y decidir si entregar o regenerar.

## CUÁNDO USAR ESTE SKILL

Carga este skill ANTES de usar `analyze_image` para auto-revisión.
Te ayudará a interpretar los resultados del análisis.

---

## CRITERIOS POR TIPO DE DISEÑO

### 1. LOGOS

**Criterios técnicos:**
- [ ] Legible a tamaños pequeños (favicon 32x32)
- [ ] Funciona en fondo claro Y oscuro
- [ ] Formas reconocibles sin color (versión monocroma)
- [ ] Sin detalles excesivos que se pierdan al escalar

**Criterios de diseño:**
- [ ] Transmite la esencia de la marca
- [ ] Memorable y distintivo
- [ ] Simple pero no genérico
- [ ] Apropiado para el sector/industria

**Umbrales:**
- Puntuación >= 7/10 → Entregar
- Puntuación 5-6 → Mejorar prompt y regenerar
- Puntuación < 5 → Cambiar enfoque completamente

### 2. ILUSTRACIONES

**Criterios técnicos:**
- [ ] Composición equilibrada
- [ ] Resolución adecuada (sin artefactos visibles)
- [ ] Colores coherentes con el contexto
- [ ] Estilo consistente en toda la imagen

**Criterios de contenido:**
- [ ] Representa lo solicitado
- [ ] Elementos principales claramente visibles
- [ ] Sin elementos extraños o fuera de contexto
- [ ] Proporción correcta de elementos

**Umbrales:**
- Puntuación >= 6/10 → Aceptable para uso general
- Para uso principal/destacado → Exigir >= 8/10

### 3. GRÁFICOS DE DATOS / INFOGRAFÍAS

**Criterios técnicos:**
- [ ] Datos legibles y correctos
- [ ] Ejes y leyendas claras
- [ ] Colores diferenciables
- [ ] Escala apropiada

**Criterios de comunicación:**
- [ ] El mensaje principal es evidente
- [ ] No hay distorsión de datos
- [ ] Jerarquía visual correcta
- [ ] Título descriptivo

**Umbrales:**
- Siempre >= 8/10 (la precisión es crítica)
- Si hay errores en datos → NUNCA entregar, regenerar

### 4. IMÁGENES PARA PRESENTACIONES

**Criterios técnicos:**
- [ ] Aspecto ratio correcto para slides (16:9 o similar)
- [ ] No compite con el texto superpuesto
- [ ] Colores compatibles con el tema de la presentación

**Criterios de uso:**
- [ ] Relevante al contenido de la slide
- [ ] Estilo coherente con otras imágenes de la presentación
- [ ] Impacto visual apropiado (no distrae, complementa)

**Umbrales:**
- Puntuación >= 6/10 → Aceptable
- Para slide de título/portada → Exigir >= 8/10

---

## CÓMO MEJORAR PROMPTS TRAS FEEDBACK NEGATIVO

### Si el análisis indica problemas de ESTILO:
```
Prompt original: "logo for fitness app"
Mejorado: "minimalist vector logo for fitness app, clean geometric shapes, 
          single color, scalable design, professional corporate style"
```

### Si el análisis indica problemas de CONTENIDO:
```
Prompt original: "illustration of team working"
Mejorado: "diverse team of 4 people collaborating around a table with laptops,
          modern office setting, warm lighting, isometric view, flat design"
```

### Si el análisis indica problemas de COMPOSICIÓN:
```
Prompt original: "banner for website"
Mejorado: "website hero banner 16:9 ratio, subject on left third for text overlay,
          gradient background from blue to purple, minimalist, negative space on right"
```

### Patrones de mejora:
1. **Más específico** → Añadir detalles concretos
2. **Estilo definido** → Nombrar estilo artístico (flat, isometric, photorealistic)
3. **Restricciones técnicas** → Mencionar ratio, tamaño, uso de espacio
4. **Contexto de uso** → Para qué se usará (web, print, icon)

---

## FLUJO DE DECISIÓN

```
┌─────────────────────────────────────────┐
│  Generar imagen                          │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│  analyze_image(type="critique")          │
└─────────────────┬───────────────────────┘
                  ▼
         ┌───────────────┐
         │ Puntuación?   │
         └───────┬───────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
  < 5/10      5-7/10       >= 8/10
    │            │            │
    ▼            ▼            ▼
 Cambiar     Ajustar      Entregar
 enfoque     prompt       resultado
    │            │
    └─────┬──────┘
          ▼
    Regenerar (máx 2 intentos)
```

---

## SEÑALES DE ALERTA (NUNCA ENTREGAR)

- ❌ Texto ilegible o corrupto en la imagen
- ❌ Proporciones humanas incorrectas (manos, caras)
- ❌ Artefactos visuales evidentes
- ❌ Elementos que no corresponden con lo solicitado
- ❌ Logos que parecen genéricos/stock
- ❌ Gráficos con datos visualmente incorrectos

---

## EJEMPLO DE USO COMPLETO

```
1. Tarea: "Logo minimalista para app de meditación MindFlow"

2. load_skill("branding")  # Para técnicas de creación
3. load_skill("design_critique")  # Para evaluación

4. generate_image("minimalist zen logo for meditation app MindFlow, 
                   flowing water droplet forming letter M, 
                   calm blue gradient, vector style, scalable")

5. analyze_image(analysis_type="compare", 
                 context="Logo minimalista meditación, debe ser: calmado, 
                          simple, memorable, funcionar en pequeño")

6. Interpretar resultado:
   - Si >= 7/10 y cumple criterios → deliver_result()
   - Si < 7 pero cerca → mejorar prompt específicamente
   - Si < 5 → cambiar concepto (quizás otra metáfora visual)
```
