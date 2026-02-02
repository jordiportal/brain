"""
Brain 2.0 Tool Configuration

Carga y gestiona la configuración de las Core Tools.
Usa variables de entorno o configuración por defecto.
"""

import os
import httpx
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import structlog

logger = structlog.get_logger()


@dataclass
class FilesystemConfig:
    """Configuración de herramientas de filesystem"""
    workspace_root: str = "/workspace"
    allowed_paths: list = field(default_factory=lambda: ["/workspace", "/app/src"])
    max_file_size_mb: int = 10
    allow_absolute_paths: bool = False
    read_enabled: bool = True
    write_enabled: bool = True
    edit_enabled: bool = True
    list_enabled: bool = True
    search_enabled: bool = True


@dataclass
class ExecutionConfig:
    """Configuración de herramientas de ejecución"""
    python_image: str = "python:3.11-slim"
    node_image: str = "node:20-slim"
    timeout_seconds: int = 30
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    network_enabled: bool = False
    shell_enabled: bool = True
    python_enabled: bool = True
    javascript_enabled: bool = True
    shell_blacklist: list = field(default_factory=lambda: ["rm -rf /", "mkfs", "dd if="])


@dataclass
class WebConfig:
    """Configuración de herramientas web"""
    search_provider: str = "duckduckgo"  # duckduckgo, serper, google, bing, tavily
    search_api_key: Optional[str] = None
    search_max_results: int = 5
    fetch_timeout: int = 30
    fetch_max_size_mb: int = 5
    fetch_user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    search_enabled: bool = True
    fetch_enabled: bool = True
    blocked_domains: list = field(default_factory=list)


@dataclass
class ToolConfig:
    """Configuración global de tools"""
    filesystem: FilesystemConfig = field(default_factory=FilesystemConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    web: WebConfig = field(default_factory=WebConfig)
    is_active: bool = True
    last_updated: Optional[datetime] = None


class ToolConfigManager:
    """Gestiona la configuración de tools"""
    
    def __init__(self):
        self._config: Optional[ToolConfig] = None
    
    @property
    def config(self) -> ToolConfig:
        """Obtiene la configuración actual (carga si no existe)"""
        if self._config is None:
            self._config = self._load_default_config()
        return self._config
    
    def _load_default_config(self) -> ToolConfig:
        """Carga configuración por defecto desde variables de entorno"""
        logger.info("Loading default tool configuration from environment")
        
        config = ToolConfig()
        
        # Filesystem desde env
        config.filesystem.workspace_root = os.getenv("WORKSPACE_ROOT", "/workspace")
        
        # Execution desde env
        config.execution.python_image = os.getenv("CODE_RUNNER_PYTHON_IMAGE", "python:3.11-slim")
        config.execution.node_image = os.getenv("CODE_RUNNER_NODE_IMAGE", "node:20-slim")
        config.execution.timeout_seconds = int(os.getenv("CODE_EXECUTION_TIMEOUT", "30"))
        config.execution.memory_limit = os.getenv("CODE_EXECUTION_MEMORY_LIMIT", "512m")
        
        # Web desde env
        config.web.search_provider = os.getenv("WEB_SEARCH_PROVIDER", "duckduckgo")
        config.web.search_api_key = os.getenv("WEB_SEARCH_API_KEY")
        config.web.fetch_timeout = int(os.getenv("WEB_FETCH_TIMEOUT", "30"))
        
        return config
    
    async def load_from_strapi(self) -> ToolConfig:
        """Carga configuración desde Strapi"""
        if not self._strapi_token:
            logger.warning("STRAPI_API_TOKEN not set, using default config")
            return self._load_default_config()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self._strapi_url}/api/tool-config",
                    headers={"Authorization": f"Bearer {self._strapi_token}"},
                    params={"populate": "*"}
                )
                
                if response.status_code == 404:
                    logger.info("Tool config not found in Strapi, using defaults")
                    return self._load_default_config()
                
                response.raise_for_status()
                data = response.json()
                
                if not data.get("data"):
                    logger.info("Tool config empty in Strapi, using defaults")
                    return self._load_default_config()
                
                attrs = data["data"].get("attributes", {})
                config = self._parse_strapi_config(attrs)
                
                self._config = config
                logger.info("Tool configuration loaded from Strapi")
                
                return config
                
        except Exception as e:
            logger.error(f"Error loading tool config from Strapi: {e}")
            return self._load_default_config()
    
    def _parse_strapi_config(self, attrs: Dict[str, Any]) -> ToolConfig:
        """Parsea la configuración desde Strapi"""
        config = ToolConfig()
        
        # Filesystem
        if fs := attrs.get("filesystem"):
            config.filesystem = FilesystemConfig(
                workspace_root=fs.get("workspaceRoot", "/workspace"),
                allowed_paths=fs.get("allowedPaths", ["/workspace", "/app/src"]),
                max_file_size_mb=fs.get("maxFileSizeMB", 10),
                allow_absolute_paths=fs.get("allowAbsolutePaths", False),
                read_enabled=fs.get("readEnabled", True),
                write_enabled=fs.get("writeEnabled", True),
                edit_enabled=fs.get("editEnabled", True),
                list_enabled=fs.get("listEnabled", True),
                search_enabled=fs.get("searchEnabled", True)
            )
        
        # Execution
        if ex := attrs.get("execution"):
            config.execution = ExecutionConfig(
                python_image=ex.get("pythonImage", "python:3.11-slim"),
                node_image=ex.get("nodeImage", "node:20-slim"),
                timeout_seconds=ex.get("timeoutSeconds", 30),
                memory_limit=ex.get("memoryLimit", "512m"),
                cpu_limit=ex.get("cpuLimit", "1.0"),
                network_enabled=ex.get("networkEnabled", False),
                shell_enabled=ex.get("shellEnabled", True),
                python_enabled=ex.get("pythonEnabled", True),
                javascript_enabled=ex.get("javascriptEnabled", True),
                shell_blacklist=ex.get("shellBlacklist", [])
            )
        
        # Web
        if web := attrs.get("web"):
            config.web = WebConfig(
                search_provider=web.get("searchProvider", "duckduckgo"),
                search_api_key=web.get("searchApiKey"),
                search_max_results=web.get("searchMaxResults", 5),
                fetch_timeout=web.get("fetchTimeout", 30),
                fetch_max_size_mb=web.get("fetchMaxSizeMB", 5),
                fetch_user_agent=web.get("fetchUserAgent", "Mozilla/5.0"),
                search_enabled=web.get("searchEnabled", True),
                fetch_enabled=web.get("fetchEnabled", True),
                blocked_domains=web.get("blockedDomains", [])
            )
        
        config.is_active = attrs.get("isActive", True)
        
        return config
    
    def reload(self):
        """Fuerza recarga de configuración"""
        self._config = None


# Instancia global
tool_config_manager = ToolConfigManager()


def get_tool_config() -> ToolConfig:
    """Obtiene la configuración de tools"""
    return tool_config_manager.config


def get_filesystem_config() -> FilesystemConfig:
    """Obtiene configuración de filesystem"""
    return tool_config_manager.config.filesystem


def get_execution_config() -> ExecutionConfig:
    """Obtiene configuración de ejecución"""
    return tool_config_manager.config.execution


def get_web_config() -> WebConfig:
    """Obtiene configuración web"""
    return tool_config_manager.config.web
