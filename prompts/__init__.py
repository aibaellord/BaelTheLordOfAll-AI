"""
BAEL - Prompt Library
Comprehensive collection of system prompts, templates, and chains.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Base path for prompts
PROMPTS_DIR = Path(__file__).parent


class PromptLibrary:
    """
    Centralized prompt management system.

    Provides:
    - System prompts for personas
    - Reusable templates
    - Multi-step prompt chains
    - Variable substitution
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir else PROMPTS_DIR
        self._cache: Dict[str, str] = {}

    def get_system_prompt(self, persona: str) -> Optional[str]:
        """Get system prompt for a persona."""
        cache_key = f"system:{persona}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_path = self.prompts_dir / "system" / f"{persona}.txt"
        if prompt_path.exists():
            content = prompt_path.read_text()
            self._cache[cache_key] = content
            return content

        return None

    def get_template(self, name: str) -> Optional[str]:
        """Get a prompt template."""
        cache_key = f"template:{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_path = self.prompts_dir / "templates" / f"{name}.txt"
        if prompt_path.exists():
            content = prompt_path.read_text()
            self._cache[cache_key] = content
            return content

        return None

    def get_chain(self, name: str) -> Optional[List[Dict[str, Any]]]:
        """Get a prompt chain definition."""
        chain_path = self.prompts_dir / "chains" / f"{name}.json"
        if chain_path.exists():
            return json.loads(chain_path.read_text())
        return None

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """Render a template with variables."""
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def list_personas(self) -> List[str]:
        """List available personas."""
        system_dir = self.prompts_dir / "system"
        if system_dir.exists():
            return [f.stem for f in system_dir.glob("*.txt")]
        return []

    def list_templates(self) -> List[str]:
        """List available templates."""
        templates_dir = self.prompts_dir / "templates"
        if templates_dir.exists():
            return [f.stem for f in templates_dir.glob("*.txt")]
        return []

    def list_chains(self) -> List[str]:
        """List available chains."""
        chains_dir = self.prompts_dir / "chains"
        if chains_dir.exists():
            return [f.stem for f in chains_dir.glob("*.json")]
        return []


# Global instance
library = PromptLibrary()

__all__ = ["PromptLibrary", "library"]
