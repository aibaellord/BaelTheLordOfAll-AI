"""
BAEL - Knowledge Base
Comprehensive domain knowledge, patterns, and best practices.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

KNOWLEDGE_DIR = Path(__file__).parent


class KnowledgeBase:
    """
    Centralized knowledge management system.

    Provides:
    - Design patterns
    - Anti-patterns
    - Domain knowledge
    - Best practices
    - Code snippets
    """

    def __init__(self, knowledge_dir: Optional[str] = None):
        self.knowledge_dir = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
        self._cache: Dict[str, Any] = {}

    def get_pattern(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a design pattern."""
        return self._load_json("patterns", name)

    def get_antipattern(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an anti-pattern."""
        return self._load_json("antipatterns", name)

    def get_domain(self, name: str) -> Optional[Dict[str, Any]]:
        """Get domain knowledge."""
        return self._load_json("domains", name)

    def get_best_practice(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """Get a best practice."""
        return self._load_json(f"practices/{category}", name)

    def list_patterns(self) -> List[str]:
        """List available patterns."""
        patterns_dir = self.knowledge_dir / "patterns"
        if patterns_dir.exists():
            return [f.stem for f in patterns_dir.glob("*.json")]
        return []

    def list_domains(self) -> List[str]:
        """List available domains."""
        domains_dir = self.knowledge_dir / "domains"
        if domains_dir.exists():
            return [f.stem for f in domains_dir.glob("*.json")]
        return []

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        results = []
        query_lower = query.lower()

        for category in ["patterns", "antipatterns", "domains"]:
            category_dir = self.knowledge_dir / category
            if category_dir.exists():
                for file in category_dir.glob("*.json"):
                    data = self._load_json(category, file.stem)
                    if data:
                        name = data.get("name", "").lower()
                        desc = data.get("description", "").lower()
                        if query_lower in name or query_lower in desc:
                            results.append({
                                "category": category,
                                "name": file.stem,
                                "data": data
                            })

        return results

    def _load_json(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """Load a JSON knowledge file."""
        cache_key = f"{category}:{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        file_path = self.knowledge_dir / category / f"{name}.json"
        if file_path.exists():
            data = json.loads(file_path.read_text())
            self._cache[cache_key] = data
            return data

        return None


# Global instance
knowledge = KnowledgeBase()

__all__ = ["KnowledgeBase", "knowledge"]
