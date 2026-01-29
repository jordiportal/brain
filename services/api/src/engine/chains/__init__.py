"""
Brain 2.0 Chains Module

Registra el Adaptive Agent principal y chains básicas para OpenAI-compat.
"""

# Brain 2.0 - Adaptive Agent
from .adaptive_agent import register_adaptive_agent

# Chains básicas para OpenAI-compatible endpoint
from .conversational import register_conversational_chain
from .rag_chain import register_rag_chain

# ============================================
# Brain 1.x Agents (disponibles pero opcionales)
# ============================================
# from .tool_agent import register_tool_agent
# from .sap_agent import register_sap_agent
# from .orchestrator_agent import register_orchestrator_agent
# from .browser_agent import register_browser_agent
# from .openai_web_search_agent import register_openai_web_search_agent
# from .code_execution_agent import register_code_execution_agent
# from .persistent_admin_agent import register_persistent_admin_agent
# from .admin_orchestrator_agent import register_admin_orchestrator_agent
# from .unified_agent import register_unified_agent


def register_all_chains():
    """
    Registrar las cadenas de Brain 2.0
    
    - brain-adaptive: Agente adaptativo con tools
    - brain-chat: Chat conversacional simple
    - brain-rag: Chat con búsqueda de documentos
    """
    
    # ============================================
    # Brain 2.0 - Adaptive Agent (principal)
    # ============================================
    register_adaptive_agent()
    
    # ============================================
    # Chains para OpenAI-compatible endpoint
    # ============================================
    register_conversational_chain()
    register_rag_chain()
