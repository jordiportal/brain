"""
Base Subagent - Clase base simplificada para subagentes especializados.

Define la interfaz común y el registry para subagentes de dominio
(media, slides, sap, mail, office, etc.)

Sistema de Skills:
- Cada subagente puede tener skills en su directorio skills/
- Los skills son archivos .md con conocimiento especializado
- El LLM decide si cargar un skill usando la tool `load_skill`
- Los skills no sobrecargan el prompt base, se cargan bajo demanda
"""

from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import structlog

logger = structlog.get_logger()


@dataclass
class SubAgentResult:
    """Resultado de la ejecución de un subagente."""
    
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
        """Convierte a diccionario para serialización."""
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
            "has_sources": len(self.sources) > 0
        }


@dataclass
class Skill:
    """Representa un skill cargable por un subagente."""
    id: str
    name: str
    description: str  # Descripción para que el LLM sepa cuándo usarlo
    content: str = ""  # Contenido del skill (cargado desde archivo)


class BaseSubAgent(ABC):
    """
    Clase base abstracta para subagentes especializados.
    
    Cada subagente define:
    - id, name, description: Identificación
    - role: Rol profesional del subagente (ej: "Diseñador Visual")
    - expertise: Áreas de expertise para consultas
    - task_requirements: Qué necesita recibir para ejecutar
    - domain_tools: Lista de IDs de herramientas del dominio
    - system_prompt: Prompt de sistema
    - skills: Lista de skills disponibles (cargados bajo demanda)
    - execute(): Método principal de ejecución
    - consult(): Método para consultas de expertise (opcional)
    """
    
    id: str = "base_agent"
    name: str = "Base Agent"
    description: str = "Base agent"
    version: str = "1.0.0"
    domain_tools: List[str] = []
    system_prompt: str = "You are a specialized agent."
    
    # Rol y expertise del subagente
    role: str = "Especialista"
    expertise: str = "Puedo ayudarte con tareas de mi dominio."
    
    # Qué necesita para ejecutar
    task_requirements: str = "Descripción de la tarea a realizar."
    
    # Skills disponibles (definidos por cada subagente)
    available_skills: List[Skill] = []
    
    # Memoria conversacional por session_id (últimos N mensajes)
    MAX_MEMORY_MESSAGES = 10

    def __init__(self):
        logger.info(f"🤖 SubAgent initialized: {self.id} ({self.role})")
        self._skills_cache: Dict[str, str] = {}  # Cache de skills cargados
        self._loaded_skills: List[str] = []  # Skills cargados en la sesión actual
        self._memory_store: Dict[str, List[dict]] = {}  # session_id -> list of {role, content}
    
    def get_skills_dir(self) -> Path:
        """Obtiene el directorio de skills del subagente."""
        import inspect
        agent_file = inspect.getfile(self.__class__)
        return Path(agent_file).parent / "skills"
    
    def load_skill(self, skill_id: str) -> Dict[str, Any]:
        """
        Carga un skill desde archivo. Llamado por el LLM via tool.
        
        Returns:
            Dict con success, content (si ok), o error (si falla)
        """
        # Validar que el skill existe en available_skills
        valid_ids = [s.id for s in self.available_skills]
        if skill_id not in valid_ids:
            return {
                "success": False,
                "error": f"Skill '{skill_id}' no disponible. Skills válidos: {valid_ids}"
            }
        
        # Usar cache si ya está cargado
        if skill_id in self._skills_cache:
            logger.info(f"📚 Skill from cache: {skill_id}")
            return {
                "success": True,
                "skill_id": skill_id,
                "content": self._skills_cache[skill_id],
                "from_cache": True
            }
        
        # Cargar desde archivo
        skills_dir = self.get_skills_dir()
        skill_file = skills_dir / f"{skill_id}.md"
        
        if not skill_file.exists():
            logger.warning(f"Skill file not found: {skill_file}")
            return {
                "success": False,
                "error": f"Archivo de skill no encontrado: {skill_id}.md"
            }
        
        try:
            content = skill_file.read_text(encoding="utf-8")
            self._skills_cache[skill_id] = content
            self._loaded_skills.append(skill_id)
            logger.info(f"📚 Loaded skill: {skill_id} ({len(content)} chars)")
            return {
                "success": True,
                "skill_id": skill_id,
                "content": content,
                "chars": len(content)
            }
        except Exception as e:
            logger.error(f"Error loading skill {skill_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_load_skill_tool(self) -> Optional[Dict[str, Any]]:
        """
        Genera la definición de la tool `load_skill` para el LLM.
        Solo si el subagente tiene skills disponibles.
        
        Returns:
            Tool definition dict o None si no hay skills
        """
        if not self.available_skills:
            return None
        
        skill_descriptions = "\n".join(
            f"- {s.id}: {s.description}"
            for s in self.available_skills
        )
        
        return {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": f"""Carga conocimiento especializado para mejorar tu trabajo.
Usa esta herramienta ANTES de ejecutar la tarea si necesitas conocimiento específico.

Skills disponibles:
{skill_descriptions}

El skill cargado te dará ejemplos, templates y mejores prácticas.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {
                            "type": "string",
                            "enum": [s.id for s in self.available_skills],
                            "description": "ID del skill a cargar"
                        }
                    },
                    "required": ["skill_id"]
                }
            }
        }
    
    def get_skills_for_prompt(self) -> str:
        """
        Genera texto para incluir en el prompt sobre skills disponibles.
        """
        if not self.available_skills:
            return ""
        
        skills_list = "\n".join(
            f"- **{s.id}**: {s.description}"
            for s in self.available_skills
        )
        
        return f"""
## SKILLS DISPONIBLES

Tienes acceso a conocimiento especializado. Usa `load_skill(skill_id)` para cargar:
{skills_list}

Carga un skill si la tarea requiere conocimiento técnico específico."""
    
    def list_available_skills(self) -> List[Dict[str, Any]]:
        """Lista los skills disponibles."""
        return [
            {"id": s.id, "name": s.name, "description": s.description}
            for s in self.available_skills
        ]
    
    async def consult(
        self,
        topic: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "openai",
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """
        Consulta al subagente para obtener recomendaciones de su expertise.
        Por defecto, usa el LLM para generar una respuesta consultiva.
        Los subagentes pueden sobrescribir este método.
        """
        from ..llm_utils import call_llm_with_tools
        
        consult_prompt = f"""Eres {self.role}. {self.expertise}

Un colega te consulta sobre: {topic}

{f"Contexto adicional: {context}" if context else ""}

Responde de forma breve y profesional:
1. Da tu opinión experta sobre el enfoque
2. Sugiere 2-3 opciones o estilos que podrían funcionar
3. Haz una pregunta para afinar tu propuesta (opcional)

Sé conciso pero útil. Responde en español."""

        try:
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": f"Eres {self.role}. Responde de forma concisa y profesional."},
                    {"role": "user", "content": consult_prompt}
                ],
                tools=[],
                temperature=0.7,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            return SubAgentResult(
                success=True,
                response=response.content or "Sin respuesta",
                agent_id=self.id,
                agent_name=self.name,
                data={"mode": "consult", "topic": topic}
            )
        except Exception as e:
            logger.error(f"Consult error: {e}")
            return SubAgentResult(
                success=False,
                response=f"Error en consulta: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e)
            )
    
    def get_tools(self) -> List[Any]:
        """Obtiene las definiciones de tools de este dominio + core tools universales."""
        from src.tools import tool_registry
        from src.tools.core import CORE_TOOLS
        
        # Comenzar con las domain_tools específicas del subagente
        all_tool_ids = set(self.domain_tools)
        
        # Agregar todas las core tools excepto delegation (para evitar recursión infinita)
        delegation_tools = {"delegate", "get_agent_info"}
        core_tool_ids = [k for k in CORE_TOOLS.keys() if k not in delegation_tools]
        for tool_id in core_tool_ids:
            all_tool_ids.add(tool_id)
        
        # Obtener las definiciones de todas las herramientas
        tools = []
        missing_tools = []
        for tool_id in all_tool_ids:
            tool = tool_registry.get(tool_id)
            if tool:
                tools.append(tool)
            else:
                missing_tools.append(tool_id)
        
        if missing_tools:
            logger.warning(f"⚠️ SubAgent {self.id}: {len(missing_tools)} tools not found in registry: {missing_tools}")
        
        # DEBUG: Log detallado
        logger.info(f"🔧 SubAgent {self.id}:")
        logger.info(f"   Domain tools: {self.domain_tools}")
        logger.info(f"   All tool IDs: {len(all_tool_ids)} - {sorted(all_tool_ids)}")
        logger.info(f"   Found tools: {len(tools)} - {[t.id for t in tools]}")
        logger.info(f"   Missing tools: {len(missing_tools)} - {missing_tools}")
        
        return tools
    
    def _load_memory(self, session_id: str, max_messages: int = 10) -> List[dict]:
        """Carga los últimos mensajes de la sesión para contexto conversacional."""
        if not session_id or session_id not in self._memory_store:
            return []
        messages = self._memory_store[session_id]
        # max_messages = pares user+assistant; devolver últimos max_messages*2
        keep = min(len(messages), max_messages * 2)
        return messages[-keep:] if keep else []
    
    def _save_memory(
        self,
        session_id: str,
        user_content: str,
        assistant_content: str,
        max_messages: int = 10
    ) -> None:
        """Guarda user + assistant en la memoria de la sesión."""
        if not session_id:
            return
        if session_id not in self._memory_store:
            self._memory_store[session_id] = []
        self._memory_store[session_id].append({"role": "user", "content": user_content})
        self._memory_store[session_id].append({"role": "assistant", "content": assistant_content})
        if len(self._memory_store[session_id]) > max_messages * 2:
            self._memory_store[session_id] = self._memory_store[session_id][-max_messages * 2:]
    
    def clear_memory(self, session_id: str) -> None:
        """Limpia la memoria de una sesión."""
        if session_id in self._memory_store:
            del self._memory_store[session_id]
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """
        Ejecuta una tarea usando el mismo bucle compartido que el agente principal.
        Wrapper que construye mensajes y tools y llama a run_session_loop.
        Si session_id se proporciona, se usa memoria conversacional.
        """
        import time
        import uuid
        from src.engine.chains.adaptive.executor import (
            run_session_loop,
            AgentContext,
        )
        start_time = time.time()
        exec_id = session_id or str(uuid.uuid4())
        agent_context = AgentContext(
            session_id=session_id,
            parent_id=None,
            agent_type=self.id,
            max_iterations=12,
        )
        now = datetime.now()
        date_ctx = (
            f"\n\n## FECHA ACTUAL\n"
            f"Hoy es {now.strftime('%A %d de %B de %Y')} (fecha del sistema: {now.strftime('%Y-%m-%d')}). "
            f"Mes actual: {now.strftime('%Y%m')}. Año actual: {now.year}.\n"
        )
        messages = [{"role": "system", "content": self.system_prompt + date_ctx + (self.get_skills_for_prompt() or "")}]
        if session_id:
            memory = self._load_memory(session_id, max_messages=self.MAX_MEMORY_MESSAGES)
            for msg in memory:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        user_content = f"Tarea: {task}"
        if context:
            user_content += f"\n\nContexto adicional: {context}"
        messages.append({"role": "user", "content": user_content})
        tools_llm = [t.to_function_schema() for t in self.get_tools()]
        if not llm_url or not model or not provider_type:
            return SubAgentResult(
                success=False,
                response="Configuración LLM no disponible.",
                agent_id=self.id,
                agent_name=self.name,
                error="LLM_NOT_CONFIGURED",
                execution_time_ms=0,
            )
        try:
            result = await run_session_loop(
                execution_id=exec_id,
                messages=messages,
                tools=tools_llm,
                llm_url=llm_url,
                model=model,
                provider_type=provider_type,
                api_key=api_key,
                agent_context=agent_context,
                emit_brain_events=False,
            )
            response_text = result.final_answer or ""
            if not response_text and result.tool_results:
                response_text = f"Completado en {result.iteration} iteraciones. Herramientas: {', '.join(tr['tool'] for tr in result.tool_results)}"
            if session_id and response_text:
                self._save_memory(session_id, user_content, response_text, max_messages=self.MAX_MEMORY_MESSAGES)
            return SubAgentResult(
                success=True,
                response=response_text,
                agent_id=self.id,
                agent_name=self.name,
                tools_used=[tr["tool"] for tr in result.tool_results],
                images=result.images,
                videos=result.videos,
                data={"tool_results": result.tool_results} if result.tool_results else {},
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"SubAgent execute error: {e}", agent_id=self.id, exc_info=True)
            return SubAgentResult(
                success=False,
                response=str(e),
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


class SubAgentRegistry:
    """Registry singleton de subagentes disponibles."""
    
    def __init__(self):
        self._agents: Dict[str, BaseSubAgent] = {}
    
    def register(self, agent: BaseSubAgent) -> None:
        """Registra un subagente."""
        self._agents[agent.id] = agent
        logger.info(f"✅ SubAgent registered: {agent.id}")
    
    def get(self, agent_id: str) -> Optional[BaseSubAgent]:
        """Obtiene un subagente por ID."""
        return self._agents.get(agent_id)
    
    def list_ids(self) -> List[str]:
        """Lista los IDs disponibles."""
        return list(self._agents.keys())
    
    def list(self) -> List[BaseSubAgent]:
        """Lista todos los subagentes."""
        return list(self._agents.values())
    
    def is_initialized(self) -> bool:
        """Verifica si hay subagentes registrados."""
        return len(self._agents) > 0
    
    def get_description(self) -> str:
        """Descripción de todos los subagentes para prompts."""
        return "\n".join(
            f"- {a.id}: {a.description}"
            for a in self._agents.values()
        )


# Singleton
subagent_registry = SubAgentRegistry()
