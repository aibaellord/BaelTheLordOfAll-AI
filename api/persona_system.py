"""
Dynamic persona switching and context adaptation system.
Enables real-time persona selection, customization, and context-aware adaptation.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.PersonaSystem")


@dataclass
class PersonaTemplate:
    """Base persona template."""
    id: str
    name: str
    role: str
    description: str
    icon: str
    system_prompt: str
    capabilities: List[str]
    constraints: Optional[List[str]] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    metadata: Dict[str, Any] = None


class PersonaContext:
    """Current persona context and state."""

    def __init__(self, persona: PersonaTemplate):
        self.persona = persona
        self.created_at = datetime.utcnow()
        self.usage_count = 0
        self.performance_metrics: Dict[str, float] = {}
        self.adaptation_history: List[Dict[str, Any]] = []

    def record_usage(self, success: bool = True, metrics: Optional[Dict[str, float]] = None):
        """Record usage of this persona."""
        self.usage_count += 1
        if metrics:
            for key, value in metrics.items():
                if key not in self.performance_metrics:
                    self.performance_metrics[key] = 0
                self.performance_metrics[key] = (self.performance_metrics[key] + value) / 2
        logger.debug(f"Persona {self.persona.name} usage recorded: {self.usage_count}")

    def adapt_for_context(self, context: Dict[str, Any]):
        """Adapt persona parameters based on context."""
        adaptation = {
            "timestamp": datetime.utcnow().isoformat(),
            "context": context,
            "adjustments": {}
        }

        # Adjust temperature based on task type
        if context.get("task_type") == "creative":
            self.persona.temperature = min(1.5, self.persona.temperature + 0.2)
            adaptation["adjustments"]["temperature"] = self.persona.temperature
        elif context.get("task_type") == "analytical":
            self.persona.temperature = max(0.3, self.persona.temperature - 0.2)
            adaptation["adjustments"]["temperature"] = self.persona.temperature

        # Adjust max tokens based on task complexity
        if context.get("complexity") == "high":
            self.persona.max_tokens = min(4096, self.persona.max_tokens + 1024)
            adaptation["adjustments"]["max_tokens"] = self.persona.max_tokens

        self.adaptation_history.append(adaptation)
        logger.info(f"Persona {self.persona.name} adapted for context: {context}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.persona.id,
            "name": self.persona.name,
            "role": self.persona.role,
            "description": self.persona.description,
            "icon": self.persona.icon,
            "capabilities": self.persona.capabilities,
            "current_temperature": self.persona.temperature,
            "current_max_tokens": self.persona.max_tokens,
            "usage_count": self.usage_count,
            "performance_metrics": self.performance_metrics,
            "active_since": self.created_at.isoformat()
        }


class PersonaManager:
    """Manages persona switching and adaptation."""

    def __init__(self):
        self.personas: Dict[str, PersonaTemplate] = {}
        self.current_context: Optional[PersonaContext] = None
        self.history: List[PersonaContext] = []
        self._initialize_default_personas()

    def _initialize_default_personas(self):
        """Initialize default personas."""
        personas = [
            PersonaTemplate(
                id="architect",
                name="Architect Prime",
                role="System Design",
                description="Expert in system architecture, design patterns, and scalability",
                icon="🏛️",
                system_prompt="You are Architect Prime, a master of system design and architecture. You excel at analyzing complex systems, designing scalable solutions, and providing architectural guidance.",
                capabilities=["system_design", "architecture_review", "performance_optimization", "scalability_planning"],
                temperature=0.6,
                max_tokens=3000
            ),
            PersonaTemplate(
                id="coder",
                name="Code Master",
                role="Development",
                description="Expert developer proficient in multiple languages and frameworks",
                icon="💻",
                system_prompt="You are Code Master, a world-class software developer. You excel at writing clean, efficient code, debugging complex issues, and implementing features across all languages and frameworks.",
                capabilities=["code_writing", "debugging", "code_review", "testing", "refactoring"],
                temperature=0.5,
                max_tokens=3000
            ),
            PersonaTemplate(
                id="security",
                name="Security Sentinel",
                role="Security Analysis",
                description="Expert in security, vulnerability assessment, and compliance",
                icon="🔒",
                system_prompt="You are Security Sentinel, a cybersecurity expert. You excel at identifying vulnerabilities, assessing threats, ensuring compliance, and implementing security best practices.",
                capabilities=["vulnerability_assessment", "threat_analysis", "compliance_review", "security_hardening"],
                temperature=0.4,
                max_tokens=2500
            ),
            PersonaTemplate(
                id="qa",
                name="QA Perfectionist",
                role="Quality Assurance",
                description="Expert in testing, quality assurance, and quality metrics",
                icon="🧪",
                system_prompt="You are QA Perfectionist, a quality assurance expert. You excel at designing comprehensive test strategies, identifying edge cases, ensuring quality metrics, and preventing bugs.",
                capabilities=["test_strategy", "test_design", "quality_metrics", "bug_detection"],
                temperature=0.5,
                max_tokens=2500
            ),
            PersonaTemplate(
                id="researcher",
                name="Research Oracle",
                role="Deep Research",
                description="Expert researcher and analyst for complex topics",
                icon="🔬",
                system_prompt="You are Research Oracle, a deep research expert. You excel at investigating complex topics, synthesizing information, identifying patterns, and providing comprehensive analysis.",
                capabilities=["research", "analysis", "synthesis", "pattern_recognition"],
                temperature=0.7,
                max_tokens=4096
            ),
            PersonaTemplate(
                id="devops",
                name="DevOps Commander",
                role="Infrastructure",
                description="Expert in infrastructure, deployment, and DevOps practices",
                icon="⚙️",
                system_prompt="You are DevOps Commander, a DevOps and infrastructure expert. You excel at designing scalable infrastructure, automating deployments, and ensuring system reliability.",
                capabilities=["infrastructure", "deployment", "automation", "monitoring"],
                temperature=0.5,
                max_tokens=2800
            )
        ]

        for persona in personas:
            self.personas[persona.id] = persona

        logger.info(f"Initialized {len(personas)} default personas")

    def list_personas(self) -> List[Dict[str, Any]]:
        """List all available personas."""
        return [
            {
                "id": p.id,
                "name": p.name,
                "role": p.role,
                "description": p.description,
                "icon": p.icon,
                "capabilities": p.capabilities
            }
            for p in self.personas.values()
        ]

    def switch_to_persona(self, persona_id: str, context: Optional[Dict[str, Any]] = None) -> PersonaContext:
        """Switch to a specific persona."""
        if persona_id not in self.personas:
            logger.error(f"Persona {persona_id} not found")
            raise ValueError(f"Persona {persona_id} not found")

        # Save current context to history
        if self.current_context:
            self.history.append(self.current_context)

        # Create and set new context
        persona = self.personas[persona_id]
        self.current_context = PersonaContext(persona)

        # Adapt if context provided
        if context:
            self.current_context.adapt_for_context(context)

        logger.info(f"Switched to persona: {persona.name} (ID: {persona_id})")
        return self.current_context

    def get_current_persona(self) -> Optional[PersonaContext]:
        """Get current active persona."""
        return self.current_context

    def get_persona_system_prompt(self) -> str:
        """Get system prompt for current persona."""
        if not self.current_context:
            return "You are BAEL, the Lord of All AI Agents."
        return self.current_context.persona.system_prompt

    def get_persona_config(self) -> Dict[str, Any]:
        """Get configuration for current persona."""
        if not self.current_context:
            return {
                "temperature": 0.7,
                "max_tokens": 2048
            }

        return {
            "temperature": self.current_context.persona.temperature,
            "max_tokens": self.current_context.persona.max_tokens,
            "system_prompt": self.current_context.persona.system_prompt
        }

    def add_custom_persona(self, persona: PersonaTemplate) -> bool:
        """Add a custom persona."""
        if persona.id in self.personas:
            logger.warning(f"Persona {persona.id} already exists, skipping")
            return False

        self.personas[persona.id] = persona
        logger.info(f"Added custom persona: {persona.name} (ID: {persona.id})")
        return True

    def get_history(self) -> List[Dict[str, Any]]:
        """Get persona switching history."""
        return [
            {
                "persona": ctx.persona.name,
                "usage_count": ctx.usage_count,
                "performance_metrics": ctx.performance_metrics,
                "active_since": ctx.created_at.isoformat()
            }
            for ctx in self.history
        ]

    def export_personas(self) -> str:
        """Export all personas as JSON."""
        personas_data = []
        for persona in self.personas.values():
            personas_data.append({
                "id": persona.id,
                "name": persona.name,
                "role": persona.role,
                "description": persona.description,
                "icon": persona.icon,
                "system_prompt": persona.system_prompt,
                "capabilities": persona.capabilities,
                "constraints": persona.constraints,
                "temperature": persona.temperature,
                "max_tokens": persona.max_tokens
            })
        return json.dumps(personas_data, indent=2)


# Global persona manager instance
persona_manager = PersonaManager()
