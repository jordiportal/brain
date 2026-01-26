"""
Brain 2.0 Core Tools - Execution (3 tools)

- shell: Ejecutar comando shell en el host
- python: Ejecutar código Python en contenedor Docker
- javascript: Ejecutar código JavaScript en contenedor Docker
"""

import asyncio
import os
import subprocess
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

# Importar CodeExecutor existente para python/javascript
try:
    from ...code_executor import get_code_executor
    from ...code_executor.models import ExecutionResult
    CODE_EXECUTOR_AVAILABLE = True
except ImportError:
    CODE_EXECUTOR_AVAILABLE = False
    logger.warning("CodeExecutor no disponible, python/javascript tools deshabilitadas")


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
    if not CODE_EXECUTOR_AVAILABLE:
        return {
            "success": False,
            "error": "CodeExecutor no disponible. Verifica que Docker esté funcionando."
        }
    
    try:
        logger.info(f"🐍 python: ejecutando código ({len(code)} chars)", timeout=timeout)
        
        executor = get_code_executor()
        result: ExecutionResult = await executor.execute_python(code, timeout)
        
        logger.info(
            f"✅ python completed",
            success=result.success,
            exit_code=result.exit_code,
            execution_time=result.execution_time
        )
        
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "execution_time": result.execution_time,
            "status": result.status.value if result.status else None,
            "error": result.error_message
        }
        
    except Exception as e:
        logger.error(f"Error ejecutando Python: {e}")
        return {
            "success": False,
            "error": str(e)
        }


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
    if not CODE_EXECUTOR_AVAILABLE:
        return {
            "success": False,
            "error": "CodeExecutor no disponible. Verifica que Docker esté funcionando."
        }
    
    try:
        logger.info(f"📜 javascript: ejecutando código ({len(code)} chars)", timeout=timeout)
        
        executor = get_code_executor()
        result: ExecutionResult = await executor.execute_javascript(code, timeout)
        
        logger.info(
            f"✅ javascript completed",
            success=result.success,
            exit_code=result.exit_code,
            execution_time=result.execution_time
        )
        
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "execution_time": result.execution_time,
            "status": result.status.value if result.status else None,
            "error": result.error_message
        }
        
    except Exception as e:
        logger.error(f"Error ejecutando JavaScript: {e}")
        return {
            "success": False,
            "error": str(e)
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
