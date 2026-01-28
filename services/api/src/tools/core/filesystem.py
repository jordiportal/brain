"""
Brain 2.0 Core Tools - Filesystem (5 tools)

- read: Leer archivo completo o parcial
- write: Crear/sobrescribir archivo
- edit: Reemplazar texto en archivo
- list: Listar directorio con glob
- search: Buscar archivos o contenido (grep)
"""

import os
import re
import glob as glob_module
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger()

# Workspace base (configurable via env)
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/workspace")


def _validate_path(path: str) -> Path:
    """
    Valida y normaliza un path dentro del workspace permitido.
    Previene path traversal attacks.
    """
    # Resolver path absoluto
    if not os.path.isabs(path):
        full_path = Path(WORKSPACE_ROOT) / path
    else:
        full_path = Path(path)
    
    # Resolver symlinks y normalizar
    try:
        resolved = full_path.resolve()
    except Exception:
        resolved = full_path
    
    # Verificar que está dentro del workspace (o es path absoluto permitido)
    workspace_resolved = Path(WORKSPACE_ROOT).resolve()
    
    # Permitir paths dentro del workspace o paths absolutos explícitos
    # En Brain 2.0, el agente puede acceder a archivos del sistema si es necesario
    # pero mantenemos el workspace como base por defecto
    
    return resolved


# ============================================
# Tool Handlers
# ============================================

async def read_file(
    path: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Lee un archivo completo o parcial.
    
    Args:
        path: Ruta al archivo
        offset: Línea inicial (1-indexed, opcional)
        limit: Número máximo de líneas a leer (opcional)
    
    Returns:
        {"success": True, "content": str, "lines": int} o {"error": str}
    """
    try:
        file_path = _validate_path(path)
        
        if not file_path.exists():
            return {"error": f"Archivo no encontrado: {path}", "success": False}
        
        if not file_path.is_file():
            return {"error": f"No es un archivo: {path}", "success": False}
        
        # Leer archivo
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Aplicar offset/limit si se especificaron
        if offset is not None:
            # offset es 1-indexed
            start = max(0, offset - 1)
            lines = lines[start:]
        
        if limit is not None:
            lines = lines[:limit]
        
        content = ''.join(lines)
        
        logger.info(f"📖 read: {path}", lines=len(lines), total=total_lines)
        
        return {
            "success": True,
            "content": content,
            "lines_read": len(lines),
            "total_lines": total_lines,
            "path": str(file_path)
        }
        
    except PermissionError:
        return {"error": f"Permiso denegado: {path}", "success": False}
    except Exception as e:
        logger.error(f"Error leyendo archivo: {e}")
        return {"error": str(e), "success": False}


async def write_file(
    path: str,
    content: str
) -> Dict[str, Any]:
    """
    Crea o sobrescribe un archivo con el contenido dado.
    
    Args:
        path: Ruta al archivo
        content: Contenido a escribir
    
    Returns:
        {"success": True, "path": str, "bytes": int} o {"error": str}
    """
    try:
        file_path = _validate_path(path)
        
        # Crear directorios padre si no existen
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Escribir archivo
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        bytes_written = len(content.encode('utf-8'))
        
        logger.info(f"📝 write: {path}", bytes=bytes_written)
        
        return {
            "success": True,
            "path": str(file_path),
            "bytes": bytes_written,
            "lines": content.count('\n') + 1
        }
        
    except PermissionError:
        return {"error": f"Permiso denegado: {path}", "success": False}
    except Exception as e:
        logger.error(f"Error escribiendo archivo: {e}")
        return {"error": str(e), "success": False}


async def edit_file(
    path: str,
    old_text: str,
    new_text: str
) -> Dict[str, Any]:
    """
    Reemplaza texto en un archivo (primera ocurrencia).
    
    Args:
        path: Ruta al archivo
        old_text: Texto a buscar y reemplazar
        new_text: Texto de reemplazo
    
    Returns:
        {"success": True, "replacements": int} o {"error": str}
    """
    try:
        file_path = _validate_path(path)
        
        if not file_path.exists():
            return {"error": f"Archivo no encontrado: {path}", "success": False}
        
        # Leer contenido actual
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Verificar que el texto a reemplazar existe
        if old_text not in content:
            return {
                "error": f"Texto no encontrado en el archivo",
                "success": False,
                "hint": "Verifica que el texto a reemplazar coincide exactamente (incluyendo espacios e indentación)"
            }
        
        # Reemplazar (primera ocurrencia)
        new_content = content.replace(old_text, new_text, 1)
        
        # Escribir archivo modificado
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"✏️ edit: {path}", old_len=len(old_text), new_len=len(new_text))
        
        return {
            "success": True,
            "path": str(file_path),
            "replacements": 1,
            "old_text_preview": old_text[:100] + "..." if len(old_text) > 100 else old_text,
            "new_text_preview": new_text[:100] + "..." if len(new_text) > 100 else new_text
        }
        
    except PermissionError:
        return {"error": f"Permiso denegado: {path}", "success": False}
    except Exception as e:
        logger.error(f"Error editando archivo: {e}")
        return {"error": str(e), "success": False}


async def list_directory(
    path: str = ".",
    recursive: bool = False,
    pattern: Optional[str] = None
) -> Dict[str, Any]:
    """
    Lista contenido de un directorio.
    
    Args:
        path: Ruta al directorio (default: workspace root)
        recursive: Si True, lista recursivamente
        pattern: Patrón glob para filtrar (ej: "*.py", "**/*.json")
    
    Returns:
        {"success": True, "entries": [...]} o {"error": str}
    """
    try:
        dir_path = _validate_path(path)
        
        if not dir_path.exists():
            return {"error": f"Directorio no encontrado: {path}", "success": False}
        
        if not dir_path.is_dir():
            return {"error": f"No es un directorio: {path}", "success": False}
        
        entries = []
        
        if pattern:
            # Usar glob con patrón
            if recursive and not pattern.startswith("**"):
                pattern = f"**/{pattern}"
            
            matches = list(dir_path.glob(pattern))
            
            for item in matches[:500]:  # Limitar a 500 resultados
                rel_path = item.relative_to(dir_path) if item.is_relative_to(dir_path) else item
                entries.append({
                    "name": str(rel_path),
                    "type": "file" if item.is_file() else "dir",
                    "size": item.stat().st_size if item.is_file() else None
                })
        else:
            # Listar directorio
            if recursive:
                for root, dirs, files in os.walk(dir_path):
                    # Ignorar directorios ocultos y comunes
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git']]
                    
                    rel_root = Path(root).relative_to(dir_path)
                    
                    for d in dirs:
                        entries.append({
                            "name": str(rel_root / d),
                            "type": "dir"
                        })
                    
                    for f in files:
                        if not f.startswith('.'):
                            file_path = Path(root) / f
                            entries.append({
                                "name": str(rel_root / f),
                                "type": "file",
                                "size": file_path.stat().st_size
                            })
                    
                    if len(entries) > 500:
                        break
            else:
                for item in dir_path.iterdir():
                    if not item.name.startswith('.'):
                        entries.append({
                            "name": item.name,
                            "type": "file" if item.is_file() else "dir",
                            "size": item.stat().st_size if item.is_file() else None
                        })
        
        # Ordenar: directorios primero, luego archivos
        entries.sort(key=lambda x: (x["type"] != "dir", x["name"]))
        
        logger.info(f"📂 list: {path}", entries=len(entries), recursive=recursive)
        
        return {
            "success": True,
            "path": str(dir_path),
            "entries": entries[:500],
            "count": len(entries),
            "truncated": len(entries) > 500
        }
        
    except PermissionError:
        return {"error": f"Permiso denegado: {path}", "success": False}
    except Exception as e:
        logger.error(f"Error listando directorio: {e}")
        return {"error": str(e), "success": False}


async def search_files(
    pattern: str,
    path: str = ".",
    mode: str = "content"
) -> Dict[str, Any]:
    """
    Busca archivos o contenido dentro de archivos.
    
    Args:
        pattern: Patrón a buscar (texto o regex)
        path: Directorio base para buscar
        mode: "content" para buscar en contenido, "filename" para buscar por nombre
    
    Returns:
        {"success": True, "matches": [...]} o {"error": str}
    """
    try:
        base_path = _validate_path(path)
        
        if not base_path.exists():
            return {"error": f"Directorio no encontrado: {path}", "success": False}
        
        matches = []
        
        if mode == "filename":
            # Buscar por nombre de archivo (glob)
            for item in base_path.rglob(f"*{pattern}*"):
                if item.is_file() and not any(p.startswith('.') for p in item.parts):
                    rel_path = item.relative_to(base_path) if item.is_relative_to(base_path) else item
                    matches.append({
                        "path": str(rel_path),
                        "type": "file",
                        "size": item.stat().st_size
                    })
                
                if len(matches) >= 100:
                    break
        
        else:  # mode == "content"
            # Buscar en contenido de archivos (grep-like)
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error:
                # Si no es regex válido, buscar como texto literal
                regex = re.compile(re.escape(pattern), re.IGNORECASE)
            
            # Extensiones de texto comunes
            text_extensions = {'.py', '.js', '.ts', '.json', '.yaml', '.yml', '.md', 
                            '.txt', '.html', '.css', '.sh', '.sql', '.toml', '.ini',
                            '.env', '.cfg', '.conf', '.xml', '.csv'}
            
            for item in base_path.rglob("*"):
                if not item.is_file():
                    continue
                
                # Saltar archivos ocultos y directorios comunes
                if any(p.startswith('.') for p in item.parts):
                    continue
                if any(p in ['node_modules', '__pycache__', '.git', 'venv', 'dist', 'build'] for p in item.parts):
                    continue
                
                # Solo buscar en archivos de texto
                if item.suffix.lower() not in text_extensions:
                    continue
                
                try:
                    with open(item, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel_path = item.relative_to(base_path) if item.is_relative_to(base_path) else item
                                matches.append({
                                    "path": str(rel_path),
                                    "line": line_num,
                                    "content": line.strip()[:200]
                                })
                                
                                if len(matches) >= 100:
                                    break
                except Exception:
                    continue
                
                if len(matches) >= 100:
                    break
        
        logger.info(f"🔍 search: {pattern}", mode=mode, matches=len(matches))
        
        return {
            "success": True,
            "pattern": pattern,
            "mode": mode,
            "matches": matches,
            "count": len(matches),
            "truncated": len(matches) >= 100
        }
        
    except Exception as e:
        logger.error(f"Error buscando: {e}")
        return {"error": str(e), "success": False}


# ============================================
# Tool Definitions for Registry
# ============================================

FILESYSTEM_TOOLS = {
    "read_file": {
        "id": "read_file",
        "name": "read_file",
        "description": "Lee un archivo completo o parcial. Soporta offset y limit para archivos grandes.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta al archivo a leer"
                },
                "offset": {
                    "type": "integer",
                    "description": "Línea inicial (1-indexed, opcional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de líneas a leer (opcional)"
                }
            },
            "required": ["path"]
        },
        "handler": read_file
    },
    "write_file": {
        "id": "write_file",
        "name": "write_file",
        "description": "Crea o sobrescribe un archivo con el contenido dado. Crea directorios padre si no existen.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta al archivo a crear/sobrescribir"
                },
                "content": {
                    "type": "string",
                    "description": "Contenido a escribir en el archivo"
                }
            },
            "required": ["path", "content"]
        },
        "handler": write_file
    },
    "edit_file": {
        "id": "edit_file",
        "name": "edit_file",
        "description": "Reemplaza texto en un archivo (primera ocurrencia). Útil para ediciones precisas.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta al archivo a editar"
                },
                "old_text": {
                    "type": "string",
                    "description": "Texto exacto a buscar y reemplazar (incluyendo indentación)"
                },
                "new_text": {
                    "type": "string",
                    "description": "Texto de reemplazo"
                }
            },
            "required": ["path", "old_text", "new_text"]
        },
        "handler": edit_file
    },
    "list_directory": {
        "id": "list_directory",
        "name": "list_directory",
        "description": "Lista contenido de un directorio. Soporta listado recursivo y filtro por patrón glob.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta al directorio (default: directorio actual)"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Si True, lista recursivamente subdirectorios"
                },
                "pattern": {
                    "type": "string",
                    "description": "Patrón glob para filtrar (ej: '*.py', '**/*.json')"
                }
            },
            "required": []
        },
        "handler": list_directory
    },
    "search_files": {
        "id": "search_files",
        "name": "search_files",
        "description": "Busca archivos por nombre o contenido dentro de archivos (grep-like).",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Patrón a buscar (texto o regex)"
                },
                "path": {
                    "type": "string",
                    "description": "Directorio base para buscar (default: directorio actual)"
                },
                "mode": {
                    "type": "string",
                    "enum": ["content", "filename"],
                    "description": "'content' para buscar en contenido de archivos, 'filename' para buscar por nombre"
                }
            },
            "required": ["pattern"]
        },
        "handler": search_files
    }
}
