# Admin Orchestrator Agent - Implementación

## Resumen Ejecutivo

Se ha implementado una **nueva capa arquitectónica** para coordinación de tareas administrativas, separando las responsabilidades de **coordinación** (decidir QUÉ hacer) y **ejecución** (implementar CÓMO hacerlo).

### Arquitectura Implementada

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR PRINCIPAL                    │
│              (Coordinador General del Sistema)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Delega tareas administrativas a:
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              ADMIN ORCHESTRATOR AGENT (NUEVO)                │
│                   Coordinador Administrativo                 │
│                                                               │
│  - Analiza estrategia (directa, con conocimiento, etc.)     │
│  - Consulta RAG si necesita info sobre sitios/APIs          │
│  - Coordina secuencia de agentes especializados             │
│  - Presenta resultados coordinados                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┬───────────────┐
          ↓                ↓                ↓               ↓
    ┌──────────┐   ┌──────────────┐  ┌──────────┐  ┌──────────┐
    │   RAG    │   │ PERSISTENT   │  │  TOOL    │  │CONVERSA- │
    │  Agent   │   │ ADMIN AGENT  │  │  Agent   │  │  TIONAL  │
    │          │   │  (Executor)  │  │          │  │          │
    └──────────┘   └──────────────┘  └──────────┘  └──────────┘
                          │
                          │ Ejecuta código en:
                          ↓
                   ┌──────────────┐
                   │ CONTENEDOR   │
                   │ PERSISTENTE  │
                   │ + VOLUMEN    │
                   └──────────────┘
```

## Agentes Modificados

### 1. Admin Orchestrator Agent (NUEVO)

**Archivo**: `services/api/src/engine/chains/admin_orchestrator_agent.py`

**Responsabilidades**:
- Analizar peticiones administrativas del usuario
- Decidir estrategia de ejecución:
  - `DIRECTA`: Delegar directamente al Persistent Admin
  - `CON_CONOCIMIENTO`: Consultar RAG primero, luego ejecutar
  - `EXPLORATORIA`: Usar Tool Agent para obtener info, luego ejecutar
  - `MULTI_PASO`: Coordinar múltiples agentes en secuencia
- Coordinar flujo de información entre agentes
- Presentar resultados finales coordinados

**Nodos**:
1. `analyzer`: Analiza petición y decide estrategia (LLM, temp 0.2)
2. `knowledge_gatherer`: Consulta RAG si es necesario (TOOL)
3. `executor`: Ejecuta plan paso a paso delegando (TOOL)
4. `synthesizer`: Presenta resultados finales (LLM, temp 0.5)

**Prompts Clave**:
- **Analyzer**: Recibe petición → Decide tipo de tarea (download/scraping/monitoring/scheduling/integration) → Elige estrategia → Genera plan de pasos
- **Synthesizer**: Recibe resultados de todos los pasos → Presenta respuesta final al usuario

**Ejemplo de Output del Analyzer**:
```json
{
  "task_type": "download",
  "complexity": "medium",
  "strategy": "DIRECTA",
  "needs_knowledge": false,
  "execution_plan": [
    {"step": 1, "agent": "persistent_admin", "task": "Descarga 2 archivos .7z de https://archive.org/download/..."}
  ],
  "reasoning": "Es una descarga de directorio web, el Persistent Admin puede explorar y descargar directamente"
}
```

### 2. Persistent Admin Agent (MODIFICADO)

**Archivo**: `services/api/src/engine/chains/persistent_admin_agent.py`

**Cambios**:
- **Prompt simplificado**: Ahora recibe instrucciones específicas sobre QUÉ hacer (no decide estrategias)
- **Más ejemplos de código**: Se agregaron 6 ejemplos completos:
  - DOWNLOAD SIMPLE: Un archivo directo
  - WEB SCRAPING + DOWNLOAD: Directorio de archivos (con BeautifulSoup)
  - CRON/SCHEDULE: Tarea periódica
  - MONITOR: Detectar cambios en web/API
  - API INTEGRATION: Llamadas a APIs externas
  - (Ya existían ejemplos de estructura básica)

**Nuevo Ejemplo Agregado** (relevante para el caso de uso):
```python
# WEB SCRAPING + DOWNLOAD (directorio de archivos)
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

# URL base del directorio
base_url = "https://archive.org/download/example/"
downloads_dir = Path("/workspace/downloads")
downloads_dir.mkdir(exist_ok=True)

log(f"Obteniendo listado de: {base_url}")

# 1. Obtener la página HTML
response = requests.get(base_url, timeout=60)
response.raise_for_status()
html = response.text

# 2. Parsear HTML con BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

# 3. Buscar enlaces a archivos .7z (o la extensión que necesites)
links = soup.find_all('a', href=True)
target_files = [link['href'] for link in links if link['href'].endswith('.7z')]

log(f"Encontrados {len(target_files)} archivos .7z")

# 4. Descargar archivos (limitar a 2 para pruebas)
max_downloads = 2
for i, filename in enumerate(target_files[:max_downloads], 1):
    # Construir URL completa
    if filename.startswith('http'):
        file_url = filename
    else:
        file_url = urljoin(base_url, filename)
    
    # Nombre local
    local_filename = filename.split('/')[-1]
    local_path = downloads_dir / local_filename
    
    log(f"[{i}/{max_downloads}] Descargando: {local_filename}")
    
    try:
        file_response = requests.get(file_url, timeout=300, stream=True)
        file_response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        size_mb = local_path.stat().st_size / (1024 * 1024)
        log(f"✅ Descargado: {local_filename} ({size_mb:.2f} MB)")
    except Exception as e:
        log(f"❌ Error descargando {local_filename}: {e}")

log(f"Proceso completado. Archivos en: {downloads_dir}")
```

**Filosofía del Cambio**:
- **Antes**: El agente decidía estrategias y generaba código
- **Ahora**: El agente solo implementa (recibe "qué hacer" y genera el "cómo")
- **Ventaja**: Más especializado, ejemplos concretos, menos decisiones → mejor calidad de código

### 3. Orchestrator Principal (MODIFICADO)

**Archivo**: `services/api/src/engine/chains/orchestrator_agent.py`

**Cambios**:
1. **Prompt del Planner actualizado**: Ahora conoce al `admin_orchestrator`
   - "Para tareas administrativas (descargas web, scraping, monitoreo, scheduling, automatización), usa `admin_orchestrator`"

2. **Función `select_default_agent()` actualizada**: 
   - Ahora detecta keywords administrativas con **alta prioridad**
   - Keywords: "descarga", "download", "scraping", "monitorea", "programa", "schedule", "cron", "automatiza"
   - Si detecta cualquiera de estos, devuelve `admin_orchestrator`

**Ejemplo de Flujo**:
```
Usuario: "Descarga 2 archivos .7z de archive.org"
    ↓
Orchestrator Principal analiza → detecta "descarga"
    ↓
Delega a: admin_orchestrator
    ↓
Admin Orchestrator analiza → estrategia DIRECTA
    ↓
Delega a: persistent_admin
    ↓
Persistent Admin genera código de scraping + download
    ↓
Ejecuta en contenedor persistente
    ↓
Admin Orchestrator presenta resultados
    ↓
Orchestrator Principal devuelve respuesta final
```

## Flujos de Coordinación

### Flujo 1: Tarea Administrativa Simple (Estrategia DIRECTA)

**Ejemplo**: "Descarga 2 archivos .7z de https://archive.org/download/sonyplaystationasiantscj20151103"

```
1. Usuario → Orchestrator Principal
2. Orchestrator → Detecta "descarga" → Admin Orchestrator
3. Admin Orchestrator:
   a. Analyzer: task_type=download, strategy=DIRECTA
   b. Executor: Delega a persistent_admin con instrucción específica
4. Persistent Admin:
   a. Planner: needs_code=true, task_type=download
   b. Code Generator: Genera script con BeautifulSoup + requests
   c. Executor: Ejecuta en contenedor
   d. Synthesizer: "He descargado 2 archivos .7z en /workspace/downloads/..."
5. Admin Orchestrator:
   - Synthesizer: Presenta resultado final coordinado
6. Orchestrator Principal → Usuario
```

### Flujo 2: Tarea con Conocimiento Previo (Estrategia CON_CONOCIMIENTO)

**Ejemplo**: "Descarga datos del API de SAP que está documentado en nuestros manuales"

```
1. Usuario → Orchestrator Principal
2. Orchestrator → Detecta "descarga" → Admin Orchestrator
3. Admin Orchestrator:
   a. Analyzer: task_type=integration, strategy=CON_CONOCIMIENTO, needs_knowledge=true
   b. Knowledge Gatherer: Consulta RAG → "Buscar documentación sobre API SAP y credenciales"
   c. RAG Agent: Devuelve documentación + endpoints + autenticación
   d. Executor: Delega a persistent_admin con contexto del RAG
4. Persistent Admin:
   a. Recibe contexto (URL, headers, auth)
   b. Genera script de integración con API
   c. Ejecuta llamada y guarda resultado
5. Admin Orchestrator:
   - Synthesizer: "He consultado la documentación SAP y descargado los datos de..."
6. Orchestrador Principal → Usuario
```

### Flujo 3: Monitoreo Continuo (Estrategia MULTI_PASO)

**Ejemplo**: "Monitorea esta web cada hora y descarga nuevos archivos si aparecen"

```
1. Usuario → Orchestrator Principal
2. Orchestrator → Detecta "monitorea" → Admin Orchestrator
3. Admin Orchestrator:
   a. Analyzer: task_type=monitoring, strategy=MULTI_PASO
   b. Plan:
      - Paso 1: persistent_admin → Crear script de monitoreo con APScheduler
      - Paso 2: persistent_admin → Guardar script en /workspace/scripts/monitor_xxx.py
      - Paso 3: conversational → Explicar cómo activar el monitoreo continuo
4. Cada Paso Ejecutado en Secuencia
5. Admin Orchestrator:
   - Synthesizer: "He creado el script de monitoreo en /workspace/scripts/..., para ejecutarlo continuamente..."
6. Orchestrator Principal → Usuario
```

## Ventajas de la Nueva Arquitectura

### 1. Separación de Responsabilidades
- **Admin Orchestrator**: Decide estrategias (nivel alto)
- **Persistent Admin**: Implementa código (nivel bajo)
- **Resultado**: Cada agente hace lo que mejor sabe hacer

### 2. Escalabilidad
- Es fácil agregar nuevas estrategias al Admin Orchestrator
- Es fácil agregar más ejemplos al Persistent Admin
- Los cambios en uno no afectan al otro

### 3. Reutilización de Conocimiento
- El Admin Orchestrator puede consultar RAG para sitios conocidos
- El conocimiento sobre cómo scrappear sitios específicos se puede guardar en documentos
- La próxima vez que se pida descargar del mismo sitio, ya tendremos la info

### 4. Prompts Más Focalizados
- **Admin Orchestrator**: Prompt enfocado en decisiones estratégicas (0.2 temp)
- **Persistent Admin**: Prompt lleno de ejemplos de código (0.3 temp)
- **Resultado**: Mejor calidad en ambos niveles

### 5. Debugging Más Fácil
- Si falla la estrategia → revisar Admin Orchestrator
- Si falla el código → revisar Persistent Admin
- Los logs muestran claramente qué agente tomó qué decisión

## Prueba del Caso de Uso Original

### Petición del Usuario
```
"Descarga 2 archivos .7z de https://archive.org/download/sonyplaystationasiantscj20151103"
```

### Flujo Esperado

1. **Orchestrator Principal**:
   - Detecta keyword "descarga"
   - Delega a `admin_orchestrator`

2. **Admin Orchestrator (Analyzer)**:
   - task_type: `download`
   - strategy: `DIRECTA` (no necesita consultar RAG, es un directorio web estándar)
   - Plan: Un solo paso con `persistent_admin`

3. **Persistent Admin**:
   - Genera código basado en el ejemplo de "WEB SCRAPING + DOWNLOAD"
   - Código hace:
     1. `requests.get(url)` para obtener HTML
     2. `BeautifulSoup` para parsear y encontrar enlaces `.7z`
     3. Construir URLs completas con `urljoin`
     4. Descargar primeros 2 archivos con streaming
     5. Guardar en `/workspace/downloads/`
   - Ejecuta en contenedor persistente
   - Timeout: 300 segundos (suficiente para descargas grandes)

4. **Admin Orchestrator (Synthesizer)**:
   - Presenta resultados: "He descargado 2 archivos .7z de archive.org en /workspace/downloads/..."

### Comando de Prueba

```bash
curl -X POST http://localhost:8000/api/v1/chains/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "chain_name": "orchestrator",
    "input": {
      "message": "Descarga 2 archivos .7z de https://archive.org/download/sonyplaystationasiantscj20151103"
    }
  }'
```

### Verificación de Descargas

```bash
# Ver archivos descargados en el volumen persistente
docker exec brain-persistent-runner ls -lh /workspace/downloads/

# Ver logs de ejecución
docker exec brain-persistent-runner cat /workspace/logs/admin_script_*.log
```

## Próximos Pasos y Mejoras Futuras

### 1. Enriquecimiento del RAG
- Guardar documentación sobre sitios web comunes (archive.org, GitHub releases, etc.)
- Guardar patrones de scraping exitosos
- Próxima vez que se pida descargar de archive.org → usar conocimiento guardado

### 2. Gestión de Scripts Guardados
- Agregar herramienta para listar scripts en `/workspace/scripts/`
- Agregar herramienta para ejecutar scripts guardados
- Ejemplo: "Ejecuta el script monitor_web.py que guardamos ayer"

### 3. Notificaciones y Callbacks
- Integrar con sistema de notificaciones (email, Slack, webhooks)
- Ejemplo: "Avísame por email si detectas cambios en la web X"

### 4. Gestión de Tareas Programadas
- Interfaz para activar/desactivar cron jobs
- Visualización de tareas programadas activas
- Logs de ejecuciones programadas

### 5. Métricas y Monitoreo
- Dashboard de descargas realizadas
- Uso de espacio en volumen persistente
- Historial de ejecuciones administrativas

## Archivos Modificados/Creados

### Nuevos Archivos
- ✅ `services/api/src/engine/chains/admin_orchestrator_agent.py` (nuevo coordinador)
- ✅ `ADMIN_ORCHESTRATOR_IMPLEMENTATION.md` (esta documentación)

### Archivos Modificados
- ✅ `services/api/src/engine/chains/persistent_admin_agent.py` (prompt simplificado + ejemplos)
- ✅ `services/api/src/engine/chains/orchestrator_agent.py` (reconoce admin_orchestrator)
- ✅ `services/api/src/engine/chains/__init__.py` (registra nuevo agente)

## Conclusión

La implementación del **Admin Orchestrator Agent** establece una **capa de coordinación especializada** para tareas administrativas, separando las responsabilidades de decisión y ejecución. Esto mejora la calidad del código generado, facilita el mantenimiento y permite una mejor reutilización del conocimiento.

La arquitectura es **extensible** y **escalable**, permitiendo agregar nuevas estrategias y patrones sin afectar a los agentes existentes.
