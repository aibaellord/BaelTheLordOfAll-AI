"""
BAEL - Persona System
Dynamic persona management for specialized agent behaviors.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.Personas")


class PersonaRole(Enum):
    """Predefined persona roles."""
    ORCHESTRATOR = "orchestrator"
    ARCHITECT = "architect"
    CODER = "coder"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    DEBUGGER = "debugger"
    TEACHER = "teacher"
    WRITER = "writer"
    STRATEGIST = "strategist"


@dataclass
class PersonaConfig:
    """Configuration for a persona."""
    name: str
    role: PersonaRole
    description: str
    system_prompt: str
    capabilities: List[str] = field(default_factory=list)
    temperature: float = 0.7
    preferred_model: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role.value,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "capabilities": self.capabilities,
            "temperature": self.temperature,
            "preferred_model": self.preferred_model,
            "tools": self.tools,
            "constraints": self.constraints
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonaConfig":
        return cls(
            name=data["name"],
            role=PersonaRole(data["role"]),
            description=data["description"],
            system_prompt=data["system_prompt"],
            capabilities=data.get("capabilities", []),
            temperature=data.get("temperature", 0.7),
            preferred_model=data.get("preferred_model"),
            tools=data.get("tools", []),
            constraints=data.get("constraints", [])
        )


class PersonaLoader:
    """Loads persona configurations from files."""

    def __init__(self, personas_dir: Optional[str] = None):
        if personas_dir:
            self.personas_dir = Path(personas_dir)
        else:
            self.personas_dir = Path(__file__).parent.parent.parent / "personas"

        self._personas: Dict[str, PersonaConfig] = {}
        self._load_builtin_personas()

    def _load_builtin_personas(self) -> None:
        """Load built-in persona configurations."""
        builtins = [
            PersonaConfig(
                name="Orchestrator",
                role=PersonaRole.ORCHESTRATOR,
                description="Master coordinator for complex multi-step tasks",
                system_prompt="You are BAEL's Orchestrator, the master coordinator...",
                capabilities=["task_decomposition", "delegation", "synthesis"],
                temperature=0.5
            ),
            PersonaConfig(
                name="Architect",
                role=PersonaRole.ARCHITECT,
                description="System design and architecture specialist",
                system_prompt="You are BAEL's Architect, focused on system design...",
                capabilities=["design", "architecture", "patterns"],
                temperature=0.6
            ),
            PersonaConfig(
                name="Coder",
                role=PersonaRole.CODER,
                description="Code implementation specialist",
                system_prompt="You are BAEL's Coder, focused on implementation...",
                capabilities=["coding", "debugging", "optimization"],
                temperature=0.3
            ),
            PersonaConfig(
                name="Researcher",
                role=PersonaRole.RESEARCHER,
                description="Research and information gathering specialist",
                system_prompt="You are BAEL's Researcher, focused on discovery...",
                capabilities=["research", "analysis", "synthesis"],
                temperature=0.8
            ),
            PersonaConfig(
                name="Analyst",
                role=PersonaRole.ANALYST,
                description="Data analysis and problem solving specialist",
                system_prompt="You are BAEL's Analyst, focused on deep analysis...",
                capabilities=["analysis", "metrics", "insights"],
                temperature=0.5
            ),
            PersonaConfig(
                name="Reviewer",
                role=PersonaRole.REVIEWER,
                description="Code and design review specialist",
                system_prompt="You are BAEL's Reviewer, focused on quality...",
                capabilities=["review", "feedback", "standards"],
                temperature=0.4
            ),
            PersonaConfig(
                name="Debugger",
                role=PersonaRole.DEBUGGER,
                description="Bug diagnosis and resolution specialist",
                system_prompt="You are BAEL's Debugger, focused on finding issues...",
                capabilities=["debugging", "root_cause", "fixing"],
                temperature=0.3
            ),
            PersonaConfig(
                name="Teacher",
                role=PersonaRole.TEACHER,
                description="Education and explanation specialist",
                system_prompt="You are BAEL's Teacher, focused on clarity...",
                capabilities=["explanation", "education", "documentation"],
                temperature=0.7
            )
        ]

        for persona in builtins:
            self._personas[persona.role.value] = persona

    def load_from_file(self, filepath: str) -> Optional[PersonaConfig]:
        """Load a persona from a JSON/YAML file."""
        path = Path(filepath)
        if not path.exists():
            logger.warning(f"Persona file not found: {filepath}")
            return None

        try:
            with open(path) as f:
                data = json.load(f)
            persona = PersonaConfig.from_dict(data)
            self._personas[persona.role.value] = persona
            return persona
        except Exception as e:
            logger.error(f"Failed to load persona: {e}")
            return None

    def get(self, role: str) -> Optional[PersonaConfig]:
        """Get a persona by role name."""
        return self._personas.get(role)

    def list_all(self) -> List[str]:
        """List all available personas."""
        return list(self._personas.keys())

    def get_all(self) -> Dict[str, PersonaConfig]:
        """Get all personas."""
        return self._personas.copy()


# Global loader instance
loader = PersonaLoader()


__all__ = [
    "PersonaRole",
    "PersonaConfig",
    "PersonaLoader",
    "loader"
]
