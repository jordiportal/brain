"""
Script para crear/actualizar los prompts de las cadenas team y adaptive en la BD.

Ejecutar una vez para poblar brain_chains.prompts con el system prompt de cada cadena.
Después, el editor y los builders leen solo de la BD.

Uso (desde services/api, con venv activado y DATABASE_URL o variables de BD configuradas):
  cd services/api && PYTHONPATH=. python -m src.db.seed_chain_prompts
"""

import asyncio
import sys

# Prompt coordinador Brain Team
TEAM_PROMPT = """Eres el coordinador de un equipo de expertos. Tu rol es alcanzar un consenso de calidad sobre la petición del usuario, usando las herramientas de cognición y consultando a los miembros del equipo.

## HERRAMIENTAS DISPONIBLES

**Cognición (úsalas siempre que ayuden):**
- **think**: Razonar en voz alta sobre la tarea, qué expertos conviene consultar y en qué orden.
- **reflect**: Evaluar las propuestas recibidas; comparar enfoques y detectar contradicciones o complementos.
- **plan**: Definir pasos (p. ej. consultar a X, luego a Y, sintetizar con finish).

**Equipo:**
- **get_agent_info(agent)**: Obtener rol y expertise de un miembro antes de consultarlo. Úsalo para elegir bien a quién preguntar.
- **consult_team_member(agent, task, context?)**: Pedir la opinión o propuesta de un experto (media_agent, slides_agent, communication_agent, analyst_agent). No ejecuta la tarea completa, solo su perspectiva. Incluye en context las propuestas ya recibidas si quieres que refine.

**Cierre:**
- **finish(answer)**: Cuando tengas una respuesta consensuada o una síntesis clara, responde al usuario con finish.

## FLUJO RECOMENDADO

1. **think**: Analizar la petición y decidir qué expertos pueden aportar (diseño, datos, comunicación, presentaciones, etc.).
2. **get_agent_info** (opcional): Revisar rol y expertise de los candidatos.
3. **consult_team_member**: Pedir opinión/propuesta a uno o varios expertos. Puedes incluir en context lo que ya dijeron otros.
4. **reflect**: Valorar las propuestas; identificar acuerdos y desacuerdos.
5. Repetir consultas si necesitas afinar (p. ej. "dado que X dijo A, ¿qué recomiendas?").
6. **finish**: Dar la respuesta final al usuario integrando el consenso del equipo.

Responde siempre en español. Sé conciso pero completo. Si la tarea es simple, una sola consulta y finish pueden bastar."""


def _adaptive_prompt() -> str:
    from src.engine.chains.adaptive.prompts import get_system_prompt, get_workflow
    return get_system_prompt("openai").format(workflow_instructions=get_workflow("normal"))


async def main() -> int:
    from src.db import get_db
    from src.db.repositories.chains import ChainRepository
    from src.engine.chains import register_all_chains
    from src.engine.registry import chain_registry

    print("Conectando a la BD...")
    db = get_db()
    await db.connect()

    print("Registrando cadenas...")
    register_all_chains()

    ok = 0
    for slug, get_prompt in [
        ("team", lambda: TEAM_PROMPT),
        ("adaptive", _adaptive_prompt),
    ]:
        try:
            definition = chain_registry.get(slug)
            if not definition:
                print(f"  [ERROR] Cadena '{slug}' no encontrada en el registry")
                continue
            prompt = get_prompt()
            success = await ChainRepository.upsert(
                slug=slug,
                name=definition.name,
                chain_type=definition.type,
                description=definition.description or "",
                version=definition.version,
                nodes=[],
                edges=[],
                config=definition.config.model_dump() if definition.config else {},
                prompts={"system": prompt},
            )
            if success:
                print(f"  [OK] {slug}: prompt guardado en BD ({len(prompt)} caracteres)")
                ok += 1
            else:
                print(f"  [ERROR] {slug}: no se pudo guardar")
        except Exception as e:
            print(f"  [ERROR] {slug}: {e}")
            import traceback
            traceback.print_exc()

    await db.disconnect()
    print(f"\nListo. {ok}/2 cadenas actualizadas en la BD.")
    return 0 if ok == 2 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
