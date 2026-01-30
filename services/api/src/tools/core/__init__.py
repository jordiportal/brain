"""
Brain 2.0 Core Tools - 17 herramientas nativas universales

Filesystem (5): read_file, write_file, edit_file, list_directory, search_files
Execution (3): shell, python, javascript  
Web (2): web_search, web_fetch
Reasoning (4): think, reflect, plan, finish
Utils (1): calculate
Delegation (1): delegate (para subagentes especializados)
Slides (1): generate_slides (presentaciones con streaming)
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
    get_available_subagents_description,
    DELEGATE_TOOL
)

from .slides import (
    generate_slides,
    GENERATE_SLIDES_TOOL
)

# Delegation tools dict
DELEGATION_TOOLS = {
    "delegate": DELEGATE_TOOL
}

# Slides tools dict
SLIDES_TOOLS = {
    "generate_slides": GENERATE_SLIDES_TOOL
}

# Todas las definiciones de core tools
CORE_TOOLS = {
    **FILESYSTEM_TOOLS,
    **EXECUTION_TOOLS,
    **WEB_TOOLS,
    **REASONING_TOOLS,
    **UTILS_TOOLS,
    **DELEGATION_TOOLS,
    **SLIDES_TOOLS
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
