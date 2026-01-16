"""
Embeddings con Ollama
"""

from typing import List
import httpx
import structlog
from langchain_core.embeddings import Embeddings

logger = structlog.get_logger()


class OllamaEmbeddings(Embeddings):
    """Embeddings usando Ollama API directamente"""
    
    def __init__(
        self,
        base_url: str = "http://host.docker.internal:11434",
        model: str = "qwen3-embedding:8b"
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generar embeddings para múltiples textos"""
        embeddings = []
        for text in texts:
            embedding = self._embed_single(text)
            embeddings.append(embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Generar embedding para una query"""
        return self._embed_single(text)
    
    def _embed_single(self, text: str) -> List[float]:
        """Generar embedding para un texto"""
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.base_url}/api/embed",
                    json={
                        "model": self.model,
                        "input": text
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Ollama devuelve embeddings en data["embeddings"][0]
                embeddings = data.get("embeddings", [[]])
                if embeddings and len(embeddings) > 0:
                    return embeddings[0]
                
                # Fallback para versiones antiguas de Ollama
                return data.get("embedding", [])
                
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            raise
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Versión async de embed_documents"""
        embeddings = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                embedding = await self._aembed_single(client, text)
                embeddings.append(embedding)
        return embeddings
    
    async def aembed_query(self, text: str) -> List[float]:
        """Versión async de embed_query"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            return await self._aembed_single(client, text)
    
    async def _aembed_single(self, client: httpx.AsyncClient, text: str) -> List[float]:
        """Generar embedding async para un texto"""
        try:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": text
                }
            )
            response.raise_for_status()
            data = response.json()
            
            embeddings = data.get("embeddings", [[]])
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
            
            return data.get("embedding", [])
            
        except Exception as e:
            logger.error(f"Error generando embedding async: {e}")
            raise
