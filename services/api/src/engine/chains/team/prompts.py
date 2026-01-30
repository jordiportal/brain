"""
Prompts para el TeamCoordinator.
"""

from typing import List, Dict, Any


TEAM_SELECTION_PROMPT = """Eres un coordinador de equipos de trabajo. Tu tarea es seleccionar los agentes más apropiados para una tarea específica.

## AGENTES DISPONIBLES
{agents_description}

## TAREA
{task}

## INSTRUCCIONES
1. Analiza qué tipo de tarea es
2. Identifica qué habilidades se necesitan
3. Selecciona los agentes que mejor pueden contribuir
4. Máximo 4 agentes por equipo

## RESPUESTA
Lista los IDs de los agentes seleccionados, uno por línea.
Solo incluye los agentes que realmente aporten valor a esta tarea específica.
"""


EXECUTION_PROMPT = """Eres el agente líder encargado de ejecutar una tarea con el consenso del equipo.

## TAREA ORIGINAL
{task}

## CONTRIBUCIONES DEL EQUIPO
{contributions}

## INSTRUCCIONES
Utiliza las contribuciones de todos los agentes para crear el mejor resultado posible.
Integra las diferentes perspectivas de manera coherente.
"""


def build_team_selection_messages(
    task: str,
    available_agents: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    """Construye los mensajes para la selección de equipo."""
    
    # Formatear descripción de agentes
    agents_desc = []
    for agent in available_agents:
        desc = f"""- **{agent['id']}** ({agent['name']})
  Rol: {agent['role']}
  Expertise: {agent['expertise'][:200]}"""
        agents_desc.append(desc)
    
    agents_text = "\n\n".join(agents_desc)
    
    prompt = TEAM_SELECTION_PROMPT.format(
        agents_description=agents_text,
        task=task
    )
    
    return [
        {
            "role": "system",
            "content": "Eres un coordinador experto en formar equipos de trabajo. Responde de forma concisa."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]


def build_execution_messages(
    task: str,
    contributions: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Construye los mensajes para la ejecución final."""
    
    # Formatear contribuciones
    contrib_parts = []
    for agent_id, content in contributions.items():
        if isinstance(content, dict):
            summary = content.get("response", content.get("summary", str(content)[:300]))
        else:
            summary = str(content)[:300]
        contrib_parts.append(f"**{agent_id}**: {summary}")
    
    contributions_text = "\n\n".join(contrib_parts)
    
    prompt = EXECUTION_PROMPT.format(
        task=task,
        contributions=contributions_text
    )
    
    return [
        {
            "role": "system",
            "content": "Ejecuta la tarea integrando las contribuciones del equipo."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
