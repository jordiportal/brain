"""
Code Executor - Servicio de ejecución de código en contenedores Docker
"""

import subprocess
import tempfile
import os
import time
import structlog
from typing import Optional

from .models import (
    ExecutionResult,
    ExecutionConfig,
    ExecutionStatus,
    Language
)

logger = structlog.get_logger()


class CodeExecutor:
    """Ejecutor de código en contenedores Docker aislados (usando docker CLI)"""
    
    def __init__(self, config: Optional[ExecutionConfig] = None):
        """
        Inicializa el ejecutor de código.
        
        Args:
            config: Configuración de ejecución (opcional)
        """
        self.config = config or ExecutionConfig()
        
        # Verificar que docker CLI está disponible
        try:
            result = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                docker_version = result.stdout.strip()
                logger.info(f"CodeExecutor inicializado (Docker {docker_version})")
            else:
                raise RuntimeError(f"Docker no responde: {result.stderr}")
        except Exception as e:
            logger.error(f"Error verificando Docker: {e}")
            raise RuntimeError("No se puede conectar al Docker daemon.") from e
    
    async def execute_python(
        self, 
        code: str, 
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Ejecuta código Python en un contenedor aislado.
        
        Args:
            code: Código Python a ejecutar
            timeout: Timeout en segundos (usa config.timeout si no se especifica)
        
        Returns:
            ExecutionResult con los resultados de la ejecución
        """
        timeout = timeout or self.config.timeout
        return await self._execute_code(
            code=code,
            language=Language.PYTHON,
            image="brain-code-runner-python:latest",
            timeout=timeout
        )
    
    async def execute_javascript(
        self,
        code: str,
        timeout: Optional[int] = None
    ) -> ExecutionResult:
        """
        Ejecuta código JavaScript/Node.js en un contenedor aislado.
        
        Args:
            code: Código JavaScript a ejecutar
            timeout: Timeout en segundos (usa config.timeout si no se especifica)
        
        Returns:
            ExecutionResult con los resultados de la ejecución
        """
        timeout = timeout or self.config.timeout
        return await self._execute_code(
            code=code,
            language=Language.JAVASCRIPT,
            image="brain-code-runner-node:latest",
            timeout=timeout
        )
    
    async def _execute_code(
        self,
        code: str,
        language: Language,
        image: str,
        timeout: int
    ) -> ExecutionResult:
        """
        Ejecuta código en un contenedor Docker usando CLI.
        
        Args:
            code: Código a ejecutar
            language: Lenguaje del código
            image: Imagen Docker a usar
            timeout: Timeout en segundos
        
        Returns:
            ExecutionResult con los resultados
        """
        start_time = time.time()
        
        try:
            logger.info(
                f"Ejecutando código {language}",
                timeout=timeout
            )
            
            # Construir comando docker run (pasar código con -c o -e)
            docker_cmd = [
                "docker", "run",
                "--rm",
                f"--memory={self.config.memory_limit}",
                f"--cpus={self.config.cpu_limit}"
            ]
            
            # Deshabilitar red si está configurado
            if self.config.network_disabled:
                docker_cmd.append("--network=none")
            
            # Agregar imagen
            docker_cmd.append(image)
            
            # Agregar comando para ejecutar código
            if language == Language.PYTHON:
                docker_cmd.extend(["python", "-c", code])
            else:  # JavaScript
                docker_cmd.extend(["node", "-e", code])
            
            # Ejecutar con timeout
            try:
                result = subprocess.run(
                    docker_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                stdout = result.stdout
                stderr = result.stderr
                exit_code = result.returncode
                execution_time = time.time() - start_time
                
                # Determinar status
                if exit_code == 0:
                    status = ExecutionStatus.SUCCESS
                    success = True
                    error_msg = None
                else:
                    status = ExecutionStatus.ERROR
                    success = False
                    error_msg = f"Código de salida: {exit_code}"
                
                logger.info(
                    f"Ejecución completada",
                    language=language,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    success=success
                )
                
                return ExecutionResult(
                    success=success,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    status=status,
                    language=language,
                    error_message=error_msg,
                    container_id=None
                )
                
            except subprocess.TimeoutExpired:
                execution_time = time.time() - start_time
                logger.warning(f"Timeout después de {timeout}s")
                
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Ejecución cancelada: timeout de {timeout} segundos excedido",
                    exit_code=-1,
                    execution_time=execution_time,
                    status=ExecutionStatus.TIMEOUT,
                    language=language,
                    error_message=f"Timeout después de {timeout} segundos",
                    container_id=None
                )
            
            except subprocess.CalledProcessError as e:
                execution_time = time.time() - start_time
                logger.error(f"Error ejecutando docker: {e}")
                
                return ExecutionResult(
                    success=False,
                    stdout=e.stdout if e.stdout else "",
                    stderr=e.stderr if e.stderr else str(e),
                    exit_code=e.returncode,
                    execution_time=execution_time,
                    status=ExecutionStatus.CONTAINER_ERROR,
                    language=language,
                    error_message=f"Error del contenedor: {str(e)}",
                    container_id=None
                )
        
        except FileNotFoundError:
            execution_time = time.time() - start_time
            error_msg = "Comando 'docker' no encontrado. Asegúrate de que Docker está instalado."
            logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=error_msg,
                exit_code=-1,
                execution_time=execution_time,
                status=ExecutionStatus.CONTAINER_ERROR,
                language=language,
                error_message=error_msg,
                container_id=None
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=error_msg,
                exit_code=-1,
                execution_time=execution_time,
                status=ExecutionStatus.CONTAINER_ERROR,
                language=language,
                error_message=error_msg,
                container_id=None
            )
    
    def health_check(self) -> bool:
        """
        Verifica que Docker esté funcionando correctamente.
        
        Returns:
            True si Docker está funcionando
        """
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False


# NO crear instancia global aquí - usar lazy loading desde __init__.py
