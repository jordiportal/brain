"""
BrainSettingsRepository - Acceso a la tabla brain_settings.

Incluye caché en memoria con TTL para evitar consultas a BD en cada
llamada de tool (el executor llama a get() en cada iteración).
"""

import time
import json
from typing import Any, Dict, List, Optional

import structlog

from src.db import get_db

logger = structlog.get_logger()

# Caché en memoria: {key: (value, cached_at)}
_cache: Dict[str, tuple[Any, float]] = {}
_CACHE_TTL = 60.0  # segundos


def _invalidate(key: Optional[str] = None) -> None:
    if key:
        _cache.pop(key, None)
    else:
        _cache.clear()


class BrainSettingsRepository:

    @staticmethod
    def _parse_value(raw: Any) -> Any:
        """Parsea el valor JSONB devuelto por asyncpg (puede ser str o ya parseado)."""
        if isinstance(raw, str):
            return json.loads(raw)
        return raw

    @staticmethod
    async def get_all() -> List[Dict[str, Any]]:
        """Devuelve todos los settings como lista de dicts."""
        db = get_db()
        rows = await db.fetch_all(
            "SELECT id, key, value, type, category, label, description, is_public, created_at, updated_at "
            "FROM brain_settings ORDER BY category, key"
        )
        result = []
        for r in rows:
            d = dict(r)
            d["value"] = BrainSettingsRepository._parse_value(d["value"])
            result.append(d)
        return result

    @staticmethod
    async def get(key: str, default: Any = None) -> Any:
        """
        Devuelve el valor del setting por clave.
        Usa caché con TTL para minimizar consultas.
        """
        now = time.time()
        cached = _cache.get(key)
        if cached and (now - cached[1]) < _CACHE_TTL:
            return cached[0]

        db = get_db()
        row = await db.fetch_one(
            "SELECT value FROM brain_settings WHERE key = $1", key
        )
        if row is None:
            return default

        # JSONB viene como string o ya parseado según el driver
        raw = row["value"]
        value = raw if not isinstance(raw, str) else json.loads(raw)
        _cache[key] = (value, now)
        return value

    @staticmethod
    async def get_int(key: str, default: int = 0) -> int:
        val = await BrainSettingsRepository.get(key, default)
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    @staticmethod
    async def upsert(key: str, value: Any) -> Dict[str, Any]:
        """Actualiza el valor de un setting existente."""
        db = get_db()
        value_json = json.dumps(value)
        row = await db.fetch_one(
            """
            UPDATE brain_settings
               SET value = $1::jsonb, updated_at = NOW()
             WHERE key = $2
            RETURNING id, key, value, type, category, label, description, is_public, updated_at
            """,
            value_json,
            key,
        )
        if row is None:
            raise KeyError(f"Setting '{key}' not found")
        _invalidate(key)
        logger.info("Brain setting updated", key=key, value=value)
        d = dict(row)
        d["value"] = BrainSettingsRepository._parse_value(d["value"])
        return d
