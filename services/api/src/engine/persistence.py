"""
Persistencia de cadenas en Strapi
"""

import os
import httpx
import structlog
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = structlog.get_logger()

STRAPI_URL = os.getenv("STRAPI_URL", "http://strapi:1337")


@dataclass
class StrapiChain:
    """Cadena almacenada en Strapi"""
    id: int
    documentId: str
    name: str
    slug: str
    type: str
    description: str
    version: str
    nodes: List[Dict]
    edges: List[Dict]
    config: Dict
    isActive: bool


class ChainPersistence:
    """Gestiona la persistencia de cadenas en Strapi"""
    
    def __init__(self, strapi_url: str = None, api_token: str = None):
        self.strapi_url = strapi_url or STRAPI_URL
        self.api_token = api_token or os.getenv("STRAPI_API_TOKEN")
    
    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers
    
    async def list_chains(self) -> List[StrapiChain]:
        """Listar todas las cadenas de Strapi"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.strapi_url}/api/brain-chains",
                    headers=self._get_headers(),
                    params={"populate": "*", "pagination[pageSize]": 100}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    chains = []
                    for item in data.get("data", []):
                        chains.append(self._parse_strapi_chain(item))
                    return chains
                else:
                    logger.warning(f"Error listando cadenas de Strapi: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error conectando con Strapi: {e}")
            return []
    
    async def get_chain(self, chain_slug: str) -> Optional[StrapiChain]:
        """Obtener una cadena por slug"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.strapi_url}/api/brain-chains",
                    headers=self._get_headers(),
                    params={
                        "filters[slug][$eq]": chain_slug,
                        "populate": "*"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("data", [])
                    if items:
                        return self._parse_strapi_chain(items[0])
                return None
        except Exception as e:
            logger.error(f"Error obteniendo cadena de Strapi: {e}")
            return None
    
    async def save_chain(self, chain_data: Dict[str, Any]) -> Optional[StrapiChain]:
        """Guardar o actualizar una cadena en Strapi"""
        try:
            slug = chain_data.get("slug") or chain_data.get("id")
            
            # Verificar si existe
            existing = await self.get_chain(slug)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {"data": self._prepare_strapi_data(chain_data)}
                
                if existing:
                    # Actualizar
                    response = await client.put(
                        f"{self.strapi_url}/api/brain-chains/{existing.documentId}",
                        headers=self._get_headers(),
                        json=payload
                    )
                else:
                    # Crear
                    response = await client.post(
                        f"{self.strapi_url}/api/brain-chains",
                        headers=self._get_headers(),
                        json=payload
                    )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    return self._parse_strapi_chain(data.get("data", {}))
                else:
                    logger.error(f"Error guardando cadena: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.error(f"Error guardando cadena en Strapi: {e}")
            return None
    
    async def delete_chain(self, chain_slug: str) -> bool:
        """Eliminar una cadena de Strapi"""
        try:
            existing = await self.get_chain(chain_slug)
            if not existing:
                return False
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.strapi_url}/api/brain-chains/{existing.documentId}",
                    headers=self._get_headers()
                )
                return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error eliminando cadena de Strapi: {e}")
            return False
    
    async def sync_from_registry(self, registry) -> Dict[str, Any]:
        """Sincronizar cadenas del registry a Strapi"""
        results = {"synced": [], "errors": []}
        
        for chain in registry.list_chains():
            chain_data = {
                "id": chain.id,
                "slug": chain.id,
                "name": chain.name,
                "type": chain.type,
                "description": chain.description,
                "version": chain.version,
                "nodes": [
                    {
                        "id": n.id,
                        "type": n.type.value,
                        "name": n.name,
                        "system_prompt": n.system_prompt,
                        "config": n.config,
                        "collection": n.collection,
                        "top_k": n.top_k,
                        "tools": n.tools
                    }
                    for n in chain.nodes
                ],
                "edges": [
                    {"source": e.source, "target": e.target, "condition": e.condition}
                    for e in chain.edges
                ],
                "config": chain.config.model_dump(),
                "isActive": True
            }
            
            saved = await self.save_chain(chain_data)
            if saved:
                results["synced"].append(chain.id)
            else:
                results["errors"].append(chain.id)
        
        return results
    
    def _parse_strapi_chain(self, item: Dict) -> StrapiChain:
        """Parsear respuesta de Strapi a StrapiChain"""
        return StrapiChain(
            id=item.get("id", 0),
            documentId=item.get("documentId", ""),
            name=item.get("name", ""),
            slug=item.get("slug", ""),
            type=item.get("type", "chain"),
            description=item.get("description", ""),
            version=item.get("version", "1.0.0"),
            nodes=item.get("nodes") or [],
            edges=item.get("edges") or [],
            config=item.get("config") or {},
            isActive=item.get("isActive", True)
        )
    
    def _prepare_strapi_data(self, chain_data: Dict) -> Dict:
        """Preparar datos para enviar a Strapi"""
        return {
            "name": chain_data.get("name"),
            "slug": chain_data.get("slug") or chain_data.get("id"),
            "type": chain_data.get("type", "chain"),
            "description": chain_data.get("description", ""),
            "version": chain_data.get("version", "1.0.0"),
            "nodes": chain_data.get("nodes", []),
            "edges": chain_data.get("edges", []),
            "config": chain_data.get("config", {}),
            "isActive": chain_data.get("isActive", True),
            "definition": chain_data  # Guardar definición completa como backup
        }


# Instancia global
chain_persistence = ChainPersistence()
