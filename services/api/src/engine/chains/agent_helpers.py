"""
Agent Helpers - Funciones compartidas por todos los agentes
Evita duplicación de código y proporciona utilidades comunes.
"""

import json
import re
from typing import Optional, Dict, Any, List


def extract_json(text: str) -> Optional[Dict]:
    """
    Extraer JSON de un texto (implementación única para todos los agentes).
    
    Busca patrones comunes de JSON en markdown, bloques de código, etc.
    """
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # JSON en bloque markdown
        r'```\s*([\s\S]*?)\s*```',       # Bloque de código genérico
        r'\{[\s\S]*?\}'                   # JSON directo
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match.strip() if isinstance(match, str) else match)
                if isinstance(data, dict):  # Solo devolver objetos
                    return data
            except json.JSONDecodeError:
                continue
    
    # Último intento: parsear texto completo
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            return data
    except:
        pass
    
    return None


def build_llm_messages(
    system_prompt: Optional[str] = None,
    template: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
    memory: Optional[List[Dict]] = None,
    max_memory: int = 10
) -> List[Dict]:
    """
    Construir lista de mensajes para LLM con:
    - System prompt
    - Memoria de conversación
    - Template con variables {{var}}
    
    Args:
        system_prompt: Prompt del sistema
        template: Template con variables {{variable_name}}
        variables: Diccionario de variables para reemplazar
        memory: Lista de mensajes previos {"role": "...", "content": "..."}
        max_memory: Máximo de mensajes de memoria a incluir
        
    Returns:
        Lista de mensajes en formato OpenAI
    """
    messages = []
    
    # 1. System prompt (siempre primero)
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # 2. Memoria (últimos N mensajes)
    if memory:
        messages.extend(memory[-max_memory:])
    
    # 3. Template con variables reemplazadas
    if template:
        content = template
        if variables:
            for key, value in variables.items():
                # Reemplazar {{key}} con el valor
                placeholder = f"{{{{{key}}}}}"
                content = content.replace(placeholder, str(value))
        messages.append({"role": "user", "content": content})
    
    return messages


def format_json_preview(
    data: Any, 
    max_chars: int = 4000,
    indent: int = 2
) -> tuple[str, bool]:
    """
    Formatear datos como JSON con límite de caracteres.
    
    Args:
        data: Datos a formatear
        max_chars: Límite de caracteres
        indent: Indentación del JSON
        
    Returns:
        (json_string, was_truncated)
    """
    json_str = json.dumps(data, indent=indent, ensure_ascii=False, default=str)
    truncated = len(json_str) > max_chars
    preview = json_str[:max_chars]
    
    return preview, truncated


def format_memory(
    memory: Optional[List[Dict]], 
    max_messages: int = 10,
    format_style: str = "text"
) -> str:
    """
    Formatear memoria para incluir en prompts.
    
    Args:
        memory: Lista de mensajes
        max_messages: Máximo de mensajes a formatear
        format_style: "text" | "json"
        
    Returns:
        String formateado de la memoria
    """
    if not memory:
        return "No hay conversación previa."
    
    recent_memory = memory[-max_messages:]
    
    if format_style == "json":
        return json.dumps(recent_memory, indent=2, ensure_ascii=False)
    
    # Formato texto
    formatted = []
    for msg in recent_memory:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        formatted.append(f"{role}: {content}")
    
    return "\n".join(formatted)


def clean_code_block(text: str, language: Optional[str] = None) -> str:
    """
    Extraer código limpio de un texto que puede contener bloques markdown.
    
    Args:
        text: Texto con posible código
        language: Lenguaje esperado (python, javascript, etc.)
        
    Returns:
        Código limpio sin marcas markdown
    """
    # Buscar bloques de código con lenguaje específico
    if language:
        pattern = f'```{language}\\s*([\\s\\S]*?)```'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Buscar cualquier bloque de código
    pattern = r'```(?:\w+)?\s*([\s\S]*?)```'
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    
    # Si no hay bloques, devolver texto limpio
    return text.strip()


def truncate_with_marker(
    text: str, 
    max_length: int, 
    marker: str = "\n... [TRUNCATED] ..."
) -> tuple[str, bool]:
    """
    Truncar texto agregando un marcador visible.
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima
        marker: Marcador de truncado
        
    Returns:
        (truncated_text, was_truncated)
    """
    if len(text) <= max_length:
        return text, False
    
    truncated = text[:max_length - len(marker)] + marker
    return truncated, True


def validate_template_variables(
    template: str, 
    provided_vars: Dict[str, Any]
) -> tuple[bool, List[str]]:
    """
    Validar que un template tiene todas las variables necesarias.
    
    Args:
        template: Template con {{variables}}
        provided_vars: Variables proporcionadas
        
    Returns:
        (is_valid, missing_variables)
    """
    # Encontrar todas las variables en el template
    pattern = r'\{\{(\w+)\}\}'
    required_vars = set(re.findall(pattern, template))
    provided_vars_set = set(provided_vars.keys())
    
    missing = list(required_vars - provided_vars_set)
    is_valid = len(missing) == 0
    
    return is_valid, missing


def get_template_variables(template: str) -> List[str]:
    """
    Extraer lista de variables de un template.
    
    Args:
        template: Template con {{variables}}
        
    Returns:
        Lista de nombres de variables
    """
    pattern = r'\{\{(\w+)\}\}'
    return list(set(re.findall(pattern, template)))
