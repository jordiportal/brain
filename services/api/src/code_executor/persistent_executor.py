"""
Persistent Code Executor - Ejecuta código en contenedor permanente con volumen persistente

Diferencias con CodeExecutor:
- Contenedor permanente (no se destruye)
- Volumen montado para persistencia
- Red habilitada
- Acceso a base de datos y servicios
"""

import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional
import structlog

from .models import (
    ExecutionResult,
    ExecutionStatus,
    Language
)

logger = structlog.get_logger()


class PersistentCodeExecutor:
    """Ejecutor de código en contenedor Docker permanente"""
    
    CONTAINER_NAME = "brain-persistent-runner"
    WORKSPACE_PATH = "/workspace"
    
    def __init__(self):
        """Inicializa el ejecutor persistente"""
        self._verify_container_running()
    
    def _verify_container_running(self) -> bool:
        """Verifica que el contenedor persistente esté corriendo"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.CONTAINER_NAME}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if self.CONTAINER_NAME in result.stdout:
                logger.info(f"Contenedor persistente {self.CONTAINER_NAME} está corriendo")
                return True
            else:
                logger.warning(f"Contenedor {self.CONTAINER_NAME} no está corriendo")
                return False
                
        except Exception as e:
            logger.error(f"Error verificando contenedor: {e}")
            return False
    
    async def execute_python(
        self,
        code: str,
        script_name: Optional[str] = None,
        timeout: int = 300,  # 5 minutos por defecto (más tiempo que efímero)
        save_script: bool = True
    ) -> ExecutionResult:
        """
        Ejecuta código Python en el contenedor persistente.
        
        Args:
            code: Código Python a ejecutar
            script_name: Nombre del script (generado si no se proporciona)
            timeout: Timeout en segundos (default: 300s)
            save_script: Si True, guarda el script en /workspace/scripts
        
        Returns:
            ExecutionResult con los resultados
        """
        start_time = time.time()
        
        # Generar nombre único si no se proporciona
        if not script_name:
            script_name = f"script_{uuid.uuid4().hex[:8]}.py"
        elif not script_name.endswith('.py'):
            script_name = f"{script_name}.py"
        
        script_path = f"{self.WORKSPACE_PATH}/scripts/{script_name}"
        
        try:
            logger.info(
                "Ejecutando Python en contenedor persistente",
                script=script_name,
                timeout=timeout,
                save=save_script
            )
            
            # Paso 1: Escribir código en el contenedor
            write_cmd = [
                "docker", "exec",
                self.CONTAINER_NAME,
                "bash", "-c",
                f'cat > {script_path} << \'EOFPYTHON\'\n{code}\nEOFPYTHON'
            ]
            
            write_result = subprocess.run(
                write_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if write_result.returncode != 0:
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Error escribiendo script: {write_result.stderr}",
                    exit_code=write_result.returncode,
                    execution_time=time.time() - start_time,
                    status=ExecutionStatus.CONTAINER_ERROR,
                    language=Language.PYTHON,
                    error_message="No se pudo escribir el script en el contenedor",
                    container_id=self.CONTAINER_NAME
                )
            
            # Paso 2: Ejecutar el script
            exec_cmd = [
                "docker", "exec",
                self.CONTAINER_NAME,
                "python", script_path
            ]
            
            try:
                exec_result = subprocess.run(
                    exec_cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                stdout = exec_result.stdout
                stderr = exec_result.stderr
                exit_code = exec_result.returncode
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
                
                # Paso 3: Limpiar script si no se debe guardar
                if not save_script:
                    subprocess.run(
                        ["docker", "exec", self.CONTAINER_NAME, "rm", "-f", script_path],
                        capture_output=True,
                        timeout=5
                    )
                
                logger.info(
                    "Ejecución persistente completada",
                    script=script_name,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    success=success,
                    saved=save_script
                )
                
                return ExecutionResult(
                    success=success,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    execution_time=execution_time,
                    status=status,
                    language=Language.PYTHON,
                    error_message=error_msg,
                    container_id=self.CONTAINER_NAME
                )
            
            except subprocess.TimeoutExpired:
                execution_time = time.time() - start_time
                logger.warning(f"Timeout después de {timeout}s en contenedor persistente")
                
                # Intentar limpiar
                if not save_script:
                    subprocess.run(
                        ["docker", "exec", self.CONTAINER_NAME, "rm", "-f", script_path],
                        capture_output=True,
                        timeout=5
                    )
                
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr=f"Ejecución cancelada: timeout de {timeout} segundos excedido",
                    exit_code=-1,
                    execution_time=execution_time,
                    status=ExecutionStatus.TIMEOUT,
                    language=Language.PYTHON,
                    error_message=f"Timeout después de {timeout} segundos",
                    container_id=self.CONTAINER_NAME
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
                language=Language.PYTHON,
                error_message=error_msg,
                container_id=self.CONTAINER_NAME
            )
    
    def list_scripts(self) -> list[str]:
        """Lista scripts guardados en /workspace/scripts"""
        try:
            result = subprocess.run(
                ["docker", "exec", self.CONTAINER_NAME, "ls", "-1", f"{self.WORKSPACE_PATH}/scripts"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                scripts = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                return scripts
            else:
                return []
        
        except Exception as e:
            logger.error(f"Error listando scripts: {e}")
            return []
    
    def read_file(self, file_path: str) -> Optional[str]:
        """Lee un archivo del workspace del contenedor"""
        try:
            full_path = f"{self.WORKSPACE_PATH}/{file_path}"
            result = subprocess.run(
                ["docker", "exec", self.CONTAINER_NAME, "cat", full_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Error leyendo archivo: {result.stderr}")
                return None
        
        except Exception as e:
            logger.error(f"Error leyendo archivo: {e}")
            return None
    
    def write_file(self, file_path: str, content: str) -> bool:
        """Escribe un archivo en el workspace del contenedor"""
        try:
            full_path = f"{self.WORKSPACE_PATH}/{file_path}"
            
            # Crear directorio si no existe
            dir_path = str(Path(full_path).parent)
            subprocess.run(
                ["docker", "exec", self.CONTAINER_NAME, "mkdir", "-p", dir_path],
                capture_output=True,
                timeout=5
            )
            
            # Escribir archivo
            write_cmd = [
                "docker", "exec",
                self.CONTAINER_NAME,
                "bash", "-c",
                f'cat > {full_path} << \'EOFFILE\'\n{content}\nEOFFILE'
            ]
            
            result = subprocess.run(
                write_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return result.returncode == 0
        
        except Exception as e:
            logger.error(f"Error escribiendo archivo: {e}")
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """Elimina un archivo del workspace"""
        try:
            full_path = f"{self.WORKSPACE_PATH}/{file_path}"
            result = subprocess.run(
                ["docker", "exec", self.CONTAINER_NAME, "rm", "-f", full_path],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        
        except Exception as e:
            logger.error(f"Error eliminando archivo: {e}")
            return False
    
    def health_check(self) -> bool:
        """Verifica que el contenedor esté funcionando"""
        return self._verify_container_running()


# Instancia global lazy (creada cuando se solicita)
_persistent_executor_instance = None


def get_persistent_executor() -> PersistentCodeExecutor:
    """Obtiene la instancia singleton del executor persistente"""
    global _persistent_executor_instance
    
    if _persistent_executor_instance is None:
        _persistent_executor_instance = PersistentCodeExecutor()
    
    return _persistent_executor_instance
