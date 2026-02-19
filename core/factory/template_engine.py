"""
BAEL Template Engine
=====================

Engine template management and processing.
Provides reusable patterns for engine generation.

Features:
- Template registration
- Variable substitution
- Conditional sections
- Template inheritance
- Template validation
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern, Set

logger = logging.getLogger(__name__)


class TemplateCategory(Enum):
    """Template categories."""
    ENGINE = "engine"
    SERVICE = "service"
    INTEGRATION = "integration"
    UTILITY = "utility"
    TEST = "test"
    DOCUMENTATION = "documentation"


class VariableType(Enum):
    """Template variable types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    CODE = "code"


@dataclass
class TemplateVariable:
    """A template variable definition."""
    name: str
    type: VariableType = VariableType.STRING
    description: str = ""

    # Constraints
    required: bool = True
    default: Any = None
    pattern: Optional[str] = None
    choices: List[Any] = field(default_factory=list)

    # Transformations
    transform: Optional[str] = None  # upper, lower, title, camel, snake

    def validate(self, value: Any) -> bool:
        """Validate a value against this variable."""
        if value is None:
            return not self.required

        if self.choices and value not in self.choices:
            return False

        if self.pattern:
            if not re.match(self.pattern, str(value)):
                return False

        return True

    def apply_transform(self, value: str) -> str:
        """Apply transformation to value."""
        if not self.transform:
            return value

        if self.transform == "upper":
            return value.upper()
        elif self.transform == "lower":
            return value.lower()
        elif self.transform == "title":
            return value.title()
        elif self.transform == "camel":
            words = value.replace("-", " ").replace("_", " ").split()
            return words[0].lower() + "".join(w.capitalize() for w in words[1:])
        elif self.transform == "snake":
            return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
        elif self.transform == "pascal":
            words = value.replace("-", " ").replace("_", " ").split()
            return "".join(w.capitalize() for w in words)

        return value


@dataclass
class TemplateSection:
    """A conditional section in a template."""
    name: str
    content: str
    condition: str  # Variable name or expression
    is_inverted: bool = False  # If true, show when condition is False


@dataclass
class EngineTemplate:
    """An engine template."""
    id: str
    name: str
    description: str = ""

    # Classification
    category: TemplateCategory = TemplateCategory.ENGINE

    # Content
    content: str = ""
    sections: Dict[str, TemplateSection] = field(default_factory=dict)

    # Variables
    variables: List[TemplateVariable] = field(default_factory=list)

    # Inheritance
    extends: Optional[str] = None
    blocks: Dict[str, str] = field(default_factory=dict)

    # Metadata
    version: str = "1.0.0"
    author: str = "BAEL"
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


class TemplateEngine:
    """
    Template processing engine for BAEL.
    """

    # Template syntax patterns
    VAR_PATTERN = re.compile(r"\{\{(\w+)(?:\|(\w+))?\}\}")  # {{var}} or {{var|transform}}
    SECTION_START = re.compile(r"\{%\s*(if|unless)\s+(\w+)\s*%\}")
    SECTION_END = re.compile(r"\{%\s*end(if|unless)\s*%\}")
    BLOCK_START = re.compile(r"\{%\s*block\s+(\w+)\s*%\}")
    BLOCK_END = re.compile(r"\{%\s*endblock\s*%\}")
    LOOP_START = re.compile(r"\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}")
    LOOP_END = re.compile(r"\{%\s*endfor\s*%\}")

    def __init__(self):
        # Template storage
        self.templates: Dict[str, EngineTemplate] = {}

        # Custom filters
        self._filters: Dict[str, Callable[[str], str]] = {}
        self._register_default_filters()

        # Stats
        self.stats = {
            "templates_registered": 0,
            "renders": 0,
        }

    def _register_default_filters(self) -> None:
        """Register default filters."""
        self._filters["upper"] = str.upper
        self._filters["lower"] = str.lower
        self._filters["title"] = str.title
        self._filters["capitalize"] = str.capitalize

        def snake_case(s: str) -> str:
            return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower()

        def pascal_case(s: str) -> str:
            words = s.replace("-", " ").replace("_", " ").split()
            return "".join(w.capitalize() for w in words)

        def camel_case(s: str) -> str:
            pascal = pascal_case(s)
            return pascal[0].lower() + pascal[1:] if pascal else ""

        self._filters["snake"] = snake_case
        self._filters["pascal"] = pascal_case
        self._filters["camel"] = camel_case

    def register(self, template: EngineTemplate) -> None:
        """Register a template."""
        self.templates[template.id] = template
        self.stats["templates_registered"] += 1
        logger.debug(f"Registered template: {template.id}")

    def register_filter(
        self,
        name: str,
        func: Callable[[str], str],
    ) -> None:
        """Register a custom filter."""
        self._filters[name] = func

    def get(self, template_id: str) -> Optional[EngineTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)

    def list(
        self,
        category: Optional[TemplateCategory] = None,
    ) -> List[EngineTemplate]:
        """List templates."""
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        return templates

    def render(
        self,
        template_id: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render a template with variables.

        Args:
            template_id: Template ID
            variables: Variable values

        Returns:
            Rendered content
        """
        self.stats["renders"] += 1

        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Validate variables
        self._validate_variables(template, variables)

        # Get base content (with inheritance)
        content = self._resolve_inheritance(template)

        # Process conditionals
        content = self._process_conditionals(content, variables)

        # Process loops
        content = self._process_loops(content, variables)

        # Substitute variables
        content = self._substitute_variables(content, variables, template)

        return content

    def render_string(
        self,
        template_string: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render a template string directly.

        Args:
            template_string: Template content
            variables: Variable values

        Returns:
            Rendered content
        """
        self.stats["renders"] += 1

        # Process conditionals
        content = self._process_conditionals(template_string, variables)

        # Process loops
        content = self._process_loops(content, variables)

        # Substitute variables
        content = self._substitute_variables(content, variables)

        return content

    def _validate_variables(
        self,
        template: EngineTemplate,
        variables: Dict[str, Any],
    ) -> None:
        """Validate variables against template definition."""
        for var_def in template.variables:
            value = variables.get(var_def.name)

            if not var_def.validate(value):
                if var_def.required and value is None:
                    raise ValueError(f"Required variable missing: {var_def.name}")
                if value is not None:
                    raise ValueError(f"Invalid value for variable: {var_def.name}")

    def _resolve_inheritance(self, template: EngineTemplate) -> str:
        """Resolve template inheritance."""
        if not template.extends:
            return template.content

        parent = self.templates.get(template.extends)
        if not parent:
            logger.warning(f"Parent template not found: {template.extends}")
            return template.content

        # Get parent content
        parent_content = self._resolve_inheritance(parent)

        # Replace blocks
        for block_name, block_content in template.blocks.items():
            pattern = re.compile(
                rf"\{{% block {block_name} %\}}.*?\{{% endblock %\}}",
                re.DOTALL,
            )
            replacement = f"{{% block {block_name} %}}{block_content}{{% endblock %}}"
            parent_content = pattern.sub(replacement, parent_content)

        # Remove block markers
        parent_content = re.sub(r"\{%\s*block\s+\w+\s*%\}", "", parent_content)
        parent_content = re.sub(r"\{%\s*endblock\s*%\}", "", parent_content)

        return parent_content

    def _process_conditionals(
        self,
        content: str,
        variables: Dict[str, Any],
    ) -> str:
        """Process conditional sections."""
        result = content

        # Find all conditionals
        while True:
            match = self.SECTION_START.search(result)
            if not match:
                break

            start_pos = match.start()
            condition_type = match.group(1)  # if or unless
            var_name = match.group(2)

            # Find matching end
            depth = 1
            search_pos = match.end()
            end_pos = -1

            while depth > 0:
                end_match = self.SECTION_END.search(result, search_pos)
                start_match = self.SECTION_START.search(result, search_pos)

                if not end_match:
                    break

                if start_match and start_match.start() < end_match.start():
                    depth += 1
                    search_pos = start_match.end()
                else:
                    depth -= 1
                    if depth == 0:
                        end_pos = end_match.end()
                    search_pos = end_match.end()

            if end_pos < 0:
                break

            # Extract section content
            section_content = result[match.end():end_pos - len(self.SECTION_END.search(result[end_pos-20:end_pos]).group())]

            # Evaluate condition
            value = variables.get(var_name)
            condition_met = bool(value)
            if condition_type == "unless":
                condition_met = not condition_met

            # Replace section
            if condition_met:
                # Clean up the end tag
                section_content = self.SECTION_END.sub("", section_content)
                result = result[:start_pos] + section_content + result[end_pos:]
            else:
                result = result[:start_pos] + result[end_pos:]

        return result

    def _process_loops(
        self,
        content: str,
        variables: Dict[str, Any],
    ) -> str:
        """Process loop sections."""
        result = content

        while True:
            match = self.LOOP_START.search(result)
            if not match:
                break

            start_pos = match.start()
            item_var = match.group(1)
            list_var = match.group(2)

            # Find matching end
            end_match = self.LOOP_END.search(result, match.end())
            if not end_match:
                break

            end_pos = end_match.end()

            # Extract loop content
            loop_content = result[match.end():end_match.start()]

            # Get list
            items = variables.get(list_var, [])
            if not isinstance(items, (list, tuple)):
                items = [items]

            # Render for each item
            rendered_items = []
            for item in items:
                item_vars = {**variables, item_var: item}
                rendered = self._substitute_variables(loop_content, item_vars)
                rendered_items.append(rendered)

            # Replace loop
            result = result[:start_pos] + "".join(rendered_items) + result[end_pos:]

        return result

    def _substitute_variables(
        self,
        content: str,
        variables: Dict[str, Any],
        template: Optional[EngineTemplate] = None,
    ) -> str:
        """Substitute variables in content."""
        def replacer(match):
            var_name = match.group(1)
            filter_name = match.group(2)

            value = variables.get(var_name, "")

            # Apply template variable transform if defined
            if template:
                for var_def in template.variables:
                    if var_def.name == var_name:
                        if var_def.transform:
                            value = var_def.apply_transform(str(value))
                        break

            # Apply explicit filter
            if filter_name and filter_name in self._filters:
                value = self._filters[filter_name](str(value))

            return str(value) if value is not None else ""

        return self.VAR_PATTERN.sub(replacer, content)

    def create_template(
        self,
        template_id: str,
        name: str,
        content: str,
        variables: Optional[List[TemplateVariable]] = None,
        **kwargs,
    ) -> EngineTemplate:
        """
        Create and register a new template.

        Args:
            template_id: Template ID
            name: Template name
            content: Template content
            variables: Variable definitions
            **kwargs: Additional template attributes

        Returns:
            Created template
        """
        template = EngineTemplate(
            id=template_id,
            name=name,
            content=content,
            variables=variables or [],
            **kwargs,
        )

        self.register(template)

        return template

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            **self.stats,
            "filters_registered": len(self._filters),
        }


def demo():
    """Demonstrate template engine."""
    print("=" * 60)
    print("BAEL Template Engine Demo")
    print("=" * 60)

    engine = TemplateEngine()

    # Create a template
    template = engine.create_template(
        template_id="greeting",
        name="Greeting Template",
        content="""
Hello, {{name|title}}!

{% if show_email %}
Your email: {{email}}
{% endif %}

{% for skill in skills %}
- {{skill}}
{% endfor %}
""",
        variables=[
            TemplateVariable(name="name", required=True),
            TemplateVariable(name="show_email", type=VariableType.BOOLEAN, default=False),
            TemplateVariable(name="email"),
            TemplateVariable(name="skills", type=VariableType.LIST),
        ],
    )

    print(f"\nRegistered template: {template.id}")

    # Render
    result = engine.render("greeting", {
        "name": "bael",
        "show_email": True,
        "email": "bael@example.com",
        "skills": ["Python", "AI", "Automation"],
    })

    print(f"\nRendered:")
    print(result)

    # Direct string rendering
    result2 = engine.render_string(
        "Class: {{name|pascal}}, Method: {{name|snake}}",
        {"name": "data processor"},
    )

    print(f"\nString render: {result2}")

    print(f"\nStats: {engine.get_stats()}")


if __name__ == "__main__":
    demo()
