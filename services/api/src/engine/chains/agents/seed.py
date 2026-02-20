"""
Seed de agentes por defecto.

Se ejecuta UNA vez al arrancar si la tabla agent_definitions esta vacia.
Lee los prompts y skills desde los ficheros .md actuales y los inserta en BD.
Despues de este seed inicial, los ficheros ya no se usan; la BD es la fuente unica.
"""

from pathlib import Path
from typing import List, Dict, Any

import structlog

logger = structlog.get_logger(__name__)

_AGENTS_DIR = Path(__file__).parent


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _load_skills(agent_dir: Path, skill_defs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    skills_dir = agent_dir / "skills"
    result = []
    for s in skill_defs:
        content = _read_file(skills_dir / f"{s['id']}.md")
        result.append({
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "content": content,
        })
    return result


# ── Agent definitions ──────────────────────────────────────────────

COMMUNICATION_FALLBACK_PROMPT = """Eres un Director de Comunicación experto en storytelling corporativo.

Ayudas a definir:
- Tono y estilo del mensaje según la audiencia
- Estructuras narrativas efectivas
- Arcos emocionales para conectar con la audiencia
- Mensajes clave y call-to-actions

Proporciona recomendaciones claras y accionables para comunicar efectivamente."""


def get_default_agents() -> List[Dict[str, Any]]:
    """Devuelve los 5 agentes por defecto listos para insertar en BD."""

    agents: List[Dict[str, Any]] = []

    # ── SAP Analyst ────────────────────────────────────────────────
    sap_dir = _AGENTS_DIR / "sap_analyst"
    agents.append({
        "agent_id": "sap_analyst",
        "name": "SAP BIW Analyst",
        "description": "Analista de datos SAP BIW: extracción, queries, P&L, reportes via proxy-biw",
        "role": "Analista de Datos SAP BIW",
        "expertise": "Experto en extracción y análisis de datos SAP BIW usando herramientas bi_* conectadas a proxy-biw",
        "task_requirements": "Consultas sobre datos SAP BIW: queries, P&L, ventas, análisis",
        "system_prompt": _read_file(sap_dir / "prompts" / "system_prompt.txt"),
        "domain_tools": [
            "bi_list_catalogs", "bi_list_queries", "bi_get_metadata",
            "bi_get_dimension_values", "bi_get_query_variables",
            "bi_execute_query", "bw_execute_mdx",
            "generate_spreadsheet",
        ],
        "skills": _load_skills(sap_dir, [
            {"id": "sap_biw_analyst", "name": "SAP BIW Analyst",
             "description": "Conocimiento de dominio completo: queries KH Lloreda, dimensiones, medidas, versiones, ejemplos de uso. CARGAR SIEMPRE."},
            {"id": "biw_data_extraction", "name": "Extracción BIW",
             "description": "Técnicas de extracción: InfoCubes, DSOs, queries BEx, navegación multidimensional"},
            {"id": "financial_analysis", "name": "Análisis Financiero",
             "description": "P&L, márgenes, ratios financieros, comparativas"},
            {"id": "sales_analysis", "name": "Análisis de Ventas",
             "description": "Ventas por segmento, canal, marca, evolución temporal"},
        ]),
        "version": "4.0.0",
        "icon": "analytics",
    })

    # ── Designer ───────────────────────────────────────────────────
    des_dir = _AGENTS_DIR / "designer"
    agents.append({
        "agent_id": "designer_agent",
        "name": "Designer",
        "description": "Diseñador visual: imágenes, vídeos, presentaciones, logos",
        "role": "Diseñador Visual",
        "expertise": "Experto en diseño visual: generación de imágenes, vídeos cinematográficos y presentaciones profesionales",
        "task_requirements": "Describe la tarea: imagen, vídeo, presentación, o cualquier combinación",
        "system_prompt": _read_file(des_dir / "prompts" / "system_prompt.txt"),
        "domain_tools": [
            "generate_image", "edit_image", "generate_video",
            "generate_slides", "analyze_image",
        ],
        "skills": _load_skills(des_dir, [
            {"id": "design", "name": "Design", "description": "Generación de imágenes, vídeos y presentaciones profesionales con IA"},
            {"id": "slides", "name": "Presentaciones", "description": "Diseño de slides HTML/CSS modernos con templates profesionales"},
            {"id": "design_critique", "name": "Design Critique", "description": "Criterios de auto-evaluación para diseño"},
            {"id": "data_viz", "name": "Visualización de Datos", "description": "Gráficos, charts e infografías efectivas"},
            {"id": "branding", "name": "Branding e Identidad Visual", "description": "Logos, paletas de colores y elementos de identidad visual"},
        ]),
        "version": "3.0.0",
        "icon": "palette",
    })

    # ── Researcher ─────────────────────────────────────────────────
    res_dir = _AGENTS_DIR / "researcher"
    agents.append({
        "agent_id": "researcher_agent",
        "name": "Researcher",
        "description": "Investigador: búsqueda web, datos actuales, fuentes",
        "role": "Investigador",
        "expertise": "Experto en búsqueda y compilación de información de internet",
        "task_requirements": "Describe qué información necesitas investigar",
        "system_prompt": _read_file(res_dir / "prompts" / "system_prompt.txt"),
        "domain_tools": ["web_search", "web_fetch"],
        "skills": _load_skills(res_dir, [
            {"id": "deep_research", "name": "Investigación Profunda",
             "description": "Técnicas para investigaciones exhaustivas y compilación de información de calidad"},
        ]),
        "version": "3.0.0",
        "icon": "search",
    })

    # ── Communication ──────────────────────────────────────────────
    com_dir = _AGENTS_DIR / "communication"
    com_prompt = _read_file(com_dir / "prompts" / "system_prompt.txt")
    if not com_prompt.strip():
        com_prompt = COMMUNICATION_FALLBACK_PROMPT

    agents.append({
        "agent_id": "communication_agent",
        "name": "Communication Strategist",
        "description": "Estratega de comunicación experto en storytelling y narrativa efectiva",
        "role": "Director de Comunicación",
        "expertise": "Experto en comunicación estratégica y storytelling corporativo",
        "task_requirements": "Describe qué necesitas comunicar y a qué audiencia",
        "system_prompt": com_prompt,
        "domain_tools": [],
        "skills": _load_skills(com_dir, [
            {"id": "storytelling", "name": "Storytelling y Narrativa",
             "description": "Técnicas para crear narrativas efectivas y comunicación persuasiva"},
        ]),
        "version": "3.0.0",
        "icon": "forum",
    })

    # ── RAG ────────────────────────────────────────────────────────
    rag_dir = _AGENTS_DIR / "rag"
    agents.append({
        "agent_id": "rag_agent",
        "name": "RAG Specialist",
        "description": "Especialista en Recuperación Aumentada: responde preguntas basándose en documentos indexados",
        "role": "Especialista en Recuperación de Información",
        "expertise": "Experto en RAG (Retrieval Augmented Generation): búsqueda semántica, análisis documental y respuestas fundamentadas",
        "task_requirements": "Pregunta sobre documentos indexados, o solicitud de indexar nuevos documentos",
        "system_prompt": _read_file(rag_dir / "prompts" / "system_prompt.txt"),
        "domain_tools": ["rag_search", "rag_ingest_document", "rag_get_collection_stats"],
        "skills": [],
        "version": "1.0.0",
        "icon": "library_books",
    })

    return agents


async def seed_default_agents() -> int:
    """Inserta agentes por defecto en BD si la tabla esta vacia. Devuelve numero insertados."""
    from src.db.repositories.agent_definitions import AgentDefinitionRepository

    count = await AgentDefinitionRepository.count()
    if count > 0:
        logger.info("agent_definitions already has data, skipping seed", count=count)
        return 0

    agents = get_default_agents()
    inserted = 0
    for agent_data in agents:
        try:
            await AgentDefinitionRepository.create(agent_data)
            inserted += 1
            logger.info("Seeded agent", agent_id=agent_data["agent_id"])
        except Exception as e:
            logger.error("Failed to seed agent", agent_id=agent_data["agent_id"], error=str(e))

    logger.info("Agent seed complete", inserted=inserted, total=len(agents))
    return inserted
