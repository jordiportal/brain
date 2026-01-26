"""
Cadenas predefinidas
"""

from .conversational import register_conversational_chain
from .rag_chain import register_rag_chain
from .tool_agent import register_tool_agent
from .sap_agent import register_sap_agent
from .orchestrator_agent import register_orchestrator_agent
from .browser_agent import register_browser_agent
from .openai_web_search_agent import register_openai_web_search_agent
from .code_execution_agent import register_code_execution_agent
from .persistent_admin_agent import register_persistent_admin_agent
from .admin_orchestrator_agent import register_admin_orchestrator_agent
from .unified_agent import register_unified_agent

def register_all_chains():
    """Registrar todas las cadenas predefinidas"""
    register_conversational_chain()
    register_rag_chain()
    register_tool_agent()
    register_sap_agent()
    register_browser_agent()
    register_openai_web_search_agent()
    register_code_execution_agent()
    register_persistent_admin_agent()  # ✅ Agente ejecutor administrativo
    register_admin_orchestrator_agent()  # ✅ Coordinador administrativo
    register_unified_agent()  # ✅ Nuevo sistema neuronal
    # El orchestrator general debe ir al final para poder descubrir los demás agentes
    register_orchestrator_agent()