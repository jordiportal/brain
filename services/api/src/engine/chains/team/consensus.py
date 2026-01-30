"""
Motor de Consenso para equipos de agentes.

Coordina el debate entre múltiples agentes hasta alcanzar consenso.
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

import structlog

logger = structlog.get_logger()


class ProposalStatus(Enum):
    """Estado de una propuesta en el debate."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    ADJUSTED = "adjusted"
    OBJECTED = "objected"


@dataclass
class Proposal:
    """Propuesta de un agente durante el consenso."""
    agent_id: str
    agent_name: str
    content: Dict[str, Any]
    confidence: float = 0.8
    status: ProposalStatus = ProposalStatus.PENDING
    feedback: Optional[str] = None
    adjustments: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "content": self.content,
            "confidence": self.confidence,
            "status": self.status.value,
            "feedback": self.feedback,
            "adjustments": self.adjustments
        }


@dataclass
class ConsensusResult:
    """Resultado del proceso de consenso."""
    success: bool
    proposals: List[Proposal]
    merged_brief: Dict[str, Any]
    rounds_taken: int
    conflicts_resolved: List[str] = field(default_factory=list)
    lead_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "proposals": [p.to_dict() for p in self.proposals],
            "merged_brief": self.merged_brief,
            "rounds_taken": self.rounds_taken,
            "conflicts_resolved": self.conflicts_resolved,
            "lead_agent": self.lead_agent
        }


class ConsensusEngine:
    """
    Motor de consenso que coordina el debate entre agentes.
    
    Flujo:
    1. Consulta inicial paralela a todos los agentes
    2. Rondas de revisión cruzada (cada agente revisa propuestas de otros)
    3. Resolución de conflictos si hay desacuerdos
    4. Merge de propuestas en un brief unificado
    """
    
    def __init__(
        self,
        max_rounds: int = 3,
        consensus_threshold: float = 0.7,
        llm_config: Optional[Dict[str, Any]] = None
    ):
        self.max_rounds = max_rounds
        self.consensus_threshold = consensus_threshold
        self.llm_config = llm_config or {}
        
    async def run(
        self,
        agents: List[Any],  # List[BaseSubAgent]
        task: str,
        context: Optional[str] = None,
        on_event: Optional[callable] = None
    ) -> ConsensusResult:
        """
        Ejecuta el proceso completo de consenso.
        
        Args:
            agents: Lista de agentes que participan
            task: Descripción de la tarea
            context: Contexto adicional
            on_event: Callback para emitir eventos de progreso
        
        Returns:
            ConsensusResult con el brief consensuado
        """
        logger.info(f"Starting consensus with {len(agents)} agents", 
                   agents=[a.id for a in agents])
        
        # Fase 1: Consulta inicial paralela
        if on_event:
            await on_event({
                "type": "consensus",
                "round": 0,
                "phase": "consulting",
                "agents": [a.id for a in agents]
            })
        
        proposals = await self._consult_all(agents, task, context)
        
        # Verificar si ya hay consenso (propuestas compatibles)
        if await self._check_consensus(proposals):
            logger.info("Immediate consensus reached")
            merged = await self._merge_proposals(proposals, task)
            return ConsensusResult(
                success=True,
                proposals=proposals,
                merged_brief=merged,
                rounds_taken=0,
                lead_agent=self._determine_lead_agent(agents, task)
            )
        
        # Fase 2: Rondas de revisión
        conflicts_resolved = []
        for round_num in range(1, self.max_rounds + 1):
            if on_event:
                await on_event({
                    "type": "consensus",
                    "round": round_num,
                    "phase": "reviewing"
                })
            
            proposals = await self._review_round(agents, proposals, task)
            
            if await self._check_consensus(proposals):
                logger.info(f"Consensus reached at round {round_num}")
                break
            
            # Intentar resolver conflictos
            conflicts = self._identify_conflicts(proposals)
            if conflicts:
                if on_event:
                    await on_event({
                        "type": "consensus",
                        "round": round_num,
                        "phase": "resolving",
                        "conflicts": conflicts
                    })
                
                resolved = await self._resolve_conflicts(agents, proposals, conflicts, task)
                conflicts_resolved.extend(resolved)
        
        # Fase 3: Merge final
        if on_event:
            await on_event({
                "type": "consensus",
                "phase": "merging"
            })
        
        merged = await self._merge_proposals(proposals, task)
        lead_agent = self._determine_lead_agent(agents, task)
        
        if on_event:
            await on_event({
                "type": "consensus",
                "phase": "completed",
                "lead_agent": lead_agent
            })
        
        return ConsensusResult(
            success=True,
            proposals=proposals,
            merged_brief=merged,
            rounds_taken=round_num if 'round_num' in locals() else self.max_rounds,
            conflicts_resolved=conflicts_resolved,
            lead_agent=lead_agent
        )
    
    async def _consult_all(
        self,
        agents: List[Any],
        task: str,
        context: Optional[str]
    ) -> List[Proposal]:
        """Consulta inicial paralela a todos los agentes."""
        
        async def consult_agent(agent) -> Proposal:
            try:
                # Preparar task para modo consulta
                consult_task = json.dumps({
                    "mode": "consult",
                    "task": task,
                    "context": context or "",
                    "team_mode": True
                })
                
                result = await agent.execute(
                    task=consult_task,
                    context=context,
                    **self.llm_config
                )
                
                # Extraer contenido estructurado
                content = result.data if result.data else {"response": result.response}
                
                return Proposal(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=content,
                    confidence=0.8 if result.success else 0.3,
                    status=ProposalStatus.PENDING
                )
                
            except Exception as e:
                logger.error(f"Error consulting agent {agent.id}: {e}")
                return Proposal(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content={"error": str(e)},
                    confidence=0.0,
                    status=ProposalStatus.OBJECTED
                )
        
        # Ejecutar consultas en paralelo
        results = await asyncio.gather(
            *[consult_agent(agent) for agent in agents],
            return_exceptions=True
        )
        
        # Filtrar excepciones
        proposals = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                proposals.append(Proposal(
                    agent_id=agents[i].id,
                    agent_name=agents[i].name,
                    content={"error": str(result)},
                    confidence=0.0,
                    status=ProposalStatus.OBJECTED
                ))
            else:
                proposals.append(result)
        
        return proposals
    
    async def _review_round(
        self,
        agents: List[Any],
        proposals: List[Proposal],
        task: str
    ) -> List[Proposal]:
        """
        Ronda de revisión cruzada.
        Cada agente revisa las propuestas de los otros.
        """
        updated_proposals = []
        
        for agent, proposal in zip(agents, proposals):
            # Propuestas de otros agentes
            other_proposals = [p for p in proposals if p.agent_id != agent.id]
            
            try:
                review_task = json.dumps({
                    "mode": "review",
                    "task": task,
                    "my_proposal": proposal.content,
                    "other_proposals": [
                        {
                            "agent": p.agent_name,
                            "content": p.content
                        }
                        for p in other_proposals
                    ]
                })
                
                result = await agent.execute(
                    task=review_task,
                    context="Revisa las propuestas y sugiere ajustes si es necesario.",
                    **self.llm_config
                )
                
                # Actualizar propuesta con feedback
                new_proposal = Proposal(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=result.data if result.data else proposal.content,
                    confidence=proposal.confidence,
                    status=ProposalStatus.ADJUSTED if result.data else ProposalStatus.ACCEPTED,
                    feedback=result.response
                )
                updated_proposals.append(new_proposal)
                
            except Exception as e:
                logger.warning(f"Error in review for {agent.id}: {e}")
                proposal.status = ProposalStatus.ACCEPTED
                updated_proposals.append(proposal)
        
        return updated_proposals
    
    async def _check_consensus(self, proposals: List[Proposal]) -> bool:
        """
        Verifica si hay consenso entre las propuestas.
        Consenso = ninguna propuesta objetada + confianza promedio > threshold
        """
        if not proposals:
            return False
        
        # Si hay propuestas objetadas, no hay consenso
        if any(p.status == ProposalStatus.OBJECTED for p in proposals):
            return False
        
        # Verificar confianza promedio
        avg_confidence = sum(p.confidence for p in proposals) / len(proposals)
        return avg_confidence >= self.consensus_threshold
    
    def _identify_conflicts(self, proposals: List[Proposal]) -> List[str]:
        """Identifica conflictos entre propuestas."""
        conflicts = []
        
        # Buscar propuestas objetadas
        for p in proposals:
            if p.status == ProposalStatus.OBJECTED:
                conflicts.append(f"{p.agent_name}: {p.feedback or 'objeción sin detalle'}")
        
        # Buscar contradicciones (simplificado)
        # En una implementación más avanzada, usaríamos el LLM para detectar conflictos
        
        return conflicts
    
    async def _resolve_conflicts(
        self,
        agents: List[Any],
        proposals: List[Proposal],
        conflicts: List[str],
        task: str
    ) -> List[str]:
        """
        Intenta resolver conflictos entre propuestas.
        Retorna lista de conflictos resueltos.
        """
        resolved = []
        
        # Estrategia simple: el coordinador decide
        # En una implementación más avanzada, los agentes negociarían
        
        for conflict in conflicts:
            # Marcar como resuelto por el coordinador
            resolved.append(f"Resuelto: {conflict}")
        
        # Actualizar estado de propuestas objetadas
        for p in proposals:
            if p.status == ProposalStatus.OBJECTED:
                p.status = ProposalStatus.ADJUSTED
        
        return resolved
    
    async def _merge_proposals(
        self,
        proposals: List[Proposal],
        task: str
    ) -> Dict[str, Any]:
        """
        Combina las propuestas en un brief unificado.
        """
        merged = {
            "task": task,
            "contributions": {}
        }
        
        for proposal in proposals:
            if proposal.status != ProposalStatus.OBJECTED:
                merged["contributions"][proposal.agent_id] = {
                    "agent_name": proposal.agent_name,
                    "content": proposal.content,
                    "confidence": proposal.confidence
                }
        
        return merged
    
    def _determine_lead_agent(self, agents: List[Any], task: str) -> Optional[str]:
        """
        Determina qué agente debería liderar la ejecución final.
        Basado en el tipo de tarea y las capacidades de los agentes.
        """
        task_lower = task.lower()
        
        # Mapeo de palabras clave a agentes ejecutores
        execution_keywords = {
            "slides_agent": ["presentación", "slides", "diapositivas"],
            "media_agent": ["imagen", "foto", "ilustración", "genera una imagen"],
            "analyst_agent": ["analiza", "datos", "estadísticas", "gráfico"],
        }
        
        for agent_id, keywords in execution_keywords.items():
            if any(kw in task_lower for kw in keywords):
                # Verificar que el agente está en el equipo
                if any(a.id == agent_id for a in agents):
                    return agent_id
        
        # Por defecto, el primer agente con capacidad de ejecución
        for agent in agents:
            if hasattr(agent, 'domain_tools') and agent.domain_tools:
                return agent.id
        
        return agents[0].id if agents else None
