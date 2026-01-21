"""
Code Execution Agent - REFACTORIZADO con estándar
Agente que genera y ejecuta código Python o JavaScript en contenedores Docker aislados.

Capacidades:
1. Analizar peticiones del usuario
2. Generar código Python o JavaScript
3. Ejecutarlo en contenedores Docker
4. Corregir errores y reintentar (máx 3 intentos)
5. Presentar resultados con imágenes base64
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
from .agent_helpers import (  # ✅ Usar helpers compartidos
    extract_json,
    clean_code_block,
    build_llm_messages
)

import structlog

logger = structlog.get_logger()


# ============================================
# Funciones específicas del Code Executor
# ============================================

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
            base64_data = line.replace('IMAGE_BASE64:', '').strip()
            if base64_data:
                images.append(base64_data)
        else:
            text_lines.append(line)
    
    clean_text = '\n'.join(text_lines).strip()
    return clean_text, images


# ============================================
# Definición del Agente (con prompts editables)
# ============================================

CODE_EXECUTION_DEFINITION = ChainDefinition(
    id="code_execution",
    name="Code Execution Agent",
    description="Agente que genera código Python o JavaScript y lo ejecuta en contenedores Docker aislados. Puede corregir errores automáticamente.",
    type="agent",
    version="2.0.0",  # ✅ Versión actualizada
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Petición"
        ),
        NodeDefinition(
            id="planner",
            type=NodeType.LLM,
            name="Planificador",
            # ✅ System prompt editable
            system_prompt="""Eres un asistente de programación experto que analiza peticiones de usuarios.

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
{
  "needs_code": true/false,
  "language": "python" o "javascript",
  "task_description": "descripción clara de la tarea",
  "libraries_needed": ["lib1", "lib2"],
  "complexity": "simple|medium|complex"
}

Si no necesita código, responde:
{
  "needs_code": false,
  "direct_response": "tu respuesta directa al usuario"
}""",
            prompt_template="Petición del usuario: {{user_query}}",
            temperature=0.2
        ),
        NodeDefinition(
            id="code_generator",
            type=NodeType.LLM,
            name="Generador de Código",
            # ✅ System prompt editable con variables
            system_prompt="""Eres un programador experto en {{language}}.

TAREA: {{task_description}}

BIBLIOTECAS DISPONIBLES: {{libraries}}

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
- Formato: print("IMAGE_BASE64:{data_base64}")

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

print(f"IMAGE_BASE64:{image_base64}")
```

FORMATO DE RESPUESTA:
Genera SOLO el código, sin markdown, sin explicaciones antes o después.
El código debe empezar directamente (no uses ```python o ```javascript).

CÓDIGO:""",
            prompt_template="Genera el código ahora.",
            temperature=0.3
        ),
        NodeDefinition(
            id="executor",
            type=NodeType.TOOL,
            name="Ejecutor Docker"
        ),
        NodeDefinition(
            id="error_handler",
            type=NodeType.LLM,
            name="Corrector de Errores",
            # ✅ System prompt editable
            system_prompt="""El código que generaste falló con el siguiente error:

CÓDIGO ORIGINAL:
```
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

Por favor, analiza el error y genera una VERSIÓN CORREGIDA del código.

REGLAS:
1. Corrige el error identificado
2. Mantén la funcionalidad original
3. Asegúrate de que el nuevo código es sintácticamente correcto
4. Si el error es de lógica, ajusta la lógica

Genera SOLO el código corregido, sin explicaciones.

CÓDIGO CORREGIDO:""",
            prompt_template="Genera el código corregido.",
            temperature=0.3
        ),
        NodeDefinition(
            id="synthesizer",
            type=NodeType.LLM,
            name="Sintetizador",
            # ✅ System prompt editable
            system_prompt="""Eres un asistente que presenta resultados de ejecución de código al usuario.

PETICIÓN ORIGINAL: {{user_query}}
LENGUAJE USADO: {{language}}
INTENTOS: {{attempts}}

RESULTADO DE LA EJECUCIÓN:
{{execution_result}}

Tu trabajo es:
1. Explicar qué hizo el código
2. Presentar los resultados de forma clara
3. Si hubo errores, explicarlos de forma amigable
4. Sugerir mejoras si es relevante

IMPORTANTE - DETECCIÓN DE IMÁGENES:
Si el stdout contiene "IMAGE_BASE64:", significa que el código generó una imagen.
- Extrae el código base64 después del marcador
- Muestra la imagen usando markdown: ![Resultado](data:image/png;base64,{base64_data})
- Explica qué representa la imagen

Genera una respuesta clara y útil para el usuario.""",
            prompt_template="Presenta los resultados al usuario.",
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
# Builder Function (Lógica del Agente)
# ============================================

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
    
    FASES:
    1. Planning: Analizar si necesita código y qué lenguaje
    2. Code Generation: Generar código con LLM
    3. Execution: Ejecutar en Docker con retry (máx 3)
    4. Error Handling: Corregir código si falla
    5. Synthesis: Presentar resultados con imágenes
    
    NODOS:
    - input (INPUT): Petición del usuario
    - planner (LLM): Decide lenguaje y task
    - code_generator (LLM): Genera código
    - executor (TOOL): Ejecuta en Docker
    - error_handler (LLM): Corrige errores
    - synthesizer (LLM): Presenta resultados
    - output (OUTPUT): Respuesta final
    
    MEMORY: Yes (últimos 10 mensajes)
    TOOLS: Docker code execution (Python/JavaScript)
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    max_retries = input_data.get("max_retries", 3)
    
    # ✅ Obtener nodos con prompts editables
    planner_node = CODE_EXECUTION_DEFINITION.get_node("planner")
    code_gen_node = CODE_EXECUTION_DEFINITION.get_node("code_generator")
    error_handler_node = CODE_EXECUTION_DEFINITION.get_node("error_handler")
    synth_node = CODE_EXECUTION_DEFINITION.get_node("synthesizer")
    
    if not all([planner_node, code_gen_node, error_handler_node, synth_node]):
        raise ValueError("Nodos del Code Execution Agent no encontrados")
    
    # ========== FASE 1: PLANIFICACIÓN ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="📋 Analizando petición",
        data={"query": query}
    )
    
    # ✅ Usar helper para construir mensajes
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
    
    plan_data = extract_json(plan_response)  # ✅ Usar helper compartido
    
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
    libs_str = ", ".join(libraries) if libraries else "ninguna específica"
    
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="code_generator",
        node_name=f"💻 Generando código {language}",
        data={"language": language, "task": task}
    )
    
    # ✅ Reemplazar variables en system prompt
    code_gen_prompt = code_gen_node.system_prompt
    code_gen_prompt = code_gen_prompt.replace("{{language}}", language)
    code_gen_prompt = code_gen_prompt.replace("{{task_description}}", task)
    code_gen_prompt = code_gen_prompt.replace("{{libraries}}", libs_str)
    
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
    
    generated_code = clean_code_block(generated_code, language)  # ✅ Usar helper
    
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
        
        # ========== FASE 4: ERROR HANDLING ==========
        if attempt < max_retries:
            yield StreamEvent(
                event_type="node_start",
                execution_id=execution_id,
                node_id=f"error_handler_{attempt}",
                node_name="🔧 Corrigiendo error",
                data={"error": execution_result.error_message}
            )
            
            # ✅ Reemplazar variables en error handler prompt
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
            
            current_code = clean_code_block(corrected_code, language)  # ✅ Usar helper
            
            yield StreamEvent(
                event_type="node_end",
                execution_id=execution_id,
                node_id=f"error_handler_{attempt}",
                node_name="🔧 Código corregido",
                data={"corrected": True}
            )
    
    # ========== FASE 5: SÍNTESIS ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="📊 Presentando resultados"
    )
    
    # Procesar stdout para extraer imágenes
    clean_text, images = process_execution_output(execution_result.stdout if execution_result else "")
    
    result_dict = execution_result.to_dict() if execution_result else {}
    if clean_text != execution_result.stdout:
        result_dict["stdout"] = clean_text
        result_dict["images_count"] = len(images)
    
    # ✅ Reemplazar variables en synthesizer prompt
    synth_prompt = synth_node.system_prompt
    synth_prompt = synth_prompt.replace("{{user_query}}", query)
    synth_prompt = synth_prompt.replace("{{language}}", language)
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
    
    # Si hay imágenes, agregarlas
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


# ============================================
# Registro del Agente
# ============================================

def register_code_execution_agent():
    """Registrar el agente de ejecución de código"""
    
    chain_registry.register(
        chain_id="code_execution",
        definition=CODE_EXECUTION_DEFINITION,
        builder=build_code_execution_agent
    )
    
    logger.info("Code Execution Agent registrado (v2.0.0)")
