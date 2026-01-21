"""
Code Execution Agent - Agente que genera y ejecuta código

Este agente puede:
1. Analizar peticiones del usuario
2. Generar código Python o JavaScript
3. Ejecutarlo en contenedores Docker aislados
4. Corregir errores y reintentar (máx 3 intentos)
5. Presentar resultados al usuario
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
from ...code_executor import get_code_executor, Language, ExecutionStatus

import structlog

logger = structlog.get_logger()


# ===========================================
# System Prompts
# ===========================================

PLANNER_PROMPT = """Eres un asistente de programación experto que analiza peticiones de usuarios.

Tu trabajo es decidir si la petición requiere escribir y ejecutar código.

ANÁLISIS:
1. ¿Necesita escribir código? (sí/no)
2. Si sí, ¿qué lenguaje usar? (python o javascript)
3. ¿Qué debe hacer el código?
4. ¿Qué bibliotecas/funciones necesita?

BIBLIOTECAS DISPONIBLES:
Python: numpy, pandas, matplotlib, requests
JavaScript/Node.js: axios, lodash, moment

RESPONDE EN JSON:
{{
  "needs_code": true/false,
  "language": "python" o "javascript",
  "task_description": "descripción clara de la tarea",
  "libraries_needed": ["lib1", "lib2"],
  "complexity": "simple|medium|complex"
}}

Si no necesita código, responde:
{{
  "needs_code": false,
  "direct_response": "tu respuesta directa al usuario"
}}
"""


def get_code_generator_prompt(language: str, task: str, libraries: list) -> str:
    """Genera el prompt para el generador de código"""
    libs_str = ", ".join(libraries) if libraries else "ninguna específica"
    
    return f"""Eres un programador experto en {language}.

TAREA: {task}

BIBLIOTECAS DISPONIBLES: {libs_str}

REGLAS IMPORTANTES:
1. Escribe código limpio, bien comentado y eficiente
2. Incluye manejo de errores apropiado
3. El código debe producir output visible (usar print() o console.log())
4. NO uses input() ni interacciones con el usuario
5. NO uses loops infinitos
6. Si necesitas datos de ejemplo, genera datos sintéticos
7. El código debe ser autocontenido y ejecutable

IMPORTANTE PARA IMÁGENES Y GRÁFICAS:
Si la tarea requiere generar una imagen, gráfica o visualización:
- USA matplotlib con backend 'Agg' (sin display)
- GUARDA la imagen en un BytesIO buffer
- CONVIERTE a base64 y imprímela con un marcador especial
- Formato: print("IMAGE_BASE64:{{data_base64}}")

Ejemplo para Python con matplotlib:
```
import matplotlib
matplotlib.use('Agg')  # Backend sin display
import matplotlib.pyplot as plt
import io
import base64

# ... generar gráfica ...
plt.figure()
# ... tu código de plotting ...

# Guardar a base64
buffer = io.BytesIO()
plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
buffer.seek(0)
image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
plt.close()

print(f"IMAGE_BASE64:{{image_base64}}")
```

FORMATO DE RESPUESTA:
Genera SOLO el código, sin markdown, sin explicaciones antes o después.
El código debe empezar directamente (no uses ```python o ```javascript).

CÓDIGO:"""


ERROR_HANDLER_PROMPT = """El código que generaste falló con el siguiente error:

CÓDIGO ORIGINAL:
```
{code}
```

ERROR:
```
{error}
```

STDOUT:
```
{stdout}
```

STDERR:
```
{stderr}
```

Por favor, analiza el error y genera una VERSIÓN CORREGIDA del código.

REGLAS:
1. Corrige el error identificado
2. Mantén la funcionalidad original
3. Asegúrate de que el nuevo código es sintácticamente correcto
4. Si el error es de lógica, ajusta la lógica

Genera SOLO el código corregido, sin explicaciones.

CÓDIGO CORREGIDO:"""


SYNTHESIZER_PROMPT = """Eres un asistente que presenta resultados de ejecución de código al usuario.

PETICIÓN ORIGINAL: {query}
LENGUAJE USADO: {language}
INTENTOS: {attempts}

RESULTADO DE LA EJECUCIÓN:
{execution_result}

Tu trabajo es:
1. Explicar qué hizo el código
2. Presentar los resultados de forma clara
3. Si hubo errores, explicarlos de forma amigable
4. Sugerir mejoras si es relevante

IMPORTANTE - DETECCIÓN DE IMÁGENES:
Si el stdout contiene "IMAGE_BASE64:", significa que el código generó una imagen.
- Extrae el código base64 después del marcador
- Muestra la imagen usando markdown: ![Resultado](data:image/png;base64,{{base64_data}})
- Explica qué representa la imagen

Genera una respuesta clara y útil para el usuario."""


# ===========================================
# Helper Functions
# ===========================================

def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extrae JSON de una respuesta del LLM"""
    try:
        # Buscar bloques JSON en el texto
        start = text.find('{')
        if start == -1:
            return None
        
        # Encontrar el cierre correspondiente
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    json_str = text[start:i+1]
                    return json.loads(json_str)
        
        return None
    except Exception as e:
        logger.error(f"Error extrayendo JSON: {e}")
        return None


def clean_code(code: str) -> str:
    """Limpia el código eliminando markdown y espacios extra"""
    # Eliminar bloques de markdown
    code = code.strip()
    
    # Si empieza con ```python o ```javascript, eliminar
    if code.startswith('```'):
        lines = code.split('\n')
        if len(lines) > 1:
            # Eliminar primera línea (```python)
            lines = lines[1:]
            # Eliminar última línea si es ```
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            code = '\n'.join(lines)
    
    return code.strip()


def process_execution_output(stdout: str) -> tuple[str, list[str]]:
    """
    Procesa el stdout para extraer imágenes en base64.
    
    Returns:
        (texto_limpio, lista_de_imagenes_base64)
    """
    images = []
    text_lines = []
    
    for line in stdout.split('\n'):
        if line.startswith('IMAGE_BASE64:'):
            # Extraer base64
            base64_data = line.replace('IMAGE_BASE64:', '').strip()
            if base64_data:
                images.append(base64_data)
        else:
            text_lines.append(line)
    
    clean_text = '\n'.join(text_lines).strip()
    return clean_text, images


# ===========================================
# Agent Builder
# ===========================================

async def build_code_execution_agent(
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
    Builder del agente de ejecución de código.
    
    Flujo:
    1. Planificación: ¿Necesita código? ¿Qué lenguaje?
    2. Generación: LLM genera el código
    3. Ejecución: Ejecutar en contenedor Docker
    4. Retry: Si falla, intentar corregir (máx 3 veces)
    5. Síntesis: Presentar resultados
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    max_retries = input_data.get("max_retries", 3)
    
    # ========== FASE 1: PLANIFICACIÓN ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="📋 Analizando petición",
        data={"query": query}
    )
    
    planner_messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": f"Petición del usuario: {query}"}
    ]
    
    plan_response = await call_llm(
        llm_url, model, planner_messages,
        temperature=0.2,
        provider_type=provider_type,
        api_key=api_key
    )
    
    plan_data = extract_json(plan_response)
    
    if not plan_data:
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            node_id="planner",
            content="No pude entender la petición"
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
    language = plan_data.get("language", "python")
    task = plan_data.get("task_description", query)
    libraries = plan_data.get("libraries_needed", [])
    
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="code_generator",
        node_name=f"💻 Generando código {language}",
        data={"language": language, "task": task}
    )
    
    code_prompt = get_code_generator_prompt(language, task, libraries)
    code_messages = [
        {"role": "system", "content": code_prompt},
        {"role": "user", "content": "Genera el código ahora."}
    ]
    
    generated_code = await call_llm(
        llm_url, model, code_messages,
        temperature=0.3,
        provider_type=provider_type,
        api_key=api_key
    )
    
    generated_code = clean_code(generated_code)
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="code_generator",
        node_name="💻 Código generado",
        data={"code": generated_code[:500] + "..." if len(generated_code) > 500 else generated_code}
    )
    
    # ========== FASE 3: EJECUCIÓN CON RETRY ==========
    attempt = 0
    execution_result = None
    current_code = generated_code
    
    while attempt < max_retries:
        attempt += 1
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"executor_{attempt}",
            node_name=f"🚀 Ejecutando código (intento {attempt}/{max_retries})",
            data={"attempt": attempt}
        )
        
        # Ejecutar el código
        try:
            code_exec = get_code_executor()
            
            if language == "python":
                execution_result = await code_exec.execute_python(current_code)
            elif language in ["javascript", "node"]:
                execution_result = await code_exec.execute_javascript(current_code)
            else:
                yield StreamEvent(
                    event_type="error",
                    execution_id=execution_id,
                    node_id="executor",
                    content=f"Lenguaje no soportado: {language}"
                )
                return
        except Exception as e:
            logger.error(f"Error ejecutando código: {e}")
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id="executor",
                content=f"Error del sistema: {str(e)}"
            )
            return
        
        # Enviar resultado de ejecución
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"executor_{attempt}",
            node_name=f"🚀 Ejecución completada (intento {attempt})",
            data={
                "success": execution_result.success,
                "status": execution_result.status.value,
                "stdout": execution_result.stdout[:200] if execution_result.stdout else "",
                "execution_time": execution_result.execution_time
            }
        )
        
        # Si tuvo éxito, salir del loop
        if execution_result.success:
            break
        
        # Si falló y quedan intentos, intentar corregir
        if attempt < max_retries:
            yield StreamEvent(
                event_type="node_start",
                execution_id=execution_id,
                node_id=f"error_handler_{attempt}",
                node_name="🔧 Corrigiendo error",
                data={"error": execution_result.error_message}
            )
            
            error_prompt = ERROR_HANDLER_PROMPT.format(
                code=current_code,
                error=execution_result.error_message or "Error desconocido",
                stdout=execution_result.stdout,
                stderr=execution_result.stderr
            )
            
            error_messages = [
                {"role": "system", "content": error_prompt},
                {"role": "user", "content": "Genera el código corregido."}
            ]
            
            corrected_code = await call_llm(
                llm_url, model, error_messages,
                temperature=0.3,
                provider_type=provider_type,
                api_key=api_key
            )
            
            current_code = clean_code(corrected_code)
            
            yield StreamEvent(
                event_type="node_end",
                execution_id=execution_id,
                node_id=f"error_handler_{attempt}",
                node_name="🔧 Código corregido",
                data={"corrected": True}
            )
    
    # ========== FASE 4: SÍNTESIS ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="📊 Presentando resultados"
    )
    
    # Procesar stdout para extraer imágenes
    clean_text, images = process_execution_output(execution_result.stdout if execution_result else "")
    
    # Actualizar execution_result con texto limpio
    result_dict = execution_result.to_dict() if execution_result else {}
    if clean_text != execution_result.stdout:
        result_dict["stdout"] = clean_text
        result_dict["images_count"] = len(images)
    
    synthesis_prompt = SYNTHESIZER_PROMPT.format(
        query=query,
        language=language,
        attempts=attempt,
        execution_result=json.dumps(result_dict, indent=2, ensure_ascii=False)
    )
    
    synthesis_messages = [
        {"role": "system", "content": synthesis_prompt},
        {"role": "user", "content": "Presenta los resultados al usuario."}
    ]
    
    final_response = await call_llm(
        llm_url, model, synthesis_messages,
        temperature=0.7,
        provider_type=provider_type,
        api_key=api_key
    )
    
    # Si hay imágenes, agregarlas al final de la respuesta
    if images:
        final_response += "\n\n## 🖼️ Imagen Generada\n\n"
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
            "execution_time": execution_result.execution_time if execution_result else 0,
            "images_generated": len(images)
        }
    )


# ===========================================
# Registro del Agente
# ===========================================

def register_code_execution_agent():
    """Registrar el agente de ejecución de código"""
    
    definition = ChainDefinition(
        id="code_execution",
        name="Code Execution Agent",
        description="Agente que genera código Python o JavaScript y lo ejecuta en contenedores Docker aislados. Puede corregir errores automáticamente.",
        type="agent",
        version="1.0.0",
        nodes=[
            NodeDefinition(id="input", type=NodeType.INPUT, name="Petición"),
            NodeDefinition(id="planner", type=NodeType.LLM, name="Planificador"),
            NodeDefinition(id="code_generator", type=NodeType.LLM, name="Generador de Código"),
            NodeDefinition(id="executor", type=NodeType.TOOL, name="Ejecutor"),
            NodeDefinition(id="error_handler", type=NodeType.LLM, name="Corrector de Errores"),
            NodeDefinition(id="synthesizer", type=NodeType.LLM, name="Sintetizador"),
            NodeDefinition(id="output", type=NodeType.OUTPUT, name="Respuesta")
        ],
        config=ChainConfig(
            temperature=0.5,
            use_memory=True,
            max_memory_messages=10
        )
    )
    
    chain_registry.register(
        chain_id="code_execution",
        definition=definition,
        builder=build_code_execution_agent
    )
    
    logger.info("Code Execution Agent registrado")
