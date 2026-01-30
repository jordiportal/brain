"""
Brain 2.0 Core Tools - 16 herramientas nativas universales

Filesystem (5): read_file, write_file, edit_file, list_directory, search_files
Execution (3): shell, python, javascript  
Web (2): web_search, web_fetch
Reasoning (4): think, reflect, plan, finish
Utils (1): calculate
Delegation (1): delegate (para subagentes especializados)

NOTA: generate_image y generate_slides NO están en CORE_TOOLS.
Estas herramientas las usan los subagentes especializados (media_agent, slides_agent).
El agente principal usa `delegate` para acceder a estas funcionalidades.
"""

from .filesystem import (
    read_file,
    write_file,
    edit_file,
    list_directory,
    search_files,
    FILESYSTEM_TOOLS
)

from .execution import (
    shell_execute,
    python_execute,
    javascript_execute,
    EXECUTION_TOOLS
)

from .web import (
    web_search,
    web_fetch,
    WEB_TOOLS
)

from .reasoning import (
    think,
    reflect,
    plan,
    finish,
    REASONING_TOOLS
)

from .utils import (
    calculate,
    UTILS_TOOLS
)

from .delegation import (
    delegate,
    get_agent_info,
    get_available_subagents_description,
    DELEGATE_TOOL,
    GET_AGENT_INFO_TOOL
)

# Mantener imports para uso interno por subagentes
from .slides import (
    generate_slides,
    GENERATE_SLIDES_TOOL
)

# Delegation tools dict
DELEGATION_TOOLS = {
    "get_agent_info": GET_AGENT_INFO_TOOL,
    "delegate": DELEGATE_TOOL
}

# Slides tools dict (NO incluido en CORE_TOOLS, usado por slides_agent)
SLIDES_TOOLS = {
    "generate_slides": GENERATE_SLIDES_TOOL
}

# CORE_TOOLS: Solo herramientas del agente principal
# Las herramientas especializadas (imágenes, presentaciones) las usan los subagentes
CORE_TOOLS = {
    **FILESYSTEM_TOOLS,
    **EXECUTION_TOOLS,
    **WEB_TOOLS,
    **REASONING_TOOLS,
    **UTILS_TOOLS,
    **DELEGATION_TOOLS,
    # NO incluir SLIDES_TOOLS - el agente usa delegate → slides_agent
}

__all__ = [
    # Filesystem
    "read_file",
    "write_file", 
    "edit_file",
    "list_directory",
    "search_files",
    # Execution
    "shell_execute",
    "python_execute",
    "javascript_execute",
    # Web
    "web_search",
    "web_fetch",
    # Reasoning
    "think",
    "reflect",
    "plan",
    "finish",
    # Utils
    "calculate",
    # Delegation
    "delegate",
    "get_agent_info",
    "get_available_subagents_description",
    # Slides
    "generate_slides",
    # All tools
    "CORE_TOOLS",
    "FILESYSTEM_TOOLS",
    "EXECUTION_TOOLS",
    "WEB_TOOLS",
    "REASONING_TOOLS",
    "UTILS_TOOLS",
    "DELEGATION_TOOLS",
    "SLIDES_TOOLS"
]
