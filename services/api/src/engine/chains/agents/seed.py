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
            {"id": "data_analysis", "name": "Análisis de Datos Tabulares",
             "description": "Técnicas para analizar archivos Excel/CSV con pandas: lectura, transformación, gráficos, exportación"},
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
        "excluded_core_tools": [
            "python", "javascript", "shell",
            "web_search", "web_fetch",
            "read_file", "write_file", "edit_file", "list_directory", "search_files",
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

    # ── Microsoft 365 Assistant ──────────────────────────────────
    m365_dir = _AGENTS_DIR / "m365_assistant"
    agents.append({
        "agent_id": "m365_assistant",
        "name": "Microsoft 365 Assistant",
        "description": "Asistente M365: correo, calendario, OneDrive, Teams y directorio corporativo",
        "role": "Asistente de Productividad Microsoft 365",
        "expertise": "Experto en gestión de correo, calendario, archivos, Teams y directorio corporativo via Microsoft Graph",
        "task_requirements": "Consultas sobre correo, calendario, archivos OneDrive, Teams o directorio corporativo",
        "system_prompt": _read_file(m365_dir / "prompts" / "system_prompt.txt"),
        "domain_tools": [
            "m365_mail_list", "m365_mail_folders", "m365_mail_send",
            "m365_calendar_list", "m365_calendar_events", "m365_calendar_create_event",
            "m365_onedrive_root", "m365_onedrive_list", "m365_onedrive_search",
            "m365_teams_list", "m365_teams_chats", "m365_teams_channels",
            "m365_teams_members", "m365_teams_channel_messages", "m365_teams_send_message",
            "m365_directory_users", "m365_directory_groups", "m365_directory_group_members",
        ],
        "skills": _load_skills(m365_dir, [
            {"id": "m365_productivity", "name": "Microsoft 365 Productivity",
             "description": "Referencia completa de todas las herramientas M365, patrones de uso y mejores prácticas. CARGAR SIEMPRE."},
            {"id": "email_management", "name": "Gestión de Correo",
             "description": "Estrategias de búsqueda de correo, plantillas HTML y reglas de envío"},
            {"id": "calendar_teams", "name": "Calendario y Teams",
             "description": "Gestión de agenda, creación de eventos, envío de mensajes Teams"},
        ]),
        "version": "1.0.0",
        "icon": "mail",
    })

    # ── Blender 3D Creator ────────────────────────────────────────
    b3d_dir = _AGENTS_DIR / "blender_3d_creator"
    agents.append({
        "agent_id": "blender_3d_creator",
        "name": "Blender 3D Creator",
        "description": "Artista 3D: creación de escenas, modelado, materiales, texturas, iluminación e importación de assets en Blender",
        "role": "Artista 3D y Technical Director",
        "expertise": "Experto en Blender Python API (bpy), modelado procedural, composición de escenas, "
                     "materiales PBR, iluminación, y gestión de assets 3D desde PolyHaven, Sketchfab "
                     "e IA generativa (Hyper3D, Hunyuan3D)",
        "task_requirements": "Tareas de creación 3D: escenas, objetos, materiales, texturas, iluminación, "
                             "renders, importación de modelos, automatización de Blender",
        "system_prompt": _read_file(b3d_dir / "prompts" / "system_prompt.txt"),
        "domain_tools": [
            "mcp_blender_get_scene_info",
            "mcp_blender_get_object_info",
            "mcp_blender_get_viewport_screenshot",
            "mcp_blender_execute_blender_code",
            "mcp_blender_get_polyhaven_status",
            "mcp_blender_get_polyhaven_categories",
            "mcp_blender_search_polyhaven_assets",
            "mcp_blender_download_polyhaven_asset",
            "mcp_blender_set_texture",
            "mcp_blender_get_sketchfab_status",
            "mcp_blender_search_sketchfab_models",
            "mcp_blender_get_sketchfab_model_preview",
            "mcp_blender_download_sketchfab_model",
            "mcp_blender_get_hyper3d_status",
            "mcp_blender_generate_hyper3d_model_via_text",
            "mcp_blender_generate_hyper3d_model_via_images",
            "mcp_blender_poll_rodin_job_status",
            "mcp_blender_import_generated_asset",
            "mcp_blender_get_hunyuan3d_status",
            "mcp_blender_generate_hunyuan3d_model",
            "mcp_blender_poll_hunyuan_job_status",
            "mcp_blender_import_generated_asset_hunyuan",
        ],
        "excluded_core_tools": [
            "web_search", "web_fetch",
            "shell",
            "read_file", "write_file", "edit_file", "list_directory", "search_files",
        ],
        "skills": _load_skills(b3d_dir, [
            {"id": "scene_composition", "name": "Composición de Escenas",
             "description": "Planificación de escenas 3D: escala, orden de creación, jerarquía, cámara"},
            {"id": "materials_and_lighting", "name": "Materiales e Iluminación",
             "description": "Materiales PBR, paletas de colores, setup de iluminación, HDRIs"},
            {"id": "asset_workflow", "name": "Flujo de Assets Externos",
             "description": "Estrategia de selección de fuentes: Sketchfab, PolyHaven, Hyper3D, código Python"},
            {"id": "blender_python_patterns", "name": "Patrones Blender Python",
             "description": "Patrones bpy comunes: materiales, bmesh, cámara, render, errores frecuentes. CARGAR SIEMPRE."},
        ]),
        "version": "1.0.0",
        "icon": "view_in_ar",
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
