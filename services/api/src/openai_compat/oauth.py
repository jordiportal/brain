"""
OAuth / Microsoft Entra ID JWT Validator

Validates JWTs issued by Microsoft Entra ID (Azure AD) using JWKS.
Supports both v1 and v2 tokens.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import jwt
from jwt import PyJWKClient
import structlog

from ..db.repositories.brain_settings import BrainSettingsRepository

logger = structlog.get_logger()

# Microsoft v2 OIDC well-known patterns
_JWKS_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
_ISSUER_V2_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/v2.0"
_ISSUER_V1_TEMPLATE = "https://sts.windows.net/{tenant_id}/"


@dataclass
class OAuthConfig:
    enabled: bool = False
    tenant_id: str = ""
    client_id: str = ""


@dataclass
class OAuthClaims:
    """Parsed claims from a validated Microsoft JWT."""
    user_id: str  # preferred_username or email
    name: str = ""
    oid: str = ""  # Azure AD object ID (unique per user)
    tenant_id: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


class OAuthValidator:
    """Validates Microsoft Entra ID JWTs using JWKS."""

    def __init__(self):
        self._jwks_client: Optional[PyJWKClient] = None
        self._jwks_tenant: Optional[str] = None
        self._config_cache: Optional[OAuthConfig] = None
        self._config_cached_at: float = 0
        self._CONFIG_TTL = 60.0  # re-read settings every 60s

    async def _load_config(self) -> OAuthConfig:
        now = time.time()
        if self._config_cache and (now - self._config_cached_at) < self._CONFIG_TTL:
            return self._config_cache

        enabled = await BrainSettingsRepository.get("oauth_enabled", False)
        tenant_id = await BrainSettingsRepository.get("oauth_azure_tenant_id", "")
        client_id = await BrainSettingsRepository.get("oauth_azure_client_id", "")

        self._config_cache = OAuthConfig(
            enabled=bool(enabled),
            tenant_id=str(tenant_id).strip(),
            client_id=str(client_id).strip(),
        )
        self._config_cached_at = now
        return self._config_cache

    def _get_jwks_client(self, tenant_id: str) -> PyJWKClient:
        if self._jwks_client and self._jwks_tenant == tenant_id:
            return self._jwks_client

        jwks_url = _JWKS_URL_TEMPLATE.format(tenant_id=tenant_id)
        self._jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
        self._jwks_tenant = tenant_id
        logger.info("JWKS client initialized", jwks_url=jwks_url)
        return self._jwks_client

    async def is_enabled(self) -> bool:
        cfg = await self._load_config()
        return cfg.enabled and bool(cfg.tenant_id) and bool(cfg.client_id)

    async def validate_token(self, token: str) -> OAuthClaims:
        """
        Validate a Microsoft Entra ID JWT and return parsed claims.

        Raises ValueError on any validation failure.
        """
        cfg = await self._load_config()

        if not cfg.enabled:
            raise ValueError("OAuth authentication is not enabled")
        if not cfg.tenant_id or not cfg.client_id:
            raise ValueError("OAuth not configured: missing tenant_id or client_id")

        try:
            jwks_client = self._get_jwks_client(cfg.tenant_id)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
        except Exception as e:
            logger.warning("JWKS key resolution failed", error=str(e))
            raise ValueError(f"Cannot resolve signing key: {e}")

        # Accept both v1 and v2 issuers
        valid_issuers = [
            _ISSUER_V2_TEMPLATE.format(tenant_id=cfg.tenant_id),
            _ISSUER_V1_TEMPLATE.format(tenant_id=cfg.tenant_id),
        ]

        try:
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=cfg.client_id,
                issuer=valid_issuers,
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidAudienceError:
            raise ValueError("Token audience does not match configured client_id")
        except jwt.InvalidIssuerError:
            raise ValueError("Token issuer does not match configured tenant_id")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid token: {e}")

        # Extract user identity — prefer preferred_username (v2), fall back to upn/email (v1)
        user_id = (
            decoded.get("preferred_username")
            or decoded.get("upn")
            or decoded.get("email")
            or decoded.get("unique_name")
        )
        if not user_id:
            raise ValueError("Token does not contain a user identifier (preferred_username, upn, or email)")

        claims = OAuthClaims(
            user_id=user_id.lower(),
            name=decoded.get("name", ""),
            oid=decoded.get("oid", ""),
            tenant_id=decoded.get("tid", cfg.tenant_id),
            raw=decoded,
        )

        logger.info(
            "OAuth token validated",
            user_id=claims.user_id,
            name=claims.name,
            oid=claims.oid[:8] + "..." if claims.oid else "",
        )
        return claims

    async def check_model_permission(self, model: str) -> bool:
        """Check if a model is allowed for OAuth users."""
        raw = await BrainSettingsRepository.get("oauth_allowed_models", "*")
        allowed = str(raw).strip()
        if not allowed or allowed == "*":
            return True
        models = [m.strip() for m in allowed.split(",") if m.strip()]
        return model in models

    def clear_cache(self):
        self._config_cache = None
        self._config_cached_at = 0
        self._jwks_client = None
        self._jwks_tenant = None


# Global instance
oauth_validator = OAuthValidator()
