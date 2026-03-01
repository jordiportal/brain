"""
Base Subagent - Clase base para subagentes especializados.

Un subagente es solo configuracion: prompt + tools + skills + metadata.
El codigo de ejecucion (run_session_loop) es 100% compartido.

Las definiciones se cargan desde BD (tabla agent_definitions).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

import structlog

logger = structlog.get_logger()


@dataclass
class SubAgentResult:
    """Resultado de la ejecucion de un subagente."""

    success: bool
    response: str
    agent_id: str
    agent_name: str
    tools_used: List[str] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    videos: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "response": self.response,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "tools_used": self.tools_used,
            "images": self.images,
            "videos": self.videos,
            "sources": self.sources,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "has_images": len(self.images) > 0,
            "has_videos": len(self.videos) > 0,
            "has_sources": len(self.sources) > 0,
        }


@dataclass
class Skill:
    """Skill cargable por un subagente (contenido almacenado en BD)."""
    id: str
    name: str
    description: str
    content: str = ""


class BaseSubAgent:
    """
    Subagente especializado — instanciable directamente desde BD.

    Toda la diferenciacion viene de:
      - system_prompt (texto)
      - domain_tools (lista de IDs)
      - available_skills (lista de Skill con contenido inline)
      - metadata (role, expertise, etc.)

    El codigo de ejecucion es compartido via run_session_loop.
    """

    MAX_MEMORY_MESSAGES = 10

    def __init__(
        self,
        agent_id: str = "base_agent",
        name: str = "Base Agent",
        description: str = "",
        version: str = "1.0.0",
        role: str = "Especialista",
        expertise: str = "",
        task_requirements: str = "",
        system_prompt: str = "You are a specialized agent.",
        domain_tools: Optional[List[str]] = None,
        core_tools_enabled: bool = True,
        excluded_core_tools: Optional[List[str]] = None,
        available_skills: Optional[List[Skill]] = None,
        icon: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ):
        self.id = agent_id
        self.name = name
        self.description = description
        self.version = version
        self.role = role
        self.expertise = expertise
        self.task_requirements = task_requirements
        self.system_prompt = system_prompt
        self.domain_tools: List[str] = domain_tools or []
        self.core_tools_enabled = core_tools_enabled
        self.excluded_core_tools: set = set(excluded_core_tools or [])
        self.available_skills: List[Skill] = available_skills or []
        self.icon = icon
        self.settings: Dict[str, Any] = settings or {}

        self._skills_cache: Dict[str, str] = {}
        self._memory_store: Dict[str, List[dict]] = {}

        logger.info(f"SubAgent initialized: {self.id} ({self.name})")

    @classmethod
    def from_definition(cls, defn: Any) -> "BaseSubAgent":
        """Crea una instancia desde un AgentDefinition (Pydantic model de BD)."""
        skills = []
        for s in (defn.skills or []):
            skills.append(Skill(
                id=s.get("id", ""),
                name=s.get("name", ""),
                description=s.get("description", ""),
                content=s.get("content", ""),
            ))

        return cls(
            agent_id=defn.agent_id,
            name=defn.name,
            description=defn.description or "",
            version=defn.version or "1.0.0",
            role=defn.role or "Especialista",
            expertise=defn.expertise or "",
            task_requirements=defn.task_requirements or "",
            system_prompt=defn.system_prompt,
            domain_tools=list(defn.domain_tools or []),
            core_tools_enabled=defn.core_tools_enabled,
            excluded_core_tools=list(defn.excluded_core_tools or []),
            available_skills=skills,
            icon=defn.icon,
            settings=dict(defn.settings or {}),
        )

    # ── Skills ────────────────────────────────────────────────────

    def load_skill(self, skill_id: str) -> Dict[str, Any]:
        """Carga un skill (contenido inline desde BD). Llamado por el LLM via tool."""
        valid_ids = [s.id for s in self.available_skills]
        if skill_id not in valid_ids:
            return {"success": False, "error": f"Skill '{skill_id}' no disponible. Validos: {valid_ids}"}

        if skill_id in self._skills_cache:
            return {"success": True, "skill_id": skill_id, "content": self._skills_cache[skill_id], "from_cache": True}

        for s in self.available_skills:
            if s.id == skill_id:
                self._skills_cache[skill_id] = s.content
                logger.info(f"Loaded skill: {skill_id} ({len(s.content)} chars)")
                return {"success": True, "skill_id": skill_id, "content": s.content, "chars": len(s.content)}

        return {"success": False, "error": f"Skill '{skill_id}' content not found"}

    def get_load_skill_tool(self) -> Optional[Dict[str, Any]]:
        """Tool definition para load_skill (solo si hay skills)."""
        if not self.available_skills:
            return None

        skill_descriptions = "\n".join(f"- {s.id}: {s.description}" for s in self.available_skills)

        return {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": (
                    "Carga conocimiento especializado para mejorar tu trabajo.\n"
                    "Usa esta herramienta ANTES de ejecutar la tarea si necesitas conocimiento especifico.\n\n"
                    f"Skills disponibles:\n{skill_descriptions}\n\n"
                    "El skill cargado te dara ejemplos, templates y mejores practicas."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "enum": [s.id for s in self.available_skills],
                            "description": "ID del skill a cargar",
                        }
                    },
                    "required": ["skill_id"],
                },
            },
        }

    def get_skills_for_prompt(self) -> str:
        if not self.available_skills:
            return ""
        skills_list = "\n".join(f"- **{s.id}**: {s.description}" for s in self.available_skills)
        return (
            "\n\n## SKILLS DISPONIBLES\n\n"
            "Tienes acceso a conocimiento especializado. Usa `load_skill(skill_id)` para cargar:\n"
            f"{skills_list}\n\n"
            "Carga un skill si la tarea requiere conocimiento tecnico especifico."
        )

    def list_available_skills(self) -> List[Dict[str, Any]]:
        return [{"id": s.id, "name": s.name, "description": s.description} for s in self.available_skills]
    
    # ── Tools ───────────────────────────────────────────────────────

    def get_tools(self) -> List[Any]:
        """Tools de dominio + core tools universales (excepto delegation y excluded)."""
        from src.tools import tool_registry
        from src.tools.core import CORE_TOOLS

        all_tool_ids = set(self.domain_tools)

        if self.core_tools_enabled:
            delegation_tools = {"delegate", "get_agent_info"}
            skip = delegation_tools | self.excluded_core_tools
            for k in CORE_TOOLS:
                if k not in skip:
                    all_tool_ids.add(k)

        tools = []
        missing = []
        for tid in all_tool_ids:
            t = tool_registry.get(tid)
            if t:
                tools.append(t)
            else:
                missing.append(tid)

        if missing:
            logger.warning(f"SubAgent {self.id}: tools not found: {missing}")

        return tools

    # ── Consult ───────────────────────────────────────────────────

    async def consult(
        self,
        topic: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "openai",
        api_key: Optional[str] = None,
    ) -> SubAgentResult:
        from ..llm_utils import call_llm_with_tools

        prompt = (
            f"Eres {self.role}. {self.expertise}\n\n"
            f"Un colega te consulta sobre: {topic}\n"
            + (f"\nContexto adicional: {context}\n" if context else "")
            + "\nResponde breve y profesional: opinion experta, 2-3 opciones, pregunta para afinar."
        )
        try:
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": f"Eres {self.role}. Responde de forma concisa y profesional."},
                    {"role": "user", "content": prompt},
                ],
                tools=[],
                temperature=0.7,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model,
            )
            return SubAgentResult(
                success=True,
                response=response.content or "Sin respuesta",
                agent_id=self.id,
                agent_name=self.name,
                data={"mode": "consult", "topic": topic},
            )
        except Exception as e:
            logger.error(f"Consult error: {e}")
            return SubAgentResult(
                success=False,
                response=f"Error en consulta: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
            )

    # ── Memory ────────────────────────────────────────────────────

    def _load_memory(self, session_id: str, max_messages: int = 10) -> List[dict]:
        if not session_id or session_id not in self._memory_store:
            return []
        msgs = self._memory_store[session_id]
        keep = min(len(msgs), max_messages * 2)
        return msgs[-keep:] if keep else []

    def _save_memory(self, session_id: str, user_content: str, assistant_content: str, max_messages: int = 10) -> None:
        if not session_id:
            return
        if session_id not in self._memory_store:
            self._memory_store[session_id] = []
        self._memory_store[session_id].append({"role": "user", "content": user_content})
        self._memory_store[session_id].append({"role": "assistant", "content": assistant_content})
        if len(self._memory_store[session_id]) > max_messages * 2:
            self._memory_store[session_id] = self._memory_store[session_id][-max_messages * 2:]

    def clear_memory(self, session_id: str) -> None:
        if session_id in self._memory_store:
            del self._memory_store[session_id]

    # ── Execute ───────────────────────────────────────────────────

    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> SubAgentResult:
        """Ejecuta tarea usando run_session_loop compartido."""
        import time
        import uuid
        from src.engine.chains.adaptive.executor import run_session_loop, AgentContext

        start_time = time.time()
        exec_id = session_id or str(uuid.uuid4())
        agent_context = AgentContext(
            session_id=session_id, parent_id=None, agent_type=self.id, max_iterations=12,
        )

        now = datetime.now()
        date_ctx = (
            f"\n\n## FECHA ACTUAL\n"
            f"Hoy es {now.strftime('%A %d de %B de %Y')} ({now.strftime('%Y-%m-%d')}). "
            f"Mes: {now.strftime('%Y%m')}. Ano: {now.year}.\n"
        )
        messages = [{"role": "system", "content": self.system_prompt + date_ctx + self.get_skills_for_prompt()}]

        if session_id:
            for msg in self._load_memory(session_id, max_messages=self.MAX_MEMORY_MESSAGES):
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        user_content = f"Tarea: {task}"
        if context:
            user_content += f"\n\nContexto adicional: {context}"
        messages.append({"role": "user", "content": user_content})

        tools_llm = [t.to_function_schema() for t in self.get_tools()]

        if not llm_url or not model or not provider_type:
            return SubAgentResult(
                success=False, response="Configuracion LLM no disponible.",
                agent_id=self.id, agent_name=self.name,
                error="LLM_NOT_CONFIGURED", execution_time_ms=0,
            )

        try:
            result = await run_session_loop(
                execution_id=exec_id, messages=messages, tools=tools_llm,
                llm_url=llm_url, model=model, provider_type=provider_type,
                api_key=api_key, agent_context=agent_context, emit_brain_events=False,
            )
            response_text = result.final_answer or ""
            if not response_text and result.tool_results:
                response_text = (
                    f"Completado en {result.iteration} iteraciones. "
                    f"Herramientas: {', '.join(tr['tool'] for tr in result.tool_results)}"
                )
            if session_id and response_text:
                self._save_memory(session_id, user_content, response_text, max_messages=self.MAX_MEMORY_MESSAGES)
            return SubAgentResult(
                success=True, response=response_text,
                agent_id=self.id, agent_name=self.name,
                tools_used=[tr["tool"] for tr in result.tool_results],
                images=result.images, videos=result.videos,
                data={"tool_results": result.tool_results} if result.tool_results else {},
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"SubAgent execute error: {e}", agent_id=self.id, exc_info=True)
            return SubAgentResult(
                success=False, response=str(e),
                agent_id=self.id, agent_name=self.name, error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


# ══════════════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════════════

class SubAgentRegistry:
    """Registry singleton de subagentes disponibles."""

    def __init__(self):
        self._agents: Dict[str, BaseSubAgent] = {}
        self._initialized = False

    def register(self, agent: BaseSubAgent) -> None:
        self._agents[agent.id] = agent
        self._initialized = True
        logger.info(f"SubAgent registered: {agent.id}")

    def clear(self) -> None:
        self._agents.clear()
        self._initialized = False

    def get(self, agent_id: str) -> Optional[BaseSubAgent]:
        return self._agents.get(agent_id)

    def list_ids(self) -> List[str]:
        return list(self._agents.keys())

    def list(self) -> List[BaseSubAgent]:
        return list(self._agents.values())

    def is_initialized(self) -> bool:
        return self._initialized

    def get_description(self) -> str:
        return "\n".join(f"- {a.id}: {a.description}" for a in self._agents.values())


subagent_registry = SubAgentRegistry()
