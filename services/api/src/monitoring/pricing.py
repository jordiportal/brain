"""
Pricing Service - Dynamic LLM pricing from models.dev

Descarga y cachea los precios de modelos LLM desde https://models.dev/api.json
para calcular costes reales en la monitorización.
"""

import asyncio
import time
from typing import Optional, Dict, Tuple
import structlog

try:
    import httpx
except ImportError:
    httpx = None

logger = structlog.get_logger()

MODELS_DEV_URL = "https://models.dev/api.json"
CACHE_TTL_SECONDS = 6 * 3600  # 6 horas

# Mapeo de provider_type de Brain -> lista de provider IDs en models.dev
# Brain usa tipos genéricos ("openai", "anthropic") pero también proveedores
# intermediarios ("opencode") que tienen su propia sección en models.dev.
PROVIDER_ALIASES: Dict[str, list] = {
    "opencode": ["opencode"],
    "openai": ["openai"],
    "anthropic": ["anthropic"],
    "google": ["google-vertex", "google-ai-studio"],
    "azure": ["azure", "azure-cognitive-services"],
    "groq": ["groq"],
    "deepinfra": ["deepinfra"],
    "togetherai": ["togetherai"],
    "fireworks": ["fireworks-ai"],
    "ollama": [],
    "local": [],
}


class PricingService:
    """
    Servicio de precios dinámicos para modelos LLM.

    Descarga periódicamente la tabla de precios de models.dev y la cachea
    en memoria. El lookup se hace por (provider_type, model_name) con
    matching parcial para tolerar diferencias de naming.
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Dict[str, float]]] = {}
        self._cache_ts: float = 0
        self._loading: bool = False
        self._lock = asyncio.Lock()

    async def _fetch_pricing(self) -> Dict:
        if httpx is None:
            logger.warning("httpx not installed, cannot fetch models.dev pricing")
            return {}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(MODELS_DEV_URL)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("Failed to fetch models.dev pricing", error=str(e))
            return {}

    def _build_cache(self, raw: Dict) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Construye un índice plano:
          { provider_id: { model_id_normalizado: { "input": X, "output": Y } } }
        """
        cache: Dict[str, Dict[str, Dict[str, float]]] = {}

        for provider_id, provider_data in raw.items():
            if not isinstance(provider_data, dict):
                continue
            models = provider_data.get("models", {})
            if not isinstance(models, dict):
                continue

            provider_cache: Dict[str, Dict[str, float]] = {}
            for model_id, model_data in models.items():
                if not isinstance(model_data, dict):
                    continue
                cost = model_data.get("cost")
                if not cost or not isinstance(cost, dict):
                    continue

                input_cost = cost.get("input")
                output_cost = cost.get("output")
                if input_cost is None or output_cost is None:
                    continue
                if input_cost == 0 and output_cost == 0:
                    continue

                normalized = self._normalize_model_id(model_id)
                provider_cache[normalized] = {
                    "input": float(input_cost),
                    "output": float(output_cost),
                }

            if provider_cache:
                cache[provider_id] = provider_cache

        return cache

    @staticmethod
    def _normalize_model_id(model_id: str) -> str:
        """Normaliza un model_id para matching flexible."""
        s = model_id.lower().strip()
        # Quitar prefijos de organización (moonshotai/, openai/, etc.)
        if "/" in s:
            s = s.rsplit("/", 1)[-1]
        return s

    async def ensure_loaded(self) -> None:
        """Carga (o recarga si expiró) la tabla de precios."""
        now = time.time()
        if self._cache and (now - self._cache_ts) < CACHE_TTL_SECONDS:
            return

        async with self._lock:
            # Double-check tras adquirir el lock
            if self._cache and (time.time() - self._cache_ts) < CACHE_TTL_SECONDS:
                return

            self._loading = True
            try:
                raw = await self._fetch_pricing()
                if raw:
                    self._cache = self._build_cache(raw)
                    self._cache_ts = time.time()
                    total_models = sum(len(m) for m in self._cache.values())
                    logger.info(
                        "models.dev pricing loaded",
                        providers=len(self._cache),
                        models=total_models,
                    )
            finally:
                self._loading = False

    def _search_in_providers(
        self, provider_ids: list, norm_model: str
    ) -> Optional[Dict[str, float]]:
        """Busca un modelo normalizado en una lista de provider IDs."""
        for pid in provider_ids:
            provider_models = self._cache.get(pid)
            if not provider_models:
                continue

            # Match exacto
            if norm_model in provider_models:
                return provider_models[norm_model]

            # Match parcial: el nombre del modelo contiene o está contenido
            best_match = None
            best_score = 0
            for cached_model, price in provider_models.items():
                if norm_model in cached_model or cached_model in norm_model:
                    score = len(cached_model)
                    if score > best_score:
                        best_score = score
                        best_match = price

            if best_match:
                return best_match

        return None

    def lookup(
        self, provider_type: str, model: str
    ) -> Optional[Dict[str, float]]:
        """
        Busca el precio de un modelo. Devuelve {"input": X, "output": Y}
        (por 1M tokens) o None si no se encuentra.

        Estrategia de matching:
        1. Provider directo + aliases -> modelo exacto o parcial
        2. Fallback global: buscar en TODOS los providers
           (necesario cuando el type es "openai" pero el modelo real
           vive en "opencode" u otro provider intermediario)
        """
        if not self._cache:
            return None

        norm_model = self._normalize_model_id(model)

        # Lista de provider IDs candidatos (directos + aliases)
        provider_ids = [provider_type.lower()]
        for alias_key, alias_list in PROVIDER_ALIASES.items():
            if alias_key == provider_type.lower():
                provider_ids.extend(alias_list)
                break

        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_ids = []
        for pid in provider_ids:
            if pid not in seen:
                seen.add(pid)
                unique_ids.append(pid)

        result = self._search_in_providers(unique_ids, norm_model)
        if result:
            return result

        # Fallback global: buscar en todos los providers restantes
        remaining = [p for p in self._cache if p not in seen]
        return self._search_in_providers(remaining, norm_model)

    def estimate_cost(
        self,
        provider: str,
        model: str,
        tokens_input: int,
        tokens_output: int,
    ) -> Optional[float]:
        """
        Calcula el coste estimado en USD.
        Devuelve None si no hay datos de precio para este modelo.
        """
        if provider.lower() in ("ollama", "local"):
            return 0.0

        price = self.lookup(provider, model)
        if not price:
            return None

        input_cost = (tokens_input / 1_000_000) * price["input"]
        output_cost = (tokens_output / 1_000_000) * price["output"]
        return input_cost + output_cost

    @property
    def is_loaded(self) -> bool:
        return bool(self._cache)

    @property
    def cached_providers(self) -> int:
        return len(self._cache)

    @property
    def cached_models(self) -> int:
        return sum(len(m) for m in self._cache.values())


# Instancia global
pricing_service = PricingService()
