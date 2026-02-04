"""
Prompts como ficheros en las carpetas de los agentes.

Fuente única: ficheros system_prompt.txt en cada cadena.
La GUI lee y escribe estos ficheros vía la API.
"""

from pathlib import Path

# Ruta base: directorio de este archivo (engine/) -> chains/adaptive/prompts, chains/team/prompts
_ENGINE_DIR = Path(__file__).resolve().parent
_PROMPT_FILES = {
    "adaptive": _ENGINE_DIR / "chains" / "adaptive" / "prompts" / "system_prompt.txt",
    "team": _ENGINE_DIR / "chains" / "team" / "prompts" / "system_prompt.txt",
}


def get_prompt_file_path(chain_id: str) -> Path | None:
    """Ruta al fichero de prompt de la cadena, o None si no usa ficheros."""
    return _PROMPT_FILES.get(chain_id)


def read_prompt(chain_id: str) -> str:
    """Lee el system prompt desde el fichero. Devuelve '' si no existe o no hay fichero."""
    path = get_prompt_file_path(chain_id)
    if not path:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def write_prompt(chain_id: str, content: str) -> bool:
    """Escribe el system prompt en el fichero. Devuelve True si OK."""
    path = get_prompt_file_path(chain_id)
    if not path:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False
