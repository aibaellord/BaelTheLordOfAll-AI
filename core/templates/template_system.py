#!/usr/bin/env python3
"""
BAEL - Agent Template System
Create and manage agent templates for rapid deployment.

Features:
- Template definitions
- Variable substitution
- Template inheritance
- Template validation
- Export formats (YAML, JSON, Python)
"""

import asyncio
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class TemplateType(Enum):
    """Types of templates."""
    AGENT = "agent"
    PERSONA = "persona"
    WORKFLOW = "workflow"
    TOOL = "tool"
    PROMPT = "prompt"
    CONFIG = "config"


class VariableType(Enum):
    """Template variable types."""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    SECRET = "secret"


@dataclass
class Variable:
    """Template variable definition."""
    name: str
    type: VariableType
    description: str = ""
    default: Any = None
    required: bool = True
    validation: Optional[str] = None  # Regex pattern
    choices: List[Any] = field(default_factory=list)

    def validate(self, value: Any) -> bool:
        """Validate variable value."""
        if value is None and self.required:
            return False

        if self.type == VariableType.STRING:
            if not isinstance(value, str):
                return False
            if self.validation:
                if not re.match(self.validation, value):
                    return False

        elif self.type == VariableType.NUMBER:
            if not isinstance(value, (int, float)):
                return False

        elif self.type == VariableType.BOOLEAN:
            if not isinstance(value, bool):
                return False

        elif self.type == VariableType.LIST:
            if not isinstance(value, list):
                return False

        elif self.type == VariableType.DICT:
            if not isinstance(value, dict):
                return False

        if self.choices and value not in self.choices:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "default": self.default,
            "required": self.required,
            "validation": self.validation,
            "choices": self.choices
        }


@dataclass
class TemplateSection:
    """Section of a template."""
    name: str
    content: str
    order: int = 0
    conditional: Optional[str] = None  # Condition for inclusion

    def render(self, variables: Dict[str, Any]) -> str:
        """Render section with variables."""
        # Check condition
        if self.conditional:
            try:
                if not eval(self.conditional, {"vars": variables}):
                    return ""
            except:
                pass

        return self._substitute(self.content, variables)

    def _substitute(self, text: str, variables: Dict[str, Any]) -> str:
        """Substitute variables in text."""
        # Pattern: {{ variable_name }} or {{ variable_name | default_value }}
        pattern = r'\{\{\s*(\w+)(?:\s*\|\s*([^}]+))?\s*\}\}'

        def replace(match):
            var_name = match.group(1)
            default = match.group(2)

            if var_name in variables:
                value = variables[var_name]
                if isinstance(value, (list, dict)):
                    return json.dumps(value)
                return str(value)
            elif default:
                return default.strip()
            else:
                return match.group(0)  # Keep original

        return re.sub(pattern, replace, text)


@dataclass
class Template:
    """Template definition."""
    id: str
    name: str
    type: TemplateType
    description: str = ""
    version: str = "1.0.0"
    author: str = ""

    # Template structure
    variables: List[Variable] = field(default_factory=list)
    sections: List[TemplateSection] = field(default_factory=list)

    # Inheritance
    extends: Optional[str] = None  # Parent template ID

    # Metadata
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def get_variable(self, name: str) -> Optional[Variable]:
        """Get variable by name."""
        for var in self.variables:
            if var.name == name:
                return var
        return None

    def validate_variables(self, values: Dict[str, Any]) -> List[str]:
        """Validate variable values."""
        errors = []

        for var in self.variables:
            if var.name in values:
                if not var.validate(values[var.name]):
                    errors.append(f"Invalid value for {var.name}")
            elif var.required and var.default is None:
                errors.append(f"Missing required variable: {var.name}")

        return errors

    def get_defaults(self) -> Dict[str, Any]:
        """Get default variable values."""
        return {
            var.name: var.default
            for var in self.variables
            if var.default is not None
        }

    def render(self, variables: Dict[str, Any]) -> str:
        """Render template with variables."""
        # Merge with defaults
        final_vars = self.get_defaults()
        final_vars.update(variables)

        # Validate
        errors = self.validate_variables(final_vars)
        if errors:
            raise ValueError(f"Validation errors: {errors}")

        # Sort and render sections
        sorted_sections = sorted(self.sections, key=lambda s: s.order)
        rendered = []

        for section in sorted_sections:
            content = section.render(final_vars)
            if content:
                rendered.append(content)

        return "\n\n".join(rendered)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "variables": [v.to_dict() for v in self.variables],
            "sections": [
                {"name": s.name, "content": s.content, "order": s.order, "conditional": s.conditional}
                for s in self.sections
            ],
            "extends": self.extends,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        return cls(
            id=data["id"],
            name=data["name"],
            type=TemplateType(data["type"]),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            variables=[
                Variable(
                    name=v["name"],
                    type=VariableType(v["type"]),
                    description=v.get("description", ""),
                    default=v.get("default"),
                    required=v.get("required", True),
                    validation=v.get("validation"),
                    choices=v.get("choices", [])
                )
                for v in data.get("variables", [])
            ],
            sections=[
                TemplateSection(
                    name=s["name"],
                    content=s["content"],
                    order=s.get("order", 0),
                    conditional=s.get("conditional")
                )
                for s in data.get("sections", [])
            ],
            extends=data.get("extends"),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        )


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

class TemplateRegistry:
    """Registry for templates."""

    def __init__(self, storage_dir: str = None):
        self.templates: Dict[str, Template] = {}
        self.storage_dir = Path(storage_dir) if storage_dir else None

        if self.storage_dir:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_templates()

    def _load_templates(self) -> None:
        """Load templates from storage."""
        if not self.storage_dir:
            return

        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                template = Template.from_dict(data)
                self.templates[template.id] = template
            except Exception as e:
                logger.error(f"Failed to load template {file}: {e}")

    def register(self, template: Template) -> None:
        """Register a template."""
        self.templates[template.id] = template

        if self.storage_dir:
            self._save_template(template)

        logger.info(f"Registered template: {template.name}")

    def _save_template(self, template: Template) -> None:
        """Save template to storage."""
        if not self.storage_dir:
            return

        file = self.storage_dir / f"{template.id}.json"
        with open(file, 'w') as f:
            json.dump(template.to_dict(), f, indent=2)

    def get(self, template_id: str) -> Optional[Template]:
        """Get template by ID."""
        return self.templates.get(template_id)

    def find(
        self,
        type: TemplateType = None,
        tags: List[str] = None,
        search: str = None
    ) -> List[Template]:
        """Find templates matching criteria."""
        results = list(self.templates.values())

        if type:
            results = [t for t in results if t.type == type]

        if tags:
            results = [
                t for t in results
                if all(tag in t.tags for tag in tags)
            ]

        if search:
            search_lower = search.lower()
            results = [
                t for t in results
                if search_lower in t.name.lower() or search_lower in t.description.lower()
            ]

        return results

    def delete(self, template_id: str) -> bool:
        """Delete template."""
        if template_id in self.templates:
            del self.templates[template_id]

            if self.storage_dir:
                file = self.storage_dir / f"{template_id}.json"
                if file.exists():
                    file.unlink()

            return True
        return False

    def resolve_inheritance(self, template: Template) -> Template:
        """Resolve template inheritance."""
        if not template.extends:
            return template

        parent = self.get(template.extends)
        if not parent:
            raise ValueError(f"Parent template not found: {template.extends}")

        # Recursively resolve
        parent = self.resolve_inheritance(parent)

        # Merge
        merged_vars = list(parent.variables)
        for var in template.variables:
            existing = next((v for v in merged_vars if v.name == var.name), None)
            if existing:
                merged_vars.remove(existing)
            merged_vars.append(var)

        merged_sections = list(parent.sections)
        for section in template.sections:
            existing = next((s for s in merged_sections if s.name == section.name), None)
            if existing:
                merged_sections.remove(existing)
            merged_sections.append(section)

        return Template(
            id=template.id,
            name=template.name,
            type=template.type,
            description=template.description,
            version=template.version,
            author=template.author,
            variables=merged_vars,
            sections=merged_sections,
            tags=list(set(parent.tags + template.tags))
        )


# =============================================================================
# TEMPLATE BUILDER
# =============================================================================

class TemplateBuilder:
    """Fluent builder for templates."""

    def __init__(self, id: str, name: str, type: TemplateType):
        self._template = Template(
            id=id,
            name=name,
            type=type
        )

    def description(self, desc: str) -> "TemplateBuilder":
        self._template.description = desc
        return self

    def version(self, version: str) -> "TemplateBuilder":
        self._template.version = version
        return self

    def author(self, author: str) -> "TemplateBuilder":
        self._template.author = author
        return self

    def extends(self, parent_id: str) -> "TemplateBuilder":
        self._template.extends = parent_id
        return self

    def variable(
        self,
        name: str,
        type: VariableType,
        description: str = "",
        default: Any = None,
        required: bool = True,
        validation: str = None,
        choices: List[Any] = None
    ) -> "TemplateBuilder":
        self._template.variables.append(Variable(
            name=name,
            type=type,
            description=description,
            default=default,
            required=required,
            validation=validation,
            choices=choices or []
        ))
        return self

    def section(
        self,
        name: str,
        content: str,
        order: int = 0,
        conditional: str = None
    ) -> "TemplateBuilder":
        self._template.sections.append(TemplateSection(
            name=name,
            content=content,
            order=order,
            conditional=conditional
        ))
        return self

    def tags(self, *tags: str) -> "TemplateBuilder":
        self._template.tags.extend(tags)
        return self

    def build(self) -> Template:
        return self._template


# =============================================================================
# BUILTIN TEMPLATES
# =============================================================================

def create_builtin_templates() -> List[Template]:
    """Create built-in templates."""
    templates = []

    # Basic agent template
    agent_template = (
        TemplateBuilder("basic-agent", "Basic Agent", TemplateType.AGENT)
        .description("A basic agent template with common functionality")
        .variable("name", VariableType.STRING, "Agent name")
        .variable("description", VariableType.STRING, "Agent description", default="")
        .variable("model", VariableType.STRING, "LLM model to use", default="gpt-4")
        .variable("temperature", VariableType.NUMBER, "Temperature setting", default=0.7)
        .variable("tools", VariableType.LIST, "List of tools", default=[])
        .section("header", """# {{ name }}
{{ description }}""", order=0)
        .section("config", """## Configuration
- Model: {{ model }}
- Temperature: {{ temperature }}""", order=1)
        .section("tools", """## Tools
{{ tools }}""", order=2, conditional="vars.get('tools')")
        .tags("agent", "basic")
        .build()
    )
    templates.append(agent_template)

    # Persona template
    persona_template = (
        TemplateBuilder("basic-persona", "Basic Persona", TemplateType.PERSONA)
        .description("Template for creating agent personas")
        .variable("name", VariableType.STRING, "Persona name")
        .variable("role", VariableType.STRING, "Primary role")
        .variable("personality", VariableType.STRING, "Personality traits", default="Professional and helpful")
        .variable("expertise", VariableType.LIST, "Areas of expertise", default=[])
        .variable("communication_style", VariableType.STRING, "How the persona communicates", default="Clear and concise")
        .section("identity", """You are {{ name }}, a {{ role }}.

Personality: {{ personality }}
Communication Style: {{ communication_style }}""", order=0)
        .section("expertise", """Your areas of expertise include:
{{ expertise }}""", order=1, conditional="vars.get('expertise')")
        .tags("persona")
        .build()
    )
    templates.append(persona_template)

    # Workflow template
    workflow_template = (
        TemplateBuilder("basic-workflow", "Basic Workflow", TemplateType.WORKFLOW)
        .description("Template for multi-step workflows")
        .variable("name", VariableType.STRING, "Workflow name")
        .variable("description", VariableType.STRING, "Workflow description")
        .variable("steps", VariableType.LIST, "Workflow steps", default=[])
        .variable("timeout", VariableType.NUMBER, "Timeout in seconds", default=300)
        .section("metadata", """name: {{ name }}
description: {{ description }}
timeout: {{ timeout }}""", order=0)
        .section("steps", """steps:
{{ steps }}""", order=1)
        .tags("workflow")
        .build()
    )
    templates.append(workflow_template)

    # Prompt template
    prompt_template = (
        TemplateBuilder("basic-prompt", "Basic Prompt", TemplateType.PROMPT)
        .description("Template for LLM prompts")
        .variable("system_message", VariableType.STRING, "System message", default="You are a helpful assistant.")
        .variable("context", VariableType.STRING, "Additional context", default="")
        .variable("instructions", VariableType.STRING, "Specific instructions")
        .variable("output_format", VariableType.STRING, "Expected output format", default="")
        .section("system", """{{ system_message }}""", order=0)
        .section("context", """Context:
{{ context }}""", order=1, conditional="vars.get('context')")
        .section("instructions", """Instructions:
{{ instructions }}""", order=2)
        .section("format", """Please format your response as:
{{ output_format }}""", order=3, conditional="vars.get('output_format')")
        .tags("prompt")
        .build()
    )
    templates.append(prompt_template)

    return templates


# =============================================================================
# TEMPLATE ENGINE
# =============================================================================

class TemplateEngine:
    """Main template engine."""

    def __init__(self, storage_dir: str = None):
        self.registry = TemplateRegistry(storage_dir)

        # Register builtins
        for template in create_builtin_templates():
            self.registry.register(template)

    def create_from_template(
        self,
        template_id: str,
        variables: Dict[str, Any]
    ) -> str:
        """Create content from template."""
        template = self.registry.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Resolve inheritance
        resolved = self.registry.resolve_inheritance(template)

        return resolved.render(variables)

    def list_templates(
        self,
        type: TemplateType = None
    ) -> List[Dict[str, Any]]:
        """List available templates."""
        templates = self.registry.find(type=type)
        return [
            {
                "id": t.id,
                "name": t.name,
                "type": t.type.value,
                "description": t.description,
                "variables": [v.name for v in t.variables]
            }
            for t in templates
        ]

    def get_template_schema(self, template_id: str) -> Dict[str, Any]:
        """Get JSON schema for template variables."""
        template = self.registry.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        properties = {}
        required = []

        for var in template.variables:
            prop = {
                "description": var.description
            }

            if var.type == VariableType.STRING:
                prop["type"] = "string"
            elif var.type == VariableType.NUMBER:
                prop["type"] = "number"
            elif var.type == VariableType.BOOLEAN:
                prop["type"] = "boolean"
            elif var.type == VariableType.LIST:
                prop["type"] = "array"
            elif var.type == VariableType.DICT:
                prop["type"] = "object"
            elif var.type == VariableType.SECRET:
                prop["type"] = "string"
                prop["format"] = "password"

            if var.default is not None:
                prop["default"] = var.default

            if var.choices:
                prop["enum"] = var.choices

            if var.validation:
                prop["pattern"] = var.validation

            properties[var.name] = prop

            if var.required and var.default is None:
                required.append(var.name)

        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": properties,
            "required": required
        }


# =============================================================================
# MAIN
# =============================================================================

def demo():
    """Demo template system."""
    engine = TemplateEngine()

    # List templates
    print("Available templates:")
    for t in engine.list_templates():
        print(f"  - {t['id']}: {t['name']} ({t['type']})")
        print(f"    Variables: {t['variables']}")

    print()

    # Create from agent template
    print("Creating agent from template:")
    agent = engine.create_from_template("basic-agent", {
        "name": "ResearchBot",
        "description": "An agent specialized in research tasks",
        "model": "claude-3-opus",
        "temperature": 0.3,
        "tools": ["web_search", "document_reader", "summarizer"]
    })
    print(agent)

    print()

    # Create persona
    print("Creating persona from template:")
    persona = engine.create_from_template("basic-persona", {
        "name": "Dr. Watson",
        "role": "Medical Research Assistant",
        "personality": "Thorough, empathetic, and scientifically rigorous",
        "expertise": ["Medical literature", "Clinical trials", "Drug interactions"],
        "communication_style": "Professional but approachable"
    })
    print(persona)

    print()

    # Get schema
    print("Template schema for basic-prompt:")
    schema = engine.get_template_schema("basic-prompt")
    print(json.dumps(schema, indent=2))

    # Custom template
    print("\nCreating custom template:")
    custom = (
        TemplateBuilder("code-review", "Code Review", TemplateType.PROMPT)
        .description("Template for code review prompts")
        .variable("language", VariableType.STRING, "Programming language")
        .variable("code", VariableType.STRING, "Code to review")
        .variable("focus_areas", VariableType.LIST, "Areas to focus on", default=["bugs", "style", "performance"])
        .section("prompt", """Review the following {{ language }} code:

```{{ language }}
{{ code }}
```

Focus on:
{{ focus_areas }}

Provide specific, actionable feedback.""")
        .build()
    )
    engine.registry.register(custom)

    review = engine.create_from_template("code-review", {
        "language": "python",
        "code": "def add(a, b): return a+b",
        "focus_areas": ["type hints", "documentation", "error handling"]
    })
    print(review)


if __name__ == "__main__":
    demo()
