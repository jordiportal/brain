# Mejoras de Visibilidad en SAP Agent

## 🎯 Objetivo

Proporcionar visibilidad completa de los pasos intermedios que realiza el SAP Agent durante la ejecución, permitiendo al usuario ver en tiempo real:
- Qué está haciendo el agente
- Qué herramientas está usando
- Qué resultados está obteniendo
- Cuándo está sintetizando la respuesta

## 📊 Estructura de Pasos Visibles

### 1. **🔍 Cargando herramientas SAP**
**Propósito**: Mostrar que se están cargando las herramientas disponibles

**Información mostrada**:
- Número de endpoints SAP disponibles
- Estado de carga

**Ejemplo**:
```
🔍 Cargando herramientas SAP
Analizando consulta y cargando herramientas SAP disponibles...

✅ 37 endpoints SAP disponibles
```

---

### 2. **🤔 Análisis con IA (iteración X/Y)**
**Propósito**: Mostrar que la IA está analizando la consulta y seleccionando herramientas

**Información mostrada**:
- Número de iteración actual
- Provider de LLM usado (OpenAI, Ollama, etc.)
- Herramientas seleccionadas

**Ejemplo**:
```
🤔 Análisis con IA (iteración 1/2)
Analizando consulta y seleccionando herramientas apropiadas...

✅ Herramientas seleccionadas: Get Api Users
```

---

### 3. **⚙️ [Nombre de Herramienta]** (Por cada tool ejecutada)
**Propósito**: Mostrar la ejecución de cada herramienta SAP

**Información mostrada**:
- Nombre legible de la herramienta
- Estado de ejecución
- Resultado (número de registros, éxito/error)

**Ejemplo**:
```
⚙️ Get Api Users
Ejecutando consulta a SAP...

✅ Datos recibidos: 100 usuarios
```

---

### 4. **📊 Sintetizando respuesta**
**Propósito**: Indicar que se está generando la respuesta final con los datos

**Información mostrada**:
- Número de herramientas ejecutadas
- Estado de síntesis

**Ejemplo**:
```
📊 Sintetizando respuesta
Generando respuesta con los datos obtenidos...
```

---

### 5. **Respuesta Final**
**Propósito**: Mostrar la respuesta del agente en el área principal del chat

**Ubicación**: Área principal (no en paso colapsable)

**Ejemplo**:
```
Here is the list of SAP users:

1. ADRIAMELLADO - Adrià Mellado Fernández
2. ADRIASERRANO - Adrià Serrano Fitó
...
```

## 🔄 Flow Completo de Eventos

### Arquitectura de Eventos

```
Usuario: "Get SAP users"
    ↓
┌─────────────────────────────────────────┐
│ 🔍 Cargando herramientas SAP           │
│ - node_start("sap_loading")            │
│ - token("Analizando consulta...")      │
│ - token("✅ 37 endpoints disponibles")  │
│ - node_end("sap_loading")              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 🤔 Análisis con IA (iteración 1/2)    │
│ - node_start("ai_analysis_1")          │
│ - token("Analizando consulta...")      │
│ - token("✅ Herramientas seleccionadas")│
│ - node_end("ai_analysis_1")            │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ ⚙️ Get Api Users                       │
│ - node_start("tool_1_1")               │
│ - token("Ejecutando consulta...")      │
│ - token("✅ Datos recibidos: 100")     │
│ - node_end("tool_1_1")                 │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 📊 Sintetizando respuesta              │
│ - node_start("synthesis_1")            │
│ - token("Generando respuesta...")      │
│ - node_end("synthesis_1")              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 🤔 Análisis con IA (iteración 2/2)    │
│ - node_start("ai_analysis_2")          │
│ - token("Analizando consulta...")      │
│ - node_end("ai_analysis_2")            │
└─────────────────────────────────────────┘
    ↓
[Respuesta Final en área principal]
token(node_id="", content="Here is the list...")
```

## 🎨 Presentación en GUI

### Pasos Colapsables (Intermediate Steps)

Cada paso aparece como un bloque colapsable en el chat con:
- **Título**: Nombre del paso con icono
- **Estado**: 
  - 🟡 En progreso (spinner)
  - 🟢 Completado (checkmark)
  - 🔴 Error (X)
- **Contenido**: Mensajes acumulados durante el paso
- **Duración**: Tiempo que tomó el paso

**Ejemplo Visual**:
```
┌─────────────────────────────────────────┐
│ ✓ 🔍 Cargando herramientas SAP (1.2s) ▼│
│ Analizando consulta y cargando         │
│ herramientas SAP disponibles...         │
│                                         │
│ ✅ 37 endpoints SAP disponibles         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ✓ 🤔 Análisis con IA (iteración 1/2... ▼│
│ Analizando consulta y seleccionando    │
│ herramientas apropiadas...              │
│                                         │
│ ✅ Herramientas seleccionadas: Get...  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ✓ ⚙️ Get Api Users (0.8s)              ▼│
│ Ejecutando consulta a SAP...           │
│                                         │
│ ✅ Datos recibidos: 100 usuarios        │
└─────────────────────────────────────────┘
```

### Respuesta Final

Aparece en el área principal del chat, sin bloque colapsable:
```
Here is the list of SAP users:

1. ADRIAMELLADO - Adrià Mellado Fernández
2. ADRIASERRANO - Adrià Serrano Fitó
...
```

## 🔧 Implementación Técnica

### Código Modificado

**Archivo**: `/services/api/src/engine/chains/sap_agent.py`

#### 1. Paso de Carga de Herramientas
```python
# Iniciar paso
yield StreamEvent(
    event_type="node_start",
    execution_id=execution_id,
    node_id="sap_loading",
    node_name="🔍 Cargando herramientas SAP",
    data={"query": query, "loading_tools": True}
)

# Contenido del paso
yield StreamEvent(
    event_type="token",
    execution_id=execution_id,
    node_id="sap_loading",  # ← Clave: mismo node_id
    content="Analizando consulta..."
)

# Finalizar paso
yield StreamEvent(
    event_type="node_end",
    execution_id=execution_id,
    node_id="sap_loading",
    data={"tools_loaded": len(sap_tools)}
)
```

#### 2. Paso de Análisis con IA
```python
analysis_node_id = f"ai_analysis_{iteration}"

yield StreamEvent(
    event_type="node_start",
    node_id=analysis_node_id,
    node_name=f"🤔 Análisis con IA (iteración {iteration}/{max_iterations})"
)

# ... contenido ...

yield StreamEvent(
    event_type="node_end",
    node_id=analysis_node_id
)
```

#### 3. Paso de Ejecución de Herramienta
```python
tool_node_id = f"tool_{iteration}_{idx}"
tool_display_name = tool_name.replace("sap_btp_gateway_", "").replace("_", " ").title()

yield StreamEvent(
    event_type="node_start",
    node_id=tool_node_id,
    node_name=f"⚙️ {tool_display_name}"
)

# ... ejecución ...

yield StreamEvent(
    event_type="node_end",
    node_id=tool_node_id,
    data={"success": result.get("success")}
)
```

### Frontend (chains.component.ts)

El frontend ya está preparado para manejar estos eventos:

```typescript
if (data.event_type === 'node_start') {
  // Crear nuevo paso intermedio
  intermediateSteps.push({
    id: data.node_id,
    name: data.node_name,
    status: 'running',
    content: '',
    startTime: new Date()
  });
}

if (data.event_type === 'token' && data.node_id) {
  // Agregar contenido al paso activo
  stepContentBuffer += data.content;
  step.content = stepContentBuffer;
}

if (data.event_type === 'node_end') {
  // Marcar paso como completado
  step.status = 'completed';
  step.endTime = new Date();
}
```

## ✅ Beneficios

1. **Transparencia**: El usuario ve exactamente qué está haciendo el agente
2. **Debug**: Facilita identificar dónde falla el proceso si hay errores
3. **Confianza**: El usuario puede verificar que las herramientas correctas se están usando
4. **UX**: Mejor experiencia al ver progreso en tiempo real
5. **Performance**: Se pueden identificar cuellos de botella (pasos lentos)

## 🔄 Compatibilidad

- ✅ Funciona con OpenAI
- ✅ Funciona con Ollama
- ✅ Funciona con cualquier provider
- ✅ Compatible con streaming
- ✅ Compatible con modo no-streaming

## 📝 Ejemplo de Salida Completa

```
┌─────────────────────────────────────────┐
│ ✓ 🔍 Cargando herramientas SAP (1.2s)  │ ◀─ Paso colapsable
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ✓ 🤔 Análisis con IA (iteración 1/2)... │ ◀─ Paso colapsable
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ✓ ⚙️ Get Api Users (0.8s)              │ ◀─ Paso colapsable
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ✓ 📊 Sintetizando respuesta (0.3s)     │ ◀─ Paso colapsable
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ✓ 🤔 Análisis con IA (iteración 2/2)... │ ◀─ Paso colapsable
└─────────────────────────────────────────┘

Here is the list of SAP users:          ◀─ Respuesta final (área principal)

1. ADRIAMELLADO - Adrià Mellado Fernández
2. ADRIASERRANO - Adrià Serrano Fitó
...
```

## 🚀 Testing

Para probar la visibilidad mejorada, accede al GUI en:
```
http://localhost:4200
```

Y realiza una consulta SAP. Verás todos los pasos intermedios desplegados.
