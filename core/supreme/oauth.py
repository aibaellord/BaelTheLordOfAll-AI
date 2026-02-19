"""
Lightweight OAuth token manager for provider integrations.

Supports refresh token and client_credentials flows and simple file caching.

Designed to be minimal and dependency-light (uses aiohttp).
"""
from dataclasses import dataclass, field
import os
import json
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("BAEL.OAuth")


@dataclass
class OAuthConfig:
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    auth_url: Optional[str] = None
    scopes: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token: Optional[str] = None
    expires_at: Optional[float] = None
    token_type: Optional[str] = None
    cache_path: Optional[str] = None


class OAuthTokenManager:
    """Manage OAuth tokens with refresh and simple file cache.

    Usage:
      cfg = OAuthConfig(...)
      token = await OAuthTokenManager.get_access_token(cfg)
    """

    @staticmethod
    def _load_cache(path: str) -> Optional[Dict[str, Any]]:
        try:
            if not path or not os.path.exists(path):
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load OAuth cache: {e}")
            return None

    @staticmethod
    def _save_cache(path: str, data: Dict[str, Any]) -> None:
        try:
            d = os.path.dirname(path)
            if d and not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.debug(f"Failed to save OAuth cache: {e}")

    @staticmethod
    async def _request_token(token_url: str, payload: Dict[str, Any], auth: Optional[tuple] = None) -> Dict[str, Any]:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            async with session.post(token_url, data=payload, auth=auth, headers=headers) as resp:
                data = await resp.json()
                if resp.status >= 400:
                    raise Exception(f"OAuth token request failed: {resp.status} {data}")
                return data

    @staticmethod
    async def refresh_or_get(cfg: OAuthConfig) -> Optional[str]:
        """Return a valid access token, refreshing or using cache as needed."""
        # Try cache first
        cache_path = cfg.cache_path or os.environ.get("OAUTH_TOKEN_CACHE_PATH")
        if cache_path:
            cached = OAuthTokenManager._load_cache(cache_path)
            if cached:
                expires_at = cached.get("expires_at")
                if expires_at and time.time() < float(expires_at) - 30:
                    logger.debug("Using cached OAuth token")
                    return cached.get("access_token")

        # Refresh using refresh_token if available
        if cfg.refresh_token and cfg.token_url:
            try:
                payload = {
                    "grant_type": "refresh_token",
                    "refresh_token": cfg.refresh_token,
                }
                if cfg.client_id:
                    payload["client_id"] = cfg.client_id
                if cfg.client_secret:
                    payload["client_secret"] = cfg.client_secret

                data = await OAuthTokenManager._request_token(cfg.token_url, payload)

                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                token_type = data.get("token_type", "Bearer")

                if access_token:
                    expires_at = time.time() + int(expires_in)
                    if cache_path:
                        OAuthTokenManager._save_cache(cache_path, {
                            "access_token": access_token,
                            "expires_at": expires_at,
                            "token_type": token_type,
                        })
                    return access_token

            except Exception as e:
                logger.warning(f"OAuth refresh failed: {e}")

        # Try client_credentials flow
        if cfg.client_id and cfg.client_secret and cfg.token_url:
            try:
                payload = {
                    "grant_type": "client_credentials",
                }
                if cfg.scopes:
                    payload["scope"] = cfg.scopes

                # Basic auth where supported
                auth = (cfg.client_id, cfg.client_secret)
                data = await OAuthTokenManager._request_token(cfg.token_url, payload, auth=auth)

                access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                token_type = data.get("token_type", "Bearer")

                if access_token:
                    expires_at = time.time() + int(expires_in)
                    if cache_path:
                        OAuthTokenManager._save_cache(cache_path, {
                            "access_token": access_token,
                            "expires_at": expires_at,
                            "token_type": token_type,
                        })
                    return access_token

            except Exception as e:
                logger.warning(f"OAuth client_credentials failed: {e}")

        logger.debug("No OAuth token available")
        return None


__all__ = ["OAuthConfig", "OAuthTokenManager"]
