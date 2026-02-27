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
    
    WORKSPACE_PATH = "/workspace"
    
    def __init__(self, container_name: str = "brain-persistent-runner"):
        self.container_name = container_name
        self._verify_container_running()
    
    def _verify_container_running(self) -> bool:
        """Verifica que el contenedor persistente esté corriendo"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if self.container_name in result.stdout:
                logger.info(f"Contenedor persistente {self.container_name} está corriendo")
                return True
            else:
                logger.warning(f"Contenedor {self.container_name} no está corriendo")
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
                self.container_name,
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
                    container_id=self.container_name
                )
            
            # Paso 2: Ejecutar el script
            exec_cmd = [
                "docker", "exec",
                self.container_name,
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
                        ["docker", "exec", self.container_name, "rm", "-f", script_path],
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
                    container_id=self.container_name
                )
            
            except subprocess.TimeoutExpired:
                execution_time = time.time() - start_time
                logger.warning(f"Timeout después de {timeout}s en contenedor persistente")
                
                # Intentar limpiar
                if not save_script:
                    subprocess.run(
                        ["docker", "exec", self.container_name, "rm", "-f", script_path],
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
                    container_id=self.container_name
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
                container_id=self.container_name
            )
    
    def list_scripts(self) -> list[str]:
        """Lista scripts guardados en /workspace/scripts"""
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_name, "ls", "-1", f"{self.WORKSPACE_PATH}/scripts"],
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
                ["docker", "exec", self.container_name, "cat", full_path],
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
                ["docker", "exec", self.container_name, "mkdir", "-p", dir_path],
                capture_output=True,
                timeout=5
            )
            
            # Escribir archivo
            write_cmd = [
                "docker", "exec",
                self.container_name,
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
    
    def write_binary_file(self, file_path: str, data: bytes) -> bool:
        """
        Escribe un archivo binario en el workspace del contenedor.
        
        Args:
            file_path: Ruta relativa al workspace (ej: "media/videos/video.mp4")
            data: Bytes del archivo
            
        Returns:
            True si se escribió correctamente
        """
        import tempfile
        
        try:
            full_path = f"{self.WORKSPACE_PATH}/{file_path}"
            
            # Crear directorio en el contenedor si no existe
            dir_path = str(Path(full_path).parent)
            subprocess.run(
                ["docker", "exec", self.container_name, "mkdir", "-p", dir_path],
                capture_output=True,
                timeout=5
            )
            
            # Escribir a archivo temporal local
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            
            try:
                # Copiar al contenedor usando docker cp
                result = subprocess.run(
                    ["docker", "cp", tmp_path, f"{self.container_name}:{full_path}"],
                    capture_output=True,
                    timeout=60  # Timeout más largo para archivos grandes
                )
                
                if result.returncode == 0:
                    logger.info(f"Archivo binario guardado: {file_path} ({len(data)} bytes)")
                    return True
                else:
                    logger.error(f"Error copiando archivo: {result.stderr.decode()}")
                    return False
            finally:
                # Limpiar archivo temporal
                import os
                os.unlink(tmp_path)
        
        except Exception as e:
            logger.error(f"Error escribiendo archivo binario: {e}")
            return False
    
    def read_binary_file(self, file_path: str) -> Optional[bytes]:
        """
        Lee un archivo binario del workspace. Intenta primero via host mount
        (rapido, no requiere container running), fallback a docker cp.
        """
        data = self.read_binary_file_from_host(file_path)
        if data is not None:
            return data
        return self._read_binary_file_docker_cp(file_path)

    def read_binary_file_from_host(self, file_path: str) -> Optional[bytes]:
        """
        Lee directamente del bind-mount en el host, sin docker cp.
        Requires SANDBOX_WORKSPACE_BASE env var and a user_id-based path.
        """
        import os
        host_base = os.getenv("SANDBOX_WORKSPACE_BASE", "")
        if not host_base:
            return None

        from .sandbox_manager import sandbox_manager
        # container_name is brain-sandbox-{hash} or brain-persistent-runner
        # Reverse-lookup: try to find the host workspace from the container volumes
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}", self.container_name],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                for mount in result.stdout.strip().split():
                    parts = mount.split(":")
                    if len(parts) == 2 and parts[1] == "/workspace":
                        host_path = Path(parts[0]) / file_path
                        if host_path.exists():
                            return host_path.read_bytes()
        except Exception:
            pass

        return None

    def _read_binary_file_docker_cp(self, file_path: str) -> Optional[bytes]:
        """Fallback: read via docker cp (requires container running)."""
        import tempfile

        try:
            full_path = f"{self.WORKSPACE_PATH}/{file_path}"

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name

            try:
                result = subprocess.run(
                    ["docker", "cp", f"{self.container_name}:{full_path}", tmp_path],
                    capture_output=True,
                    timeout=60
                )

                if result.returncode == 0:
                    with open(tmp_path, 'rb') as f:
                        return f.read()
                else:
                    logger.error(f"Error leyendo archivo binario: {result.stderr.decode()}")
                    return None
            finally:
                import os
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Error leyendo archivo binario: {e}")
            return None
    
    def get_workspace_url(self, file_path: str) -> str:
        """
        Obtiene la URL para acceder a un archivo del workspace.
        
        Args:
            file_path: Ruta relativa al workspace
            
        Returns:
            URL para acceder al archivo vía API
        """
        # URL del endpoint de archivos del workspace
        return f"/api/v1/workspace/files/{file_path}"
    
    def delete_file(self, file_path: str) -> bool:
        """Elimina un archivo del workspace"""
        try:
            full_path = f"{self.WORKSPACE_PATH}/{file_path}"
            result = subprocess.run(
                ["docker", "exec", self.container_name, "rm", "-f", full_path],
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
