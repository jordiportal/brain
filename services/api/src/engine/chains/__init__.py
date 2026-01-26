"""
Brain 2.0 Chains Module

Solo registra el Adaptive Agent con las 15 core tools.
Los agentes anteriores están desactivados pero el código se mantiene.
"""

# Brain 2.0 - Solo el Adaptive Agent
from .adaptive_agent import register_adaptive_agent

# ============================================
# Brain 1.x Agents (DESACTIVADOS)
# El código se mantiene para referencia, pero no se registran.
# ============================================
# from .conversational import register_conversational_chain
# from .rag_chain import register_rag_chain
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
    
    Brain 2.0 usa un único agente adaptativo con 15 core tools.
    Los agentes especializados anteriores están desactivados.
    """
    
    # ============================================
    # Brain 2.0 - Adaptive Agent
    # ============================================
    register_adaptive_agent()
    
    # ============================================
    # Brain 1.x Agents (DESACTIVADOS)
    # Descomentar para habilitar agentes legacy
    # ============================================
    # register_conversational_chain()
    # register_rag_chain()
    # register_tool_agent()
    # register_sap_agent()
    # register_browser_agent()
    # register_openai_web_search_agent()
    # register_code_execution_agent()
    # register_persistent_admin_agent()
    # register_admin_orchestrator_agent()
    # register_unified_agent()
    # register_orchestrator_agent()  # Orchestrator va al final
