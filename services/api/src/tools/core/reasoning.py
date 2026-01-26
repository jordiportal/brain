"""
Brain 2.0 Core Tools - Reasoning (4 meta-tools)

- think: Razonar antes de actuar
- reflect: Evaluar resultados obtenidos
- plan: Crear plan estructurado para tareas complejas
- finish: Señalar respuesta final
"""

from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger()


# ============================================
# Tool Handlers
# ============================================

async def think(
    thoughts: str
) -> Dict[str, Any]:
    """
    Meta-tool para razonamiento explícito antes de actuar.
    Permite al agente planificar y analizar la situación.
    
    Args:
        thoughts: Razonamiento sobre qué hacer, qué información hay,
                 qué se necesita, posibles enfoques.
    
    Returns:
        {"acknowledged": True, "thoughts": str}
    """
    logger.info(f"🧠 THINK: {thoughts[:200]}...")
    
    return {
        "acknowledged": True,
        "thoughts": thoughts,
        "instruction": "Razonamiento registrado. Ahora puedes proceder con tu plan."
    }


async def reflect(
    observation: str,
    success: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Meta-tool para reflexionar sobre resultados obtenidos.
    Permite al agente evaluar el progreso y ajustar estrategia.
    
    Args:
        observation: Análisis de los resultados obtenidos,
                    qué significan, si se logró el objetivo.
        success: Indica si el paso anterior fue exitoso (opcional)
    
    Returns:
        {"acknowledged": True, "observation": str}
    """
    status = "✅" if success else "❌" if success is False else "🔍"
    logger.info(f"{status} REFLECT: {observation[:200]}...")
    
    return {
        "acknowledged": True,
        "observation": observation,
        "success": success,
        "instruction": "Reflexión registrada. Decide los próximos pasos basándote en esta evaluación."
    }


async def plan(
    goal: str,
    steps: List[str]
) -> Dict[str, Any]:
    """
    Meta-tool para crear un plan estructurado.
    Útil para tareas complejas que requieren múltiples pasos.
    
    Args:
        goal: Objetivo final a lograr
        steps: Lista de pasos a seguir en orden
    
    Returns:
        {"acknowledged": True, "goal": str, "steps": list}
    """
    logger.info(f"📋 PLAN: {goal}")
    for i, step in enumerate(steps, 1):
        logger.info(f"   {i}. {step[:100]}")
    
    return {
        "acknowledged": True,
        "goal": goal,
        "steps": steps,
        "step_count": len(steps),
        "instruction": f"Plan creado con {len(steps)} pasos. Ejecuta cada paso en orden."
    }


async def finish(
    answer: str,
    confidence: Optional[float] = None
) -> Dict[str, Any]:
    """
    Meta-tool para señalar que se tiene la respuesta final.
    Indica que la tarea está completa y proporciona la respuesta al usuario.
    
    Args:
        answer: Respuesta final completa para el usuario
        confidence: Nivel de confianza en la respuesta (0.0-1.0, opcional)
    
    Returns:
        {"final_answer": str, "done": True}
    """
    confidence_str = f" (confianza: {confidence:.0%})" if confidence is not None else ""
    logger.info(f"✅ FINISH{confidence_str}: respuesta de {len(answer)} caracteres")
    
    return {
        "final_answer": answer,
        "done": True,
        "confidence": confidence,
        "instruction": "Respuesta final lista para el usuario."
    }


# ============================================
# Tool Definitions for Registry
# ============================================

REASONING_TOOLS = {
    "think": {
        "id": "think",
        "name": "think",
        "description": "Razona sobre la situación antes de actuar. Usa para planificar, analizar información disponible, considerar enfoques.",
        "parameters": {
            "type": "object",
            "properties": {
                "thoughts": {
                    "type": "string",
                    "description": "Tu razonamiento: qué sabes, qué necesitas, cómo proceder, qué podría fallar."
                }
            },
            "required": ["thoughts"]
        },
        "handler": think
    },
    "reflect": {
        "id": "reflect",
        "name": "reflect",
        "description": "Reflexiona sobre los resultados obtenidos. Usa después de ejecutar acciones para evaluar progreso.",
        "parameters": {
            "type": "object",
            "properties": {
                "observation": {
                    "type": "string",
                    "description": "Tu análisis: qué obtuviste, qué significa, si lograste el objetivo, qué hacer después."
                },
                "success": {
                    "type": "boolean",
                    "description": "Indica si el paso anterior fue exitoso (opcional)"
                }
            },
            "required": ["observation"]
        },
        "handler": reflect
    },
    "plan": {
        "id": "plan",
        "name": "plan",
        "description": "Crea un plan estructurado para tareas complejas. Define objetivo y pasos a seguir.",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Objetivo final a lograr"
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de pasos a seguir en orden"
                }
            },
            "required": ["goal", "steps"]
        },
        "handler": plan
    },
    "finish": {
        "id": "finish",
        "name": "finish",
        "description": "Proporciona la respuesta final al usuario. Usa cuando tengas la respuesta completa.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Respuesta final completa para el usuario, con formato markdown si es apropiado."
                },
                "confidence": {
                    "type": "number",
                    "description": "Nivel de confianza en la respuesta (0.0-1.0, opcional)"
                }
            },
            "required": ["answer"]
        },
        "handler": finish
    }
}
