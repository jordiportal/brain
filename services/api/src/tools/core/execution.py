"""
Brain 2.0 Core Tools - Execution (3 tools)

- shell: Ejecutar comando shell en el host
- python: Ejecutar código Python en contenedor Docker
- javascript: Ejecutar código JavaScript en contenedor Docker
"""

import asyncio
import os
import subprocess
import time
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

# Importar configuración
try:
    from ..config import get_execution_config
except ImportError:
    get_execution_config = None


# ============================================
# Tool Handlers
# ============================================

async def shell_execute(
    command: str,
    workdir: Optional[str] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Ejecuta un comando shell en el sistema.
    
    Args:
        command: Comando a ejecutar
        workdir: Directorio de trabajo (opcional)
        timeout: Timeout en segundos (default: 30)
    
    Returns:
        {"success": True, "stdout": str, "stderr": str, "exit_code": int} o {"error": str}
    """
    try:
        logger.info(f"🖥️ shell: {command[:100]}", workdir=workdir, timeout=timeout)
        
        # Determinar directorio de trabajo
        cwd = workdir or os.getenv("WORKSPACE_ROOT", "/workspace")
        
        # Crear proceso
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        try:
            # Esperar con timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            success = process.returncode == 0
            
            logger.info(
                f"✅ shell completed",
                exit_code=process.returncode,
                stdout_len=len(stdout_str),
                stderr_len=len(stderr_str)
            )
            
            return {
                "success": success,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": process.returncode,
                "command": command
            }
            
        except asyncio.TimeoutError:
            # Matar proceso si hay timeout
            process.kill()
            await process.wait()
            
            logger.warning(f"⏱️ shell timeout después de {timeout}s")
            
            return {
                "success": False,
                "error": f"Timeout después de {timeout} segundos",
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
                "command": command
            }
            
    except Exception as e:
        logger.error(f"Error ejecutando shell: {e}")
        return {
            "success": False,
            "error": str(e),
            "command": command
        }


async def python_execute(
    code: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Ejecuta código Python en un contenedor Docker aislado.
    
    Args:
        code: Código Python a ejecutar
        timeout: Timeout en segundos (default: 30)
    
    Returns:
        {"success": True, "stdout": str, "stderr": str} o {"error": str}
    """
    # Obtener configuración
    config = get_execution_config() if get_execution_config else None
    image = config.python_image if config else "python:3.11-slim"
    memory_limit = config.memory_limit if config else "512m"
    cpu_limit = config.cpu_limit if config else "1.0"
    network_enabled = config.network_enabled if config else False
    
    if config and not config.python_enabled:
        return {
            "success": False,
            "error": "Python execution is disabled in configuration"
        }
    
    return await _execute_in_docker(
        code=code,
        language="python",
        image=image,
        command=["python", "-c"],
        timeout=timeout,
        memory_limit=memory_limit,
        cpu_limit=cpu_limit,
        network_enabled=network_enabled
    )


async def javascript_execute(
    code: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Ejecuta código JavaScript/Node.js en un contenedor Docker aislado.
    
    Args:
        code: Código JavaScript a ejecutar
        timeout: Timeout en segundos (default: 30)
    
    Returns:
        {"success": True, "stdout": str, "stderr": str} o {"error": str}
    """
    # Obtener configuración
    config = get_execution_config() if get_execution_config else None
    image = config.node_image if config else "node:20-slim"
    memory_limit = config.memory_limit if config else "512m"
    cpu_limit = config.cpu_limit if config else "1.0"
    network_enabled = config.network_enabled if config else False
    
    if config and not config.javascript_enabled:
        return {
            "success": False,
            "error": "JavaScript execution is disabled in configuration"
        }
    
    return await _execute_in_docker(
        code=code,
        language="javascript",
        image=image,
        command=["node", "-e"],
        timeout=timeout,
        memory_limit=memory_limit,
        cpu_limit=cpu_limit,
        network_enabled=network_enabled
    )


async def _execute_in_docker(
    code: str,
    language: str,
    image: str,
    command: list,
    timeout: int,
    memory_limit: str,
    cpu_limit: str,
    network_enabled: bool
) -> Dict[str, Any]:
    """
    Ejecuta código en un contenedor Docker.
    
    Args:
        code: Código a ejecutar
        language: Lenguaje (para logging)
        image: Imagen Docker a usar
        command: Comando base (ej: ["python", "-c"])
        timeout: Timeout en segundos
        memory_limit: Límite de memoria
        cpu_limit: Límite de CPU
        network_enabled: Si permite red
    
    Returns:
        Resultado de la ejecución
    """
    start_time = time.time()
    
    try:
        logger.info(
            f"🐳 {language}: ejecutando en Docker",
            image=image,
            timeout=timeout,
            code_len=len(code)
        )
        
        # Construir comando docker
        docker_cmd = [
            "docker", "run",
            "--rm",
            f"--memory={memory_limit}",
            f"--cpus={cpu_limit}"
        ]
        
        # Red deshabilitada por defecto para seguridad
        if not network_enabled:
            docker_cmd.append("--network=none")
        
        # Imagen y comando
        docker_cmd.append(image)
        docker_cmd.extend(command)
        docker_cmd.append(code)
        
        # Ejecutar con timeout
        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            success = process.returncode == 0
            
            logger.info(
                f"✅ {language} completed",
                success=success,
                exit_code=process.returncode,
                execution_time=f"{execution_time:.2f}s"
            )
            
            return {
                "success": success,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "exit_code": process.returncode,
                "execution_time": execution_time,
                "language": language,
                "error": None if success else f"Exit code: {process.returncode}"
            }
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            execution_time = time.time() - start_time
            
            logger.warning(f"⏱️ {language} timeout after {timeout}s")
            
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Timeout after {timeout} seconds",
                "exit_code": -1,
                "execution_time": execution_time,
                "language": language,
                "error": f"Timeout after {timeout} seconds"
            }
            
    except FileNotFoundError:
        return {
            "success": False,
            "error": "Docker not found. Please ensure Docker is installed and running.",
            "language": language
        }
    except Exception as e:
        logger.error(f"Error executing {language}: {e}")
        return {
            "success": False,
            "error": str(e),
            "language": language
        }


# ============================================
# Tool Definitions for Registry
# ============================================

EXECUTION_TOOLS = {
    "shell": {
        "id": "shell",
        "name": "shell",
        "description": "Ejecuta un comando shell en el sistema. Útil para comandos del sistema, git, npm, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Comando shell a ejecutar (ej: 'ls -la', 'git status', 'npm install')"
                },
                "workdir": {
                    "type": "string",
                    "description": "Directorio de trabajo para ejecutar el comando (opcional)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout en segundos (default: 30)"
                }
            },
            "required": ["command"]
        },
        "handler": shell_execute
    },
    "python": {
        "id": "python",
        "name": "python",
        "description": "Ejecuta código Python en un contenedor Docker aislado. Ideal para cálculos, procesamiento de datos, scripts.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Código Python a ejecutar. Usa print() para mostrar resultados."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout en segundos (default: 30)"
                }
            },
            "required": ["code"]
        },
        "handler": python_execute
    },
    "javascript": {
        "id": "javascript",
        "name": "javascript",
        "description": "Ejecuta código JavaScript/Node.js en un contenedor Docker aislado. Ideal para scripts, manipulación de JSON.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Código JavaScript a ejecutar. Usa console.log() para mostrar resultados."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout en segundos (default: 30)"
                }
            },
            "required": ["code"]
        },
        "handler": javascript_execute
    }
}
