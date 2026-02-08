# Contributing to BAEL - The Lord of All AI

Thank you for your interest in contributing to BAEL! This guide will help you get started with contributing to the world's most advanced autonomous agent platform.

## 🌟 Ways to Contribute

1. **Code Contributions** - New features, bug fixes, performance improvements
2. **Documentation** - Improve guides, tutorials, API docs
3. **Bug Reports** - Help us identify and fix issues
4. **Feature Requests** - Suggest new capabilities
5. **Testing** - Write tests, perform QA
6. **Examples** - Create example applications and use cases
7. **Community Support** - Help other users in discussions

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Docker & Docker Compose (optional, for containerization)
- PostgreSQL 13+ (or SQLite for development)
- Redis 6+ (for caching)

### Development Setup

1. **Fork and Clone the Repository**

```bash
# Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/BaelTheLordOfAll-AI.git
cd BaelTheLordOfAll-AI

# Add upstream remote
git remote add upstream https://github.com/aibaellord/BaelTheLordOfAll-AI.git
```

2. **Set Up Development Environment**

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-optional.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov black flake8 mypy
```

3. **Configure Environment**

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, set your API keys for LLM providers
```

4. **Initialize Database**

```bash
# For development with SQLite (easier)
export DATABASE_URL=sqlite:///./bael_dev.db

# Or for PostgreSQL
# createdb bael_dev
# export DATABASE_URL=postgresql://user:password@localhost/bael_dev

# Initialize the database
python -c "
from core.persistence_layer import get_database
db = get_database()
db.init()
print('Database initialized')
"
```

5. **Verify Setup**

```bash
# Run tests
pytest tests/

# Start BAEL
python main.py

# Verify it's running
curl http://localhost:8000/health
```

## 📝 Code Style and Standards

### Python Style Guide

We follow PEP 8 with some modifications:

- **Line Length**: 100 characters (not 79)
- **Imports**: Organized in groups (stdlib, third-party, local)
- **Type Hints**: Required for all functions and methods
- **Docstrings**: Google-style docstrings for all public functions

### Code Formatting

We use **Black** for automatic code formatting:

```bash
# Format all Python files
black .

# Check formatting without making changes
black --check .
```

### Linting

We use **flake8** for linting:

```bash
# Run linter
flake8 core/ tools/ plugins/ --max-line-length=100

# Run type checker
mypy core/ tools/ plugins/
```

### Example Code Style

```python
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ExampleClass(BaseModel):
    """Example class demonstrating BAEL coding standards.
    
    This class shows proper type hints, docstrings, and structure.
    
    Attributes:
        name: The name of the example
        created_at: When the example was created
        metadata: Additional metadata
    """
    
    name: str = Field(..., description="Name of the example")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    async def process(self, input_data: str) -> Dict[str, Any]:
        """Process input data and return results.
        
        Args:
            input_data: The data to process
            
        Returns:
            Dictionary containing processing results
            
        Raises:
            ValueError: If input_data is empty
        """
        if not input_data:
            raise ValueError("input_data cannot be empty")
        
        # Processing logic here
        result = {
            "processed": True,
            "data": input_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return result
```

## 🧪 Testing

### Writing Tests

All new features must include tests. We use pytest for testing.

```python
# tests/test_example.py
import pytest
from your_module import ExampleClass


class TestExampleClass:
    """Test suite for ExampleClass."""
    
    @pytest.fixture
    def example_instance(self):
        """Create an ExampleClass instance for testing."""
        return ExampleClass(name="test")
    
    def test_creation(self, example_instance):
        """Test that ExampleClass can be created."""
        assert example_instance.name == "test"
        assert example_instance.created_at is not None
    
    @pytest.mark.asyncio
    async def test_process_valid_input(self, example_instance):
        """Test processing with valid input."""
        result = await example_instance.process("test data")
        assert result["processed"] is True
        assert result["data"] == "test data"
    
    @pytest.mark.asyncio
    async def test_process_empty_input(self, example_instance):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="input_data cannot be empty"):
            await example_instance.process("")
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_example.py

# Run with coverage
pytest --cov=core --cov=tools --cov=plugins --cov-report=html

# Run specific test
pytest tests/test_example.py::TestExampleClass::test_creation

# Run tests matching a pattern
pytest -k "test_process"
```

### Test Coverage

We aim for:
- **Minimum 80% coverage** for new code
- **90%+ coverage** for critical systems
- **100% coverage** for security-related code

## 🔄 Contribution Workflow

### 1. Create a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Write your code following our style guide
- Add tests for new functionality
- Update documentation as needed
- Commit frequently with clear messages

### 3. Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Feature
git commit -m "feat: add new skill creation capability"

# Bug fix
git commit -m "fix: resolve memory leak in orchestrator"

# Documentation
git commit -m "docs: add API examples for collaboration protocol"

# Performance
git commit -m "perf: optimize vector search in knowledge base"

# Refactoring
git commit -m "refactor: simplify error handling in brain module"

# Tests
git commit -m "test: add integration tests for MCP client"
```

### 4. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create PR on GitHub
# Go to https://github.com/aibaellord/BaelTheLordOfAll-AI
# Click "New Pull Request"
```

### 5. Pull Request Guidelines

Your PR should include:

- **Clear Title**: Descriptive and following conventional commits format
- **Description**: Explain what changes you made and why
- **Tests**: All tests passing, new tests added for new features
- **Documentation**: Updated docs for any user-facing changes
- **Screenshots**: If UI changes, include before/after screenshots

**PR Template:**

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Change 1
- Change 2

## Testing
- [ ] All existing tests pass
- [ ] Added new tests for new functionality
- [ ] Manual testing completed

## Documentation
- [ ] Updated relevant documentation
- [ ] Added code comments where necessary
- [ ] Updated API documentation if applicable

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code is commented where needed
- [ ] Documentation is updated
- [ ] No new warnings generated
- [ ] Tests pass locally
```

## 🎯 Areas for Contribution

### High Priority

1. **Core Capabilities**
   - Enhanced reasoning strategies
   - New tool integrations
   - Memory system improvements
   - Performance optimizations

2. **Persona System**
   - New specialist personas
   - Improved persona coordination
   - Domain-specific expertise modules

3. **Testing**
   - Integration tests
   - Performance benchmarks
   - Edge case coverage
   - Load testing

4. **Documentation**
   - More examples and tutorials
   - API documentation improvements
   - Video tutorials
   - Use case guides

### Medium Priority

1. **UI/UX**
   - React UI enhancements
   - New dashboard widgets
   - Workflow builder improvements
   - Mobile responsiveness

2. **Integrations**
   - New LLM provider integrations
   - MCP server implementations
   - Third-party service connectors
   - IDE plugins

3. **Tooling**
   - Developer CLI tools
   - Debugging utilities
   - Performance profilers
   - Monitoring dashboards

### Good First Issues

Look for issues labeled `good-first-issue` on GitHub. These are specifically chosen for newcomers:

- Documentation improvements
- Adding code examples
- Writing tests
- Fixing typos and formatting
- Adding type hints
- Improving error messages

## 🐛 Bug Reports

### Before Submitting a Bug Report

1. **Search existing issues** - Your bug might already be reported
2. **Update to latest version** - The bug might be fixed
3. **Reproduce the bug** - Can you consistently trigger it?
4. **Minimal reproduction** - Create the smallest example that demonstrates the bug

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**To Reproduce**
1. Step 1
2. Step 2
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- BAEL Version: [e.g., v3.0.0]
- Python Version: [e.g., 3.10.5]
- OS: [e.g., Ubuntu 22.04]
- Installation Method: [pip, docker, source]

**Logs**
```
Paste relevant logs here
```

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

We welcome feature requests! Please use this template:

```markdown
**Problem Statement**
Describe the problem this feature would solve

**Proposed Solution**
Your suggested implementation

**Alternatives Considered**
Other approaches you've thought about

**Use Cases**
How would this feature be used?

**Additional Context**
Mockups, examples, references, etc.
```

## 📚 Documentation Contributions

### Types of Documentation

1. **Code Documentation**
   - Inline comments for complex logic
   - Docstrings for all public functions
   - Type hints for all functions

2. **User Documentation**
   - Getting started guides
   - Tutorials
   - How-to guides
   - Reference documentation

3. **Developer Documentation**
   - Architecture documents
   - API documentation
   - Plugin development guides
   - Contributing guides

### Documentation Style

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Keep it up-to-date with code changes
- Use proper markdown formatting

## 🔐 Security

### Reporting Security Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Instead, email security concerns to: **security@bael.ai** (replace with actual email)

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you to resolve the issue.

### Security Best Practices

When contributing code:
- Never commit API keys, passwords, or secrets
- Use environment variables for sensitive data
- Validate all user inputs
- Use parameterized queries for database access
- Follow principle of least privilege
- Keep dependencies updated

## 🎓 Learning Resources

### Understanding BAEL

- [README.md](README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) - Documentation hub
- [docs/](docs/) - Detailed documentation

### Code Examples

- [examples/](examples/) - Example applications
- [tests/](tests/) - Test examples showing usage
- [plugins/](plugins/) - Example plugins

### External Resources

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [pytest Documentation](https://docs.pytest.org/)

## 🤝 Community

### Communication Channels

- **GitHub Discussions** - General discussions, questions
- **GitHub Issues** - Bug reports, feature requests
- **Discord** - Real-time chat (if available)
- **Email** - For private inquiries

### Code of Conduct

We are committed to providing a welcoming and inclusive environment. Be respectful, constructive, and professional in all interactions.

Key points:
- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Accept constructive criticism gracefully
- Show empathy towards others

## 📜 License

By contributing to BAEL, you agree that your contributions will be licensed under the same license as the project.

## 🙏 Recognition

All contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Significant contributions may also be featured in:
- Project README
- Social media announcements
- Blog posts

## ❓ Questions?

If you have questions about contributing:

1. Check the [FAQ.md](FAQ.md)
2. Search [GitHub Discussions](https://github.com/aibaellord/BaelTheLordOfAll-AI/discussions)
3. Ask in [GitHub Discussions](https://github.com/aibaellord/BaelTheLordOfAll-AI/discussions)
4. Review existing issues and PRs

---

**Thank you for contributing to BAEL! Together, we're building the most advanced AI platform in the world.** 🚀

_"We don't compete. We dominate."_
