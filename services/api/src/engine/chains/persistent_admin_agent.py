"""
Persistent Admin Execution Agent - Agente para ejecución administrativa persistente

Este agente es similar al Code Execution Agent pero con diferencias clave:
- Ejecuta código en contenedor PERMANENTE con volumen
- Red habilitada (puede descargar archivos)
- Scripts se guardan por defecto
- Timeouts más largos (5 min vs 30s)
- Ideal para: cron jobs, descargas programadas, monitoreo

Casos de uso:
1. Programar ejecuciones periódicas de cadenas
2. Descargar archivos de páginas web automáticamente
3. Monitorear cambios y notificar
4. Tareas administrativas que requieren estado
"""

import json
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    StreamEvent
)
from ..registry import chain_registry
from .llm_utils import call_llm
from ...code_executor.persistent_executor import get_persistent_executor
from ...code_executor.models import ExecutionStatus, Language
from .agent_helpers import (
    extract_json,
    clean_code_block,
    build_llm_messages
)

import structlog

logger = structlog.get_logger()


# ============================================
# Funciones específicas del Persistent Admin
# ============================================

def process_execution_output(stdout: str) -> tuple[str, list[str]]:
    """
    Procesa el stdout para extraer información especial.
    
    Returns:
        (texto_limpio, lista_de_imagenes_base64)
    """
    images = []
    text_lines = []
    
    for line in stdout.split('\n'):
        if line.startswith('IMAGE_BASE64:'):
            base64_data = line.replace('IMAGE_BASE64:', '').strip()
            if base64_data:
                images.append(base64_data)
        else:
            text_lines.append(line)
    
    clean_text = '\n'.join(text_lines).strip()
    return clean_text, images


# ============================================
# Definición del Agente
# ============================================

PERSISTENT_ADMIN_DEFINITION = ChainDefinition(
    id="persistent_admin",
    name="Persistent Admin Execution Agent",
    description="Agente administrativo que ejecuta código Python en contenedor permanente con volumen persistente. Ideal para tareas programadas, descargas web y monitoreo.",
    type="agent",
    version="1.0.0",
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Petición Administrativa"
        ),
        NodeDefinition(
            id="planner",
            type=NodeType.LLM,
            name="Planificador Administrativo",
            system_prompt="""Eres un asistente administrativo experto que analiza peticiones para tareas de automatización y administración.

Tu trabajo es decidir si la petición requiere escribir y ejecutar código administrativo.

CONTEXTO ESPECIAL - CONTENEDOR PERSISTENTE:
- El código se ejecutará en un contenedor PERMANENTE
- Tiene acceso a red (puede descargar archivos)
- Tiene volumen persistente en /workspace con:
  - /workspace/scripts (scripts guardados)
  - /workspace/downloads (descargas)
  - /workspace/data (datos)
  - /workspace/logs (logs)
- Puede acceder a PostgreSQL y Redis del sistema
- El script se GUARDA por defecto para futuras ejecuciones

CASOS DE USO TÍPICOS:
1. **Cron/Schedule**: Programar tareas periódicas
2. **Web Scraping**: Descargar archivos de webs automáticamente
3. **Monitoreo**: Detectar cambios y notificar
4. **Backup/Export**: Exportar datos periódicamente
5. **Integración**: Conectar con APIs externas

ANÁLISIS:
1. ¿Necesita escribir código? (sí/no)
2. ¿Es una tarea administrativa/programada? (sí/no)
3. ¿Qué debe hacer el código?
4. ¿Necesita persistencia/acceso a archivos?
5. ¿Necesita acceso a red/descargas?

BIBLIOTECAS DISPONIBLES:
- Web: requests, beautifulsoup4, lxml, httpx, aiohttp
- Scheduling: schedule, apscheduler
- Database: psycopg2, redis
- Files: openpyxl, python-docx, PyPDF2
- Utils: python-dotenv, pyyaml
- Data: numpy, pandas, matplotlib

RESPONDE EN JSON:
{
  "needs_code": true/false,
  "is_admin_task": true/false,
  "task_type": "cron|download|monitor|backup|integration|other",
  "task_description": "descripción clara",
  "libraries_needed": ["lib1", "lib2"],
  "needs_persistence": true/false,
  "needs_network": true/false,
  "estimated_runtime": "rápido|medio|largo",
  "script_name": "nombre_descriptivo.py"
}

Si no necesita código:
{
  "needs_code": false,
  "direct_response": "tu respuesta directa"
}""",
            prompt_template="Petición del usuario: {{user_query}}",
            temperature=0.2
        ),
        NodeDefinition(
            id="code_generator",
            type=NodeType.LLM,
            name="Generador de Código Administrativo",
            system_prompt="""Eres un programador experto en Python para automatización y administración de sistemas.

IMPORTANTE: Recibirás instrucciones específicas sobre QUÉ hacer. Tu trabajo es generar el código Python para hacerlo.
NO decidas estrategias ni analices peticiones, solo implementa lo que se te pide.

TAREA: {{task_description}}
TIPO: {{task_type}}
BIBLIOTECAS: {{libraries}}

CONTEXTO DEL ENTORNO:
- Contenedor: brain-persistent-runner (permanente)
- Workspace: /workspace
- Directorios disponibles:
  - /workspace/scripts (scripts guardados)
  - /workspace/downloads (para descargar archivos)
  - /workspace/data (datos persistentes)
  - /workspace/logs (logs)
- Red: HABILITADA (puedes usar requests, wget, etc.)
- Database: PostgreSQL disponible via DATABASE_URL env var
- Redis: Disponible via REDIS_URL env var

REGLAS IMPORTANTES:
1. Escribe código ROBUSTO con manejo de errores completo
2. USA logging para trazabilidad (print con timestamps)
3. GUARDA archivos en /workspace/downloads si descargas algo
4. GUARDA logs en /workspace/logs con fechas
5. Para tareas periódicas, usa schedule o cron-like logic
6. El script se guardará automáticamente para reuso
7. NO uses input() ni interacciones síncronas
8. Timeouts largos están permitidos (hasta 5 minutos)

ESTRUCTURA RECOMENDADA PARA SCRIPTS ADMINISTRATIVOS:
```python
#!/usr/bin/env python3
\"\"\"
Script: {{script_name}}
Descripción: {{task_description}}
Fecha: {datetime.now().isoformat()}
\"\"\"

import os
import sys
from datetime import datetime
from pathlib import Path

# Configuración
WORKSPACE = Path("/workspace")
DOWNLOADS_DIR = WORKSPACE / "downloads"
LOGS_DIR = WORKSPACE / "logs"
DATA_DIR = WORKSPACE / "data"

# Crear directorios si no existen
for dir in [DOWNLOADS_DIR, LOGS_DIR, DATA_DIR]:
    dir.mkdir(exist_ok=True)

def log(message):
    \"\"\"Helper de logging\"\"\"
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {message}")

def main():
    log("Iniciando ejecución...")
    try:
        # TU CÓDIGO AQUÍ
        
        log("Ejecución completada con éxito")
        return 0
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

EJEMPLOS POR TIPO DE TAREA:

**DOWNLOAD SIMPLE (un archivo directo)**:
```python
import requests
from pathlib import Path
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

url = "https://example.com/file.zip"
filename = Path("/workspace/downloads") / "file.zip"

log(f"Descargando: {url}")
response = requests.get(url, timeout=120, stream=True)
response.raise_for_status()

with open(filename, 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

log(f"Descargado: {filename} ({filename.stat().st_size} bytes)")
```

**ARCHIVE.ORG DOWNLOAD (usando Metadata API - RECOMENDADO)**:
```python
import requests
from pathlib import Path
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

# URL de la colección de archive.org
collection_url = "https://archive.org/download/example_collection"
collection_id = collection_url.rstrip('/').split('/')[-1]

downloads_dir = Path("/workspace/downloads")
downloads_dir.mkdir(exist_ok=True)

log(f"Obteniendo metadata de colección: {collection_id}")

# 1. Usar la API de metadata (más confiable que HTML scraping)
metadata_url = f"https://archive.org/metadata/{collection_id}"
response = requests.get(metadata_url, timeout=60)
response.raise_for_status()
metadata = response.json()

# 2. Obtener archivos del tipo deseado
all_files = metadata['files']
target_files = [f for f in all_files if f.get('name', '').endswith('.7z')]

log(f"Encontrados {len(target_files)} archivos .7z")

if not target_files:
    log("⚠️  No se encontraron archivos del tipo especificado")
    exit(0)

# 3. Descargar archivos (limitar cantidad para pruebas)
max_downloads = 2
downloaded = 0
failed = 0

for i, file_info in enumerate(target_files[:max_downloads], 1):
    filename = file_info['name']
    file_size = int(file_info.get('size', 0))
    
    # Construir URL de descarga
    download_url = f"https://archive.org/download/{collection_id}/{filename}"
    local_path = downloads_dir / filename
    
    log(f"[{i}/{max_downloads}] Descargando: {filename} ({file_size / (1024*1024):.2f} MB)")
    
    try:
        # Intentar descarga con redirects habilitados
        file_response = requests.get(download_url, timeout=300, stream=True, allow_redirects=True)
        
        # Manejar errores de acceso
        if file_response.status_code == 403:
            log(f"❌ Error 403 Forbidden: El archivo no es accesible públicamente")
            log(f"   Posibles causas:")
            log(f"   - La colección requiere autenticación")
            log(f"   - El contenido tiene restricciones de copyright")
            log(f"   - Acceso geográfico bloqueado")
            failed += 1
            continue
        elif file_response.status_code == 401:
            log(f"❌ Error 401 Unauthorized: Se requiere autenticación")
            failed += 1
            continue
        
        file_response.raise_for_status()
        
        # Descargar archivo
        with open(local_path, 'wb') as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        size_mb = local_path.stat().st_size / (1024 * 1024)
        log(f"✅ Descargado: {filename} ({size_mb:.2f} MB)")
        downloaded += 1
        
    except requests.exceptions.HTTPError as e:
        log(f"❌ Error HTTP descargando {filename}: {e}")
        failed += 1
    except Exception as e:
        log(f"❌ Error descargando {filename}: {e}")
        failed += 1

log(f"\nResumen: {downloaded} exitosos, {failed} fallidos")
log(f"Archivos en: {downloads_dir}")

# Si todos fallaron con 403/401, informar claramente
if downloaded == 0 and failed > 0:
    log("\n⚠️  NOTA IMPORTANTE:")
    log("   No se pudo descargar ningún archivo debido a restricciones de acceso.")
    log("   Esta colección puede requerir:")
    log("   - Cuenta de archive.org con sesión iniciada")
    log("   - Credenciales de API (logged-in-user y logged-in-sig cookies)")
    log("   - El contenido puede no estar disponible públicamente")
```

**WEB SCRAPING GENÉRICO + DOWNLOAD (otros sitios web)**:
```python
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

# URL base del directorio
base_url = "https://example.com/files/"
downloads_dir = Path("/workspace/downloads")
downloads_dir.mkdir(exist_ok=True)

log(f"Obteniendo listado de: {base_url}")

# 1. Obtener la página HTML
response = requests.get(base_url, timeout=60)
response.raise_for_status()
html = response.text

# 2. Parsear HTML con BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')

# 3. Buscar enlaces a archivos (ajustar extensión según necesidad)
links = soup.find_all('a', href=True)
target_files = [link['href'] for link in links if link['href'].endswith('.zip')]

log(f"Encontrados {len(target_files)} archivos")

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

**CRON/SCHEDULE (Tarea periódica)**:
```python
import schedule
import time
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

def tarea():
    log("Ejecutando tarea programada")
    # Tu lógica aquí (ej: check API, download file, etc.)

# Programar cada hora
schedule.every().hour.do(tarea)

log("Scheduler iniciado (ejecutando 3 ciclos de prueba)")

# Loop (para testing, ejecuta solo 3 veces)
for i in range(3):
    schedule.run_pending()
    time.sleep(2)  # Esperar 2 segundos entre ciclos

log("Test completado")
```

**MONITOR (Detectar cambios en web/API)**:
```python
import requests
import json
from pathlib import Path
from datetime import datetime

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

state_file = Path("/workspace/data/monitor_state.json")
url = "https://api.example.com/data"

log(f"Monitoreando: {url}")

# Cargar estado anterior
if state_file.exists():
    old_data = json.loads(state_file.read_text())
    log("Estado anterior cargado")
else:
    old_data = {}
    log("Primera ejecución, sin estado anterior")

# Obtener datos actuales
response = requests.get(url, timeout=60)
response.raise_for_status()
new_data = response.json()

# Detectar cambios
if new_data != old_data:
    log(f"⚠️ CAMBIO DETECTADO")
    log(f"Diferencias: {set(new_data.keys()) - set(old_data.keys())}")
    
    # Guardar nuevo estado
    state_file.write_text(json.dumps(new_data, indent=2))
    log("Nuevo estado guardado")
else:
    log("✅ Sin cambios detectados")
```

**API INTEGRATION (Llamada a API externa)**:
```python
import requests
from datetime import datetime
from pathlib import Path

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")

api_url = "https://api.example.com/endpoint"
headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}

log(f"Llamando a API: {api_url}")

try:
    response = requests.post(
        api_url,
        json={"param": "value"},
        headers=headers,
        timeout=60
    )
    response.raise_for_status()
    
    data = response.json()
    log(f"✅ Respuesta recibida: {data}")
    
    # Guardar resultado
    output_file = Path("/workspace/data/api_result.json")
    output_file.write_text(json.dumps(data, indent=2))
    log(f"Resultado guardado en: {output_file}")
    
except requests.exceptions.RequestException as e:
    log(f"❌ Error en API: {e}")
```

FORMATO DE RESPUESTA:
Genera SOLO el código Python, sin markdown, sin explicaciones extras.
El código debe ser completo y listo para ejecutar.

CÓDIGO:""",
            prompt_template="Genera el código administrativo ahora.",
            temperature=0.3
        ),
        NodeDefinition(
            id="executor",
            type=NodeType.TOOL,
            name="Ejecutor Persistente"
        ),
        NodeDefinition(
            id="error_handler",
            type=NodeType.LLM,
            name="Corrector de Errores",
            system_prompt="""El script administrativo falló. Analiza y corrige el error.

SCRIPT ORIGINAL:
```python
{{original_code}}
```

ERROR:
```
{{error_message}}
```

STDOUT:
```
{{stdout}}
```

STDERR:
```
{{stderr}}
```

CONTEXTO:
- Entorno: Contenedor persistente con red habilitada
- Workspace: /workspace
- Timeout: 300 segundos

CORRECCIONES COMUNES:
1. Red: Asegurar timeouts en requests
2. Archivos: Verificar que directorios existan
3. Permisos: Usar rutas en /workspace
4. Timeouts: Operaciones largas pueden necesitar más tiempo
5. Dependencies: Verificar imports disponibles

Genera el código CORREGIDO (solo código, sin explicaciones).

CÓDIGO CORREGIDO:""",
            prompt_template="Corrige el código.",
            temperature=0.3
        ),
        NodeDefinition(
            id="synthesizer",
            type=NodeType.LLM,
            name="Sintetizador",
            system_prompt="""Presenta los resultados de la ejecución administrativa al usuario.

PETICIÓN: {{user_query}}
TIPO DE TAREA: {{task_type}}
SCRIPT: {{script_name}}
INTENTOS: {{attempts}}
GUARDADO EN: /workspace/scripts/{{script_name}}

RESULTADO:
{{execution_result}}

Tu trabajo:
1. Explicar qué hizo el script
2. Presentar resultados claramente
3. Si descargó archivos, indicar ubicación
4. Si es una tarea programada, explicar cómo ejecutarla nuevamente
5. Sugerir mejoras o próximos pasos

NOTAS IMPORTANTES:
- El script está GUARDADO y puede reutilizarse
- Para ejecutarlo nuevamente: "Ejecuta el script {{script_name}}"
- Para ver scripts guardados: "Lista mis scripts"
- Archivos descargados están en /workspace/downloads

Genera una respuesta útil y accionable.""",
            prompt_template="Presenta los resultados.",
            temperature=0.7
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Respuesta"
        )
    ],
    config=ChainConfig(
        temperature=0.5,
        use_memory=True,
        max_memory_messages=10
    )
)


# ============================================
# Builder Function
# ============================================

async def build_persistent_admin_agent(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder del agente administrativo persistente.
    
    FASES:
    1. Planning: Analizar tarea administrativa
    2. Code Generation: Generar código robusto
    3. Persistent Execution: Ejecutar en contenedor permanente
    4. Error Handling: Corregir errores si falla
    5. Synthesis: Presentar resultados y próximos pasos
    
    NODOS:
    - input: Petición administrativa
    - planner: Analiza y clasifica tarea
    - code_generator: Genera código Python
    - executor: Ejecuta en contenedor persistente
    - error_handler: Corrige errores
    - synthesizer: Presenta resultados
    - output: Respuesta final
    
    MEMORY: Yes (últimos 10 mensajes)
    EXECUTION: Contenedor persistente con volumen
    TIMEOUT: 300 segundos (5 minutos)
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    max_retries = input_data.get("max_retries", 2)  # Menos reintentos que el normal
    save_script = input_data.get("save_script", True)  # Por defecto guardar
    script_name = input_data.get("script_name", None)
    
    # Obtener nodos
    planner_node = PERSISTENT_ADMIN_DEFINITION.get_node("planner")
    code_gen_node = PERSISTENT_ADMIN_DEFINITION.get_node("code_generator")
    error_handler_node = PERSISTENT_ADMIN_DEFINITION.get_node("error_handler")
    synth_node = PERSISTENT_ADMIN_DEFINITION.get_node("synthesizer")
    
    if not all([planner_node, code_gen_node, error_handler_node, synth_node]):
        raise ValueError("Nodos del Persistent Admin Agent no encontrados")
    
    # ========== FASE 1: PLANIFICACIÓN ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="📋 Analizando tarea administrativa",
        data={"query": query}
    )
    
    planner_messages = build_llm_messages(
        system_prompt=planner_node.system_prompt,
        template=planner_node.prompt_template,
        variables={"user_query": query},
        memory=None
    )
    
    plan_response = await call_llm(
        llm_url, model, planner_messages,
        temperature=planner_node.temperature,
        provider_type=provider_type,
        api_key=api_key
    )
    
    plan_data = extract_json(plan_response)
    
    if not plan_data:
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            node_id="planner",
            content="No pude analizar la petición"
        )
        return
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="planner",
        node_name="📋 Análisis completado",
        data=plan_data
    )
    
    # Si no necesita código, responder directamente
    if not plan_data.get("needs_code", False):
        direct_response = plan_data.get("direct_response", "No necesitas código para esto.")
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="direct_response",
            content=direct_response
        )
        return
    
    # ========== FASE 2: GENERACIÓN DE CÓDIGO ==========
    task_type = plan_data.get("task_type", "other")
    task = plan_data.get("task_description", query)
    libraries = plan_data.get("libraries_needed", [])
    libs_str = ", ".join(libraries) if libraries else "ninguna específica"
    
    # Usar script_name del plan o del input
    if not script_name:
        script_name = plan_data.get("script_name", f"admin_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
    
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="code_generator",
        node_name=f"💻 Generando script administrativo",
        data={"task_type": task_type, "script_name": script_name}
    )
    
    code_gen_prompt = code_gen_node.system_prompt
    code_gen_prompt = code_gen_prompt.replace("{{task_description}}", task)
    code_gen_prompt = code_gen_prompt.replace("{{task_type}}", task_type)
    code_gen_prompt = code_gen_prompt.replace("{{libraries}}", libs_str)
    code_gen_prompt = code_gen_prompt.replace("{{script_name}}", script_name)
    
    code_messages = build_llm_messages(
        system_prompt=code_gen_prompt,
        template=code_gen_node.prompt_template,
        variables={},
        memory=None
    )
    
    generated_code = await call_llm(
        llm_url, model, code_messages,
        temperature=code_gen_node.temperature,
        provider_type=provider_type,
        api_key=api_key
    )
    
    generated_code = clean_code_block(generated_code, "python")
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="code_generator",
        node_name="💻 Script generado",
        data={"code_preview": generated_code[:300] + "..."}
    )
    
    # ========== FASE 3: EJECUCIÓN PERSISTENTE ==========
    attempt = 0
    execution_result = None
    current_code = generated_code
    
    while attempt < max_retries:
        attempt += 1
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"executor_{attempt}",
            node_name=f"🚀 Ejecutando en contenedor persistente (intento {attempt}/{max_retries})",
            data={"attempt": attempt, "script": script_name}
        )
        
        try:
            executor = get_persistent_executor()
            
            execution_result = await executor.execute_python(
                code=current_code,
                script_name=script_name,
                timeout=300,  # 5 minutos
                save_script=save_script
            )
            
        except Exception as e:
            logger.error(f"Error ejecutando código persistente: {e}")
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id="executor",
                content=f"Error del sistema: {str(e)}"
            )
            return
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"executor_{attempt}",
            node_name=f"🚀 Ejecución completada",
            data={
                "success": execution_result.success,
                "status": execution_result.status.value,
                "saved": save_script,
                "script_path": f"/workspace/scripts/{script_name}"
            }
        )
        
        if execution_result.success:
            break
        
        # ========== FASE 4: ERROR HANDLING ==========
        if attempt < max_retries:
            yield StreamEvent(
                event_type="node_start",
                execution_id=execution_id,
                node_id=f"error_handler_{attempt}",
                node_name="🔧 Corrigiendo script",
                data={"error": execution_result.error_message}
            )
            
            error_prompt = error_handler_node.system_prompt
            error_prompt = error_prompt.replace("{{original_code}}", current_code)
            error_prompt = error_prompt.replace("{{error_message}}", execution_result.error_message or "Error desconocido")
            error_prompt = error_prompt.replace("{{stdout}}", execution_result.stdout)
            error_prompt = error_prompt.replace("{{stderr}}", execution_result.stderr)
            
            error_messages = build_llm_messages(
                system_prompt=error_prompt,
                template=error_handler_node.prompt_template,
                variables={},
                memory=None
            )
            
            corrected_code = await call_llm(
                llm_url, model, error_messages,
                temperature=error_handler_node.temperature,
                provider_type=provider_type,
                api_key=api_key
            )
            
            current_code = clean_code_block(corrected_code, "python")
            
            yield StreamEvent(
                event_type="node_end",
                execution_id=execution_id,
                node_id=f"error_handler_{attempt}",
                node_name="🔧 Script corregido"
            )
    
    # ========== FASE 5: SÍNTESIS ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="📊 Presentando resultados"
    )
    
    clean_text, images = process_execution_output(execution_result.stdout if execution_result else "")
    
    result_dict = execution_result.to_dict() if execution_result else {}
    if clean_text != execution_result.stdout:
        result_dict["stdout"] = clean_text
    
    synth_prompt = synth_node.system_prompt
    synth_prompt = synth_prompt.replace("{{user_query}}", query)
    synth_prompt = synth_prompt.replace("{{task_type}}", task_type)
    synth_prompt = synth_prompt.replace("{{script_name}}", script_name)
    synth_prompt = synth_prompt.replace("{{attempts}}", str(attempt))
    synth_prompt = synth_prompt.replace("{{execution_result}}", json.dumps(result_dict, indent=2, ensure_ascii=False))
    
    synthesis_messages = build_llm_messages(
        system_prompt=synth_prompt,
        template=synth_node.prompt_template,
        variables={},
        memory=None
    )
    
    final_response = await call_llm(
        llm_url, model, synthesis_messages,
        temperature=synth_node.temperature,
        provider_type=provider_type,
        api_key=api_key
    )
    
    if images:
        final_response += "\n\n## 🖼️ Imágenes Generadas\n\n"
        for i, img_base64 in enumerate(images, 1):
            final_response += f"![Imagen {i}](data:image/png;base64,{img_base64})\n\n"
    
    yield StreamEvent(
        event_type="token",
        execution_id=execution_id,
        node_id="synthesizer",
        content=final_response
    )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="📊 Resultados presentados",
        data={
            "success": execution_result.success if execution_result else False,
            "attempts": attempt,
            "script_saved": save_script,
            "script_path": f"/workspace/scripts/{script_name}"
        }
    )
    
    # ========== EVENTO FINAL: OUTPUT ==========
    yield StreamEvent(
        event_type="output",
        execution_id=execution_id,
        node_id="output",
        node_name="✅ Ejecución completada",
        data={
            "response": final_response,
            "success": execution_result.success if execution_result else False,
            "execution_log": execution_result.stdout if execution_result else "",
            "script_path": f"/workspace/scripts/{script_name}" if save_script else None,
            "images": images
        }
    )
    
    # ========== RESULTADO PARA MODO NO-STREAMING ==========
    if not stream:
        yield {"_result": {
            "response": final_response,
            "success": execution_result.success if execution_result else False,
            "execution_log": clean_text,
            "script_path": f"/workspace/scripts/{script_name}" if save_script else None,
            "images": images
        }}


# ============================================
# Registro del Agente
# ============================================

def register_persistent_admin_agent():
    """Registrar el agente administrativo persistente"""
    
    chain_registry.register(
        chain_id="persistent_admin",
        definition=PERSISTENT_ADMIN_DEFINITION,
        builder=build_persistent_admin_agent
    )
    
    logger.info("Persistent Admin Execution Agent registrado (v1.0.0)")
