"""
Validadores para el Adaptive Agent.

Contiene funciones de validación para:
- Nombres de tools (filtrar artifacts de modelos)
- Detección de comandos de continuación
- Detección de loops
"""

from typing import Set


# ============================================
# Validación de Tool Names
# ============================================

# Lista de tools válidas del sistema
VALID_TOOL_NAMES: Set[str] = {
    # Filesystem
    "read_file", "write_file", "edit_file", "list_directory", "search_files",
    # Execution
    "shell", "python", "javascript",
    # Web
    "web_search", "web_fetch",
    # Reasoning
    "think", "reflect", "plan", "finish",
    # Utils
    "calculate",
    # Delegation & Special
    "delegate",
    "generate_slides",
}

# Patrones que indican artifacts de modelos (no son tools reales)
INVALID_TOOL_PATTERNS = [
    '<|', '|>', 'channel', 'functions<', 'assistant<'
]


def is_valid_tool_name(name: str) -> bool:
    """
    Valida que el nombre de la tool es válido.
    
    Filtra artifacts de modelos como 'assistant<|channel|>commentary'
    que algunos LLMs generan erróneamente.
    
    Args:
        name: Nombre de la tool a validar
        
    Returns:
        True si es una tool válida
    """
    if not name:
        return False
    
    # Verificar patrones inválidos
    name_lower = name.lower()
    for pattern in INVALID_TOOL_PATTERNS:
        if pattern in name_lower:
            return False
    
    # Verificar que está en la lista de tools válidas
    return name_lower in VALID_TOOL_NAMES


def add_valid_tool(name: str) -> None:
    """
    Añade una tool a la lista de válidas.
    Útil para extensibilidad dinámica.
    """
    VALID_TOOL_NAMES.add(name.lower())


# ============================================
# Detección de Comandos de Continuación
# ============================================

# Comandos que indican que el usuario quiere continuar
CONTINUE_COMMANDS: Set[str] = {
    # Español
    "continúa", "continua", "sigue", "adelante", "prosigue",
    "sí", "si", "vale", "ok", "sigue adelante",
    "continúa por favor", "sí continúa",
    # Inglés
    "continue", "yes", "go on", "proceed", "keep going",
}

# Keywords de continuación para búsqueda parcial
CONTINUE_KEYWORDS = ["continúa", "continua", "sigue", "continue", "proceed"]


def is_continue_command(query: str) -> bool:
    """
    Detecta si la query es un comando para continuar una tarea pausada.
    
    Args:
        query: Texto de la query del usuario
        
    Returns:
        True si parece un comando de continuación
    """
    query_lower = query.lower().strip()
    
    # Verificar comandos exactos
    if query_lower in CONTINUE_COMMANDS:
        return True
    
    # Verificar keywords en queries cortas
    if len(query_lower) < 50:
        for keyword in CONTINUE_KEYWORDS:
            if keyword in query_lower:
                return True
    
    return False


# ============================================
# Detección de Loops
# ============================================

class LoopDetector:
    """
    Detecta cuando el agente está en un loop llamando la misma tool.
    """
    
    def __init__(self, max_consecutive: int = 3):
        """
        Args:
            max_consecutive: Número máximo de llamadas consecutivas permitidas
        """
        self.max_consecutive = max_consecutive
        self.last_tool_name: str | None = None
        self.consecutive_count: int = 0
    
    def track(self, tool_name: str) -> bool:
        """
        Registra una llamada a tool y detecta si hay loop.
        
        Args:
            tool_name: Nombre de la tool llamada
            
        Returns:
            True si se detectó un loop
        """
        if tool_name == self.last_tool_name:
            self.consecutive_count += 1
        else:
            self.consecutive_count = 1
            self.last_tool_name = tool_name
        
        # finish no cuenta como loop
        if tool_name == "finish":
            return False
        
        return self.consecutive_count >= self.max_consecutive
    
    def get_warning_message(self) -> str:
        """
        Genera mensaje de advertencia para inyectar al LLM.
        """
        return f"""⚠️ WARNING: You have called `{self.last_tool_name}` {self.consecutive_count} times consecutively.

STOP and call `finish` NOW with your current results. Do NOT call {self.last_tool_name} again.

If the task is complete, use: finish(final_answer="your answer here")
If you need something else, use a DIFFERENT tool."""
    
    def reset(self) -> None:
        """Reinicia el detector."""
        self.last_tool_name = None
        self.consecutive_count = 0


# ============================================
# Validación de Argumentos de Tools
# ============================================

def validate_json_args(args_str: str) -> dict:
    """
    Parsea y valida argumentos JSON de una tool call.
    
    Args:
        args_str: String JSON de argumentos
        
    Returns:
        Dict de argumentos parseados (vacío si falla)
    """
    import json
    
    if not args_str:
        return {}
    
    if isinstance(args_str, dict):
        return args_str
    
    try:
        return json.loads(args_str)
    except json.JSONDecodeError:
        return {}
