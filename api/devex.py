"""
API Documentation and Developer Experience utilities.
Provides comprehensive documentation, examples, and testing support.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BAEL.DevEx")


class APIEndpointDoc:
    """Documentation for a single API endpoint."""

    def __init__(self, method: str, path: str, summary: str, description: str):
        self.method = method
        self.path = path
        self.summary = summary
        self.description = description
        self.parameters: List[Dict[str, Any]] = []
        self.request_body: Optional[Dict[str, Any]] = None
        self.responses: Dict[int, Dict[str, Any]] = {}
        self.examples: List[Dict[str, Any]] = []
        self.tags: List[str] = []
        self.auth_required = False
        self.rate_limit: Optional[int] = None

    def add_parameter(self, name: str, param_type: str, required: bool = True,
                     description: str = "", example: Optional[Any] = None):
        """Add parameter documentation."""
        self.parameters.append({
            "name": name,
            "type": param_type,
            "required": required,
            "description": description,
            "example": example
        })

    def add_response(self, status_code: int, description: str, schema: Optional[Dict] = None):
        """Add response documentation."""
        self.responses[status_code] = {
            "description": description,
            "schema": schema
        }

    def add_example(self, title: str, request: Optional[Dict] = None, response: Optional[Dict] = None):
        """Add usage example."""
        self.examples.append({
            "title": title,
            "request": request,
            "response": response
        })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for OpenAPI."""
        return {
            "method": self.method,
            "path": self.path,
            "summary": self.summary,
            "description": self.description,
            "parameters": self.parameters,
            "request_body": self.request_body,
            "responses": self.responses,
            "examples": self.examples,
            "tags": self.tags,
            "auth_required": self.auth_required,
            "rate_limit": self.rate_limit
        }


class APIDocumentation:
    """Central API documentation."""

    def __init__(self, title: str, version: str, description: str):
        self.title = title
        self.version = version
        self.description = description
        self.endpoints: Dict[str, APIEndpointDoc] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.created_at = datetime.utcnow()

    def register_endpoint(self, endpoint: APIEndpointDoc):
        """Register an endpoint."""
        key = f"{endpoint.method} {endpoint.path}"
        self.endpoints[key] = endpoint
        logger.debug(f"Documented endpoint: {key}")

    def register_schema(self, name: str, schema: Dict[str, Any]):
        """Register a data schema."""
        self.schemas[name] = schema
        logger.debug(f"Documented schema: {name}")

    def get_endpoint_doc(self, method: str, path: str) -> Optional[APIEndpointDoc]:
        """Get documentation for endpoint."""
        key = f"{method} {path}"
        return self.endpoints.get(key)

    def list_endpoints(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all endpoints or filter by tag."""
        endpoints = list(self.endpoints.values())

        if tag:
            endpoints = [e for e in endpoints if tag in e.tags]

        return [e.to_dict() for e in endpoints]

    def export_openapi(self) -> Dict[str, Any]:
        """Export as OpenAPI 3.0 specification."""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description
            },
            "paths": {
                endpoint.path: {
                    endpoint.method.lower(): endpoint.to_dict()
                }
                for endpoint in self.endpoints.values()
            },
            "components": {
                "schemas": self.schemas
            }
        }

    def export_markdown(self) -> str:
        """Export as Markdown documentation."""
        doc = f"# {self.title}\n\n"
        doc += f"Version: {self.version}\n"
        doc += f"Generated: {self.created_at.isoformat()}\n\n"
        doc += f"{self.description}\n\n"

        # Group by tags
        tags_dict: Dict[str, List[APIEndpointDoc]] = {}
        for endpoint in self.endpoints.values():
            tag = endpoint.tags[0] if endpoint.tags else "General"
            if tag not in tags_dict:
                tags_dict[tag] = []
            tags_dict[tag].append(endpoint)

        # Document each tag
        for tag, endpoints in sorted(tags_dict.items()):
            doc += f"## {tag}\n\n"

            for endpoint in endpoints:
                doc += f"### {endpoint.method} {endpoint.path}\n\n"
                doc += f"{endpoint.summary}\n\n"
                doc += f"{endpoint.description}\n\n"

                if endpoint.parameters:
                    doc += "#### Parameters\n\n"
                    for param in endpoint.parameters:
                        doc += f"- `{param['name']}` ({param['type']}) "
                        doc += f"{'[required]' if param['required'] else '[optional]'}: "
                        doc += f"{param.get('description', '')}\n"
                    doc += "\n"

                if endpoint.responses:
                    doc += "#### Responses\n\n"
                    for status, resp in sorted(endpoint.responses.items()):
                        doc += f"- `{status}`: {resp['description']}\n"
                    doc += "\n"

                if endpoint.examples:
                    doc += "#### Examples\n\n"
                    for example in endpoint.examples:
                        doc += f"**{example['title']}**\n\n"
                        if example.get('request'):
                            doc += "```json\n"
                            doc += json.dumps(example['request'], indent=2)
                            doc += "\n```\n\n"
                        if example.get('response'):
                            doc += "Response:\n```json\n"
                            doc += json.dumps(example['response'], indent=2)
                            doc += "\n```\n\n"

        return doc


class TestCase:
    """API test case."""

    def __init__(self, name: str, endpoint: str, method: str):
        self.name = name
        self.endpoint = endpoint
        self.method = method
        self.request: Dict[str, Any] = {}
        self.expected_status: int = 200
        self.expected_response: Optional[Dict] = None
        self.setup: Optional[callable] = None
        self.teardown: Optional[callable] = None

    def set_request(self, **kwargs):
        """Set request payload."""
        self.request = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "method": self.method,
            "request": self.request,
            "expected_status": self.expected_status,
            "expected_response": self.expected_response
        }


class TestSuite:
    """Collection of API test cases."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tests: List[TestCase] = []

    def add_test(self, test: TestCase):
        """Add test case."""
        self.tests.append(test)
        logger.debug(f"Added test: {test.name}")

    def get_tests(self) -> List[Dict[str, Any]]:
        """Get all tests."""
        return [t.to_dict() for t in self.tests]

    def export_postman(self) -> Dict[str, Any]:
        """Export as Postman collection."""
        return {
            "info": {
                "name": self.name,
                "description": self.description,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [
                {
                    "name": test.name,
                    "request": {
                        "method": test.method,
                        "url": test.endpoint,
                        "body": test.request
                    },
                    "response": [
                        {
                            "name": "Default",
                            "status": test.expected_status,
                            "body": json.dumps(test.expected_response) if test.expected_response else ""
                        }
                    ]
                }
                for test in self.tests
            ]
        }


class DevelopmentGuide:
    """Development guide and best practices."""

    def __init__(self):
        self.sections: Dict[str, str] = {}

    def add_section(self, title: str, content: str):
        """Add a section to the guide."""
        self.sections[title] = content

    def to_markdown(self) -> str:
        """Export as Markdown."""
        guide = "# Development Guide\n\n"

        for title, content in self.sections.items():
            guide += f"## {title}\n\n{content}\n\n"

        return guide


# Global instances
api_docs = APIDocumentation(
    title="BAEL API",
    version="1.0.0",
    description="The ultimate AI agent orchestration system API"
)

test_suite = TestSuite(
    name="BAEL API Tests",
    description="Comprehensive test suite for BAEL API endpoints"
)

dev_guide = DevelopmentGuide()
