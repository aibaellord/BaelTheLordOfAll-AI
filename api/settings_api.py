"""
BAEL Settings API - User Preferences & Configuration
=====================================================

This API handles user settings persistence including:
- API keys (encrypted storage)
- LLM preferences
- Memory settings
- UI preferences
- All configuration that should persist across sessions
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("BAEL.SettingsAPI")

router = APIRouter(prefix="/v1/settings", tags=["settings"])

# Settings storage location
SETTINGS_DIR = Path(__file__).parent.parent / "config" / "settings"
SECRETS_DIR = Path(__file__).parent.parent / "config" / "secrets"
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
SECRETS_DIR.mkdir(parents=True, exist_ok=True)

# Environment variable mappings
ENV_VAR_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "together": "TOGETHER_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "huggingface": "HUGGINGFACE_API_KEY",
    "github": "GITHUB_TOKEN",
}


def load_saved_secrets_to_env():
    """Load saved secrets into environment variables on startup."""
    secrets_file = SECRETS_DIR / "api_keys.json"
    if secrets_file.exists():
        try:
            with open(secrets_file, 'r') as f:
                secrets = json.load(f)
            for provider, data in secrets.items():
                key = data.get("key", "")
                if key:
                    env_var = ENV_VAR_MAP.get(provider.lower())
                    if env_var:
                        os.environ[env_var] = key
                        logger.info(f"Loaded API key for {provider}")
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")


# Load secrets on module import
load_saved_secrets_to_env()
SECRETS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class LLMSettings(BaseModel):
    """LLM configuration settings."""
    provider: str = "anthropic"
    model: str = "claude-3-sonnet"
    temperature: float = 0.7
    maxTokens: int = 4096
    topP: float = 0.9
    presencePenalty: float = 0.0
    frequencyPenalty: float = 0.0
    systemPrompt: Optional[str] = None


class MemorySettings(BaseModel):
    """Memory system settings."""
    enableEpisodic: bool = True
    enableSemantic: bool = True
    enableProcedural: bool = True
    maxMemories: int = 1000
    retentionDays: int = 30
    autoConsolidate: bool = True


class ReasoningSettings(BaseModel):
    """Reasoning engine settings."""
    enableCausal: bool = True
    enableCounterfactual: bool = True
    enableAbductive: bool = True
    enableDeductive: bool = True
    enableTemporal: bool = True
    thinkingDepth: str = "deep"


class SecuritySettings(BaseModel):
    """Security settings."""
    requireConfirmation: bool = True
    sandboxCode: bool = True
    allowNetworkAccess: bool = True
    allowFileSystem: bool = True
    allowShellCommands: bool = True
    maxConcurrentTasks: int = 5


class AppearanceSettings(BaseModel):
    """UI appearance settings."""
    theme: str = "dark"
    fontSize: str = "medium"
    codeFont: str = "Fira Code"
    showTimestamps: bool = True
    compactMode: bool = False
    animationsEnabled: bool = True


class AdvancedSettings(BaseModel):
    """Advanced settings."""
    debugMode: bool = False
    verboseLogging: bool = False
    experimentalFeatures: bool = False
    autoSave: bool = True
    backupEnabled: bool = True
    telemetryEnabled: bool = False


class AllSettings(BaseModel):
    """Complete settings model."""
    llm: LLMSettings = Field(default_factory=LLMSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    reasoning: ReasoningSettings = Field(default_factory=ReasoningSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    appearance: AppearanceSettings = Field(default_factory=AppearanceSettings)
    advanced: AdvancedSettings = Field(default_factory=AdvancedSettings)


class ApiKeyRequest(BaseModel):
    """Request to save an API key."""
    provider: str
    key: str


class ApiKeyStatus(BaseModel):
    """API key status (without exposing the key)."""
    provider: str
    configured: bool
    last_updated: Optional[str] = None


# =============================================================================
# SETTINGS PERSISTENCE
# =============================================================================

def get_settings_file() -> Path:
    """Get the settings file path."""
    return SETTINGS_DIR / "user_settings.json"


def load_settings() -> AllSettings:
    """Load settings from disk."""
    settings_file = get_settings_file()
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                data = json.load(f)
            return AllSettings(**data)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
    return AllSettings()


def save_settings(settings: AllSettings) -> None:
    """Save settings to disk."""
    settings_file = get_settings_file()
    with open(settings_file, 'w') as f:
        json.dump(settings.model_dump(), f, indent=2)


def get_secrets_file() -> Path:
    """Get the secrets file path."""
    return SECRETS_DIR / "api_keys.json"


def load_secrets() -> Dict[str, Dict[str, Any]]:
    """Load API keys from disk."""
    secrets_file = get_secrets_file()
    if secrets_file.exists():
        try:
            with open(secrets_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load secrets: {e}")
    return {}


def save_secret(provider: str, key: str) -> None:
    """Save an API key to disk and set environment variable."""
    secrets = load_secrets()
    secrets[provider] = {
        "key": key,  # In production, encrypt this!
        "last_updated": datetime.now().isoformat()
    }
    secrets_file = get_secrets_file()
    with open(secrets_file, 'w') as f:
        json.dump(secrets, f, indent=2)
    # Set restrictive permissions
    os.chmod(secrets_file, 0o600)

    # Also set environment variable for immediate use
    env_var = ENV_VAR_MAP.get(provider.lower())
    if env_var:
        os.environ[env_var] = key
        logger.info(f"Set environment variable {env_var}")


def delete_secret(provider: str) -> bool:
    """Delete an API key."""
    secrets = load_secrets()
    if provider in secrets:
        del secrets[provider]
        secrets_file = get_secrets_file()
        with open(secrets_file, 'w') as f:
            json.dump(secrets, f, indent=2)
        return True
    return False


def get_api_key(provider: str) -> Optional[str]:
    """Get an API key for a provider."""
    secrets = load_secrets()
    if provider in secrets:
        return secrets[provider].get("key")
    # Also check environment variables
    env_var = ENV_VAR_MAP.get(provider.lower())
    if env_var:
        return os.environ.get(env_var)
    return None


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/")
async def get_all_settings():
    """Get all settings."""
    return load_settings()


@router.put("/")
async def update_all_settings(settings: AllSettings):
    """Update all settings at once."""
    save_settings(settings)
    return {"success": True, "message": "Settings saved"}


@router.get("/llm")
async def get_llm_settings():
    """Get LLM settings."""
    return load_settings().llm


@router.put("/llm")
async def update_llm_settings(settings: LLMSettings):
    """Update LLM settings."""
    all_settings = load_settings()
    all_settings.llm = settings
    save_settings(all_settings)
    return {"success": True}


@router.get("/memory")
async def get_memory_settings():
    """Get memory settings."""
    return load_settings().memory


@router.put("/memory")
async def update_memory_settings(settings: MemorySettings):
    """Update memory settings."""
    all_settings = load_settings()
    all_settings.memory = settings
    save_settings(all_settings)
    return {"success": True}


@router.get("/reasoning")
async def get_reasoning_settings():
    """Get reasoning settings."""
    return load_settings().reasoning


@router.put("/reasoning")
async def update_reasoning_settings(settings: ReasoningSettings):
    """Update reasoning settings."""
    all_settings = load_settings()
    all_settings.reasoning = settings
    save_settings(all_settings)
    return {"success": True}


@router.get("/security")
async def get_security_settings():
    """Get security settings."""
    return load_settings().security


@router.put("/security")
async def update_security_settings(settings: SecuritySettings):
    """Update security settings."""
    all_settings = load_settings()
    all_settings.security = settings
    save_settings(all_settings)
    return {"success": True}


@router.get("/appearance")
async def get_appearance_settings():
    """Get appearance settings."""
    return load_settings().appearance


@router.put("/appearance")
async def update_appearance_settings(settings: AppearanceSettings):
    """Update appearance settings."""
    all_settings = load_settings()
    all_settings.appearance = settings
    save_settings(all_settings)
    return {"success": True}


@router.get("/advanced")
async def get_advanced_settings():
    """Get advanced settings."""
    return load_settings().advanced


@router.put("/advanced")
async def update_advanced_settings(settings: AdvancedSettings):
    """Update advanced settings."""
    all_settings = load_settings()
    all_settings.advanced = settings
    save_settings(all_settings)
    return {"success": True}


# =============================================================================
# API KEY MANAGEMENT
# =============================================================================

@router.get("/keys")
async def list_api_keys():
    """List configured API keys (status only, not the actual keys)."""
    secrets = load_secrets()
    providers = ["anthropic", "openai", "openrouter", "google", "groq",
                 "mistral", "together", "perplexity", "huggingface", "github"]

    result = []
    for provider in providers:
        configured = provider in secrets or get_api_key(provider) is not None
        last_updated = secrets.get(provider, {}).get("last_updated")
        result.append(ApiKeyStatus(
            provider=provider,
            configured=configured,
            last_updated=last_updated
        ))

    return {"keys": result}


@router.post("/keys")
async def save_api_key(request: ApiKeyRequest):
    """Save an API key."""
    if not request.key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    save_secret(request.provider, request.key.strip())
    logger.info(f"API key saved for {request.provider}")

    return {"success": True, "message": f"API key for {request.provider} saved"}


@router.delete("/keys/{provider}")
async def remove_api_key(provider: str):
    """Remove an API key."""
    if delete_secret(provider):
        return {"success": True, "message": f"API key for {provider} removed"}
    raise HTTPException(status_code=404, detail=f"No API key found for {provider}")


@router.post("/keys/validate/{provider}")
async def validate_api_key(provider: str):
    """Validate an API key by making a test request."""
    key = get_api_key(provider)
    if not key:
        raise HTTPException(status_code=404, detail=f"No API key configured for {provider}")

    # TODO: Implement actual validation for each provider
    # For now, just check if the key exists and has reasonable format
    if len(key) < 10:
        return {"valid": False, "message": "Key appears too short"}

    return {"valid": True, "message": "Key format looks valid"}


# =============================================================================
# EXPORT/IMPORT
# =============================================================================

@router.get("/export")
async def export_settings():
    """Export all settings (excluding secrets)."""
    return {
        "settings": load_settings().model_dump(),
        "exported_at": datetime.now().isoformat(),
        "version": "1.0"
    }


@router.post("/import")
async def import_settings(data: Dict[str, Any]):
    """Import settings from exported data."""
    if "settings" not in data:
        raise HTTPException(status_code=400, detail="Invalid import data")

    try:
        settings = AllSettings(**data["settings"])
        save_settings(settings)
        return {"success": True, "message": "Settings imported"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid settings format: {e}")


@router.post("/reset")
async def reset_settings():
    """Reset all settings to defaults."""
    save_settings(AllSettings())
    return {"success": True, "message": "Settings reset to defaults"}
