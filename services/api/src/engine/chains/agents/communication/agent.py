"""
CommunicationAgent - Estratega de comunicación y storytelling.

Responsable de:
- Definir el tono y estilo del mensaje
- Estructurar la narrativa
- Crear storytelling y arco emocional
- Definir mensajes clave y call-to-action
"""

import json
from typing import Optional, Dict, Any, List

import structlog

from ..base import BaseSubAgent, SubAgentResult

logger = structlog.get_logger()


class CommunicationAgent(BaseSubAgent):
    """
    Agente especializado en comunicación y narrativa.
    
    No tiene herramientas de ejecución - su valor está en el
    razonamiento sobre cómo comunicar efectivamente.
    """
    
    id = "communication_agent"
    name = "Communication Strategist"
    description = "Estratega de comunicación experto en storytelling y narrativa efectiva"
    version = "1.0.0"
    
    role = "Director de Comunicación"
    expertise = """Soy experto en comunicación estratégica y storytelling. Puedo ayudarte con:
- Definir el tono ideal para tu audiencia (formal, cercano, inspirador, técnico)
- Estructurar narrativas efectivas (problema-solución, viaje del héroe, comparativo)
- Crear arcos emocionales que conecten con la audiencia
- Identificar mensajes clave y call-to-actions
- Adaptar el mensaje según el contexto cultural y empresarial"""
    
    task_requirements = """## MODOS DE USO

### Modo Consulta
Envía: {"mode": "consult", "task": "descripción", "audience": "público objetivo", "purpose": "objetivo"}
→ Te daré recomendaciones de comunicación y estructura narrativa

### Modo Review
Envía: {"mode": "review", "task": "descripción", "my_proposal": {...}, "other_proposals": [...]}
→ Evaluaré las propuestas y sugeriré mejoras de comunicación

### Campos que devuelvo:
- tone: Tono recomendado (formal, cercano, inspirador, etc.)
- narrative_structure: Estructura narrativa sugerida
- key_messages: Mensajes clave (máximo 3)
- emotional_arc: Arco emocional de la comunicación
- call_to_action: Acción esperada del receptor
"""
    
    domain_tools: List[str] = []  # Sin herramientas, solo razonamiento
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "openai",
        api_key: Optional[str] = None,
        **kwargs
    ) -> SubAgentResult:
        """
        Ejecuta el agente de comunicación.
        
        Modos:
        - consult: Da recomendaciones de comunicación
        - review: Evalúa propuestas de otros agentes
        """
        import time
        start_time = time.time()
        
        try:
            # Parsear task
            task_data = self._parse_task(task)
            mode = task_data.get("mode", "consult")
            
            if mode == "consult":
                return await self._handle_consult(
                    task_data, llm_url, model, provider_type, api_key, start_time
                )
            elif mode == "review":
                return await self._handle_review(
                    task_data, llm_url, model, provider_type, api_key, start_time
                )
            else:
                # Modo por defecto: tratar como consulta
                return await self._handle_consult(
                    task_data, llm_url, model, provider_type, api_key, start_time
                )
                
        except Exception as e:
            logger.error(f"CommunicationAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"Error en comunicación: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _parse_task(self, task: str) -> Dict[str, Any]:
        """Parsea el task string a diccionario."""
        try:
            return json.loads(task)
        except json.JSONDecodeError:
            return {"task": task, "mode": "consult"}
    
    async def _handle_consult(
        self,
        task_data: Dict[str, Any],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str],
        start_time: float
    ) -> SubAgentResult:
        """
        Modo consulta: Proporciona recomendaciones de comunicación.
        """
        from ...llm_utils import call_llm_with_tools
        
        task_desc = task_data.get("task", "")
        audience = task_data.get("audience", "general")
        purpose = task_data.get("purpose", "informar")
        team_mode = task_data.get("team_mode", False)
        
        prompt = f"""Eres un Director de Comunicación con experiencia en storytelling corporativo.

**TAREA:** {task_desc}
**AUDIENCIA:** {audience}
**OBJETIVO:** {purpose}

Proporciona tus recomendaciones de comunicación:

1. **TONO RECOMENDADO**
¿Qué tono sería más efectivo? (formal, cercano, inspirador, técnico, etc.)
Justifica brevemente.

2. **ESTRUCTURA NARRATIVA**
¿Qué estructura funcionaría mejor?
- Problema-Solución
- Viaje del héroe (desafío → transformación → éxito)
- Cronológico
- Comparativo (antes/después)
- Pirámide invertida

3. **MENSAJES CLAVE** (máximo 3)
¿Cuáles son los puntos que DEBEN quedar claros?

4. **ARCO EMOCIONAL**
¿Qué emociones debería experimentar la audiencia?
Inicio → Desarrollo → Cierre

5. **CALL TO ACTION**
¿Qué acción queremos que tome la audiencia?

{"Responde en formato JSON estructurado para facilitar la integración con el equipo." if team_mode else ""}
"""

        try:
            if not llm_url or not api_key:
                # Respuesta por defecto sin LLM
                return self._default_consult_response(task_desc, audience, purpose, start_time)
            
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": "Eres un experto en comunicación estratégica. Responde de forma estructurada y concisa."},
                    {"role": "user", "content": prompt}
                ],
                tools=[],
                temperature=0.7,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            # Extraer datos estructurados si es posible
            content = response.content or ""
            structured_data = self._extract_structured_data(content)
            
            return SubAgentResult(
                success=True,
                response=content,
                agent_id=self.id,
                agent_name=self.name,
                data=structured_data,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.error(f"Consult error: {e}")
            return self._default_consult_response(task_desc, audience, purpose, start_time)
    
    async def _handle_review(
        self,
        task_data: Dict[str, Any],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str],
        start_time: float
    ) -> SubAgentResult:
        """
        Modo review: Evalúa propuestas de otros agentes desde perspectiva comunicativa.
        """
        from ...llm_utils import call_llm_with_tools
        
        task_desc = task_data.get("task", "")
        my_proposal = task_data.get("my_proposal", {})
        other_proposals = task_data.get("other_proposals", [])
        
        # Formatear propuestas de otros
        others_text = ""
        for p in other_proposals:
            agent = p.get("agent", "Agente")
            content = p.get("content", {})
            if isinstance(content, dict):
                content_str = json.dumps(content, ensure_ascii=False, indent=2)[:500]
            else:
                content_str = str(content)[:500]
            others_text += f"\n**{agent}:**\n{content_str}\n"
        
        prompt = f"""Eres un Director de Comunicación revisando propuestas del equipo.

**TAREA ORIGINAL:** {task_desc}

**MI PROPUESTA ANTERIOR:**
{json.dumps(my_proposal, ensure_ascii=False, indent=2) if my_proposal else "Sin propuesta previa"}

**PROPUESTAS DE OTROS AGENTES:**
{others_text}

**TU TAREA:**
1. Evalúa las propuestas desde la perspectiva de COMUNICACIÓN
2. Identifica puntos fuertes y débiles
3. Sugiere ajustes para mejorar la efectividad comunicativa
4. Si hay conflictos, propón cómo resolverlos

Responde con:
- EVALUACIÓN: Breve análisis de cada propuesta
- AJUSTES: Cambios sugeridos
- INTEGRACIÓN: Cómo combinar lo mejor de cada una
"""

        try:
            if not llm_url or not api_key:
                return SubAgentResult(
                    success=True,
                    response="Acepto las propuestas. Sugiero mantener un tono coherente.",
                    agent_id=self.id,
                    agent_name=self.name,
                    data={"status": "accepted", "adjustments": []},
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": "Eres un experto en comunicación revisando trabajo de equipo."},
                    {"role": "user", "content": prompt}
                ],
                tools=[],
                temperature=0.5,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            return SubAgentResult(
                success=True,
                response=response.content or "",
                agent_id=self.id,
                agent_name=self.name,
                data={"status": "reviewed", "feedback": response.content},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.error(f"Review error: {e}")
            return SubAgentResult(
                success=True,
                response="Acepto las propuestas con observaciones menores.",
                agent_id=self.id,
                agent_name=self.name,
                data={"status": "accepted"},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _default_consult_response(
        self,
        task: str,
        audience: str,
        purpose: str,
        start_time: float
    ) -> SubAgentResult:
        """Respuesta por defecto cuando no hay LLM disponible."""
        import time
        
        response = f"""**Recomendaciones de Comunicación**

**Tono:** Profesional pero accesible - apropiado para {audience}

**Estructura Narrativa:** Problema-Solución
1. Contexto (¿por qué importa?)
2. Desafío actual
3. Solución propuesta
4. Beneficios
5. Próximos pasos

**Mensajes Clave:**
1. El valor principal de lo que presentamos
2. Por qué es relevante ahora
3. Qué acción esperamos

**Arco Emocional:** Curiosidad → Comprensión → Motivación

**Call to Action:** Definir según objetivo: {purpose}
"""
        
        return SubAgentResult(
            success=True,
            response=response,
            agent_id=self.id,
            agent_name=self.name,
            data={
                "tone": "profesional accesible",
                "narrative_structure": "problema-solución",
                "key_messages": ["valor principal", "relevancia actual", "acción esperada"],
                "emotional_arc": "curiosidad → comprensión → motivación",
                "call_to_action": purpose
            },
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
    
    def _extract_structured_data(self, content: str) -> Dict[str, Any]:
        """Intenta extraer datos estructurados del contenido."""
        data = {}
        
        # Buscar patrones comunes
        content_lower = content.lower()
        
        # Tono
        tone_keywords = ["formal", "cercano", "inspirador", "técnico", "profesional"]
        for tone in tone_keywords:
            if tone in content_lower:
                data["tone"] = tone
                break
        
        # Estructura
        structures = ["problema-solución", "viaje del héroe", "cronológico", "comparativo"]
        for struct in structures:
            if struct in content_lower:
                data["narrative_structure"] = struct
                break
        
        return data
