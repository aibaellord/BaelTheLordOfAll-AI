"""
BAEL - Persona Loader
Loads and manages persona definitions for the BAEL system.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .definitions import PERSONAS

logger = logging.getLogger(__name__)


@dataclass
class Persona:
    """Represents a loaded persona."""

    name: str
    role: str
    description: str
    system_prompt: str
    capabilities: List[str]
    temperature: float
    preferred_model: str
    tools: List[str]
    constraints: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert persona to dictionary."""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "capabilities": self.capabilities,
            "temperature": self.temperature,
            "preferred_model": self.preferred_model,
            "tools": self.tools,
            "constraints": self.constraints,
        }


class PersonaLoader:
    """Loads persona definitions from various sources."""

    def __init__(self, personas_dir: Optional[Path] = None):
        self.personas_dir = personas_dir or Path(__file__).parent
        self._cache: Dict[str, Persona] = {}

    async def load_all(self) -> Dict[str, Persona]:
        """Load all persona definitions."""
        personas = {}

        # Load built-in personas from definitions.py
        for role, config in PERSONAS.items():
            try:
                persona = self._create_persona(config)
                personas[role] = persona
                self._cache[role] = persona
            except Exception as e:
                logger.warning(f"Failed to load persona {role}: {e}")

        logger.info(f"Loaded {len(personas)} personas")
        return personas

    def _create_persona(self, config: Dict[str, Any]) -> Persona:
        """Create a Persona object from configuration."""
        return Persona(
            name=config.get("name", "Unknown"),
            role=config.get("role", "general"),
            description=config.get("description", ""),
            system_prompt=config.get("system_prompt", ""),
            capabilities=config.get("capabilities", []),
            temperature=config.get("temperature", 0.7),
            preferred_model=config.get("preferred_model", "claude-3-sonnet"),
            tools=config.get("tools", []),
            constraints=config.get("constraints", []),
        )

    def get(self, role: str) -> Optional[Persona]:
        """Get a persona by role."""
        return self._cache.get(role)

    def list_roles(self) -> List[str]:
        """List all available roles."""
        return list(self._cache.keys())
