---
description: Autonomous code generation pipeline with quality assurance
---

# Code Generation Workflow

## Overview
End-to-end code generation with planning, implementation, and verification.

## Steps

// turbo-all

1. **Requirements Analysis**
   - Parse user requirements
   - Identify existing patterns in codebase
   - Determine integration points

2. **Architecture Planning**
   - Design component structure
   - Define interfaces and contracts
   - Plan test coverage

3. **Implementation**
   ```bash
   # Generate code following project conventions
   # Use write_to_file for new files
   # Use replace_file_content for modifications
   ```

4. **Quality Checks**
   ```bash
   # Run linting
   python -m pylint --errors-only <file>
   
   # Check types
   python -m mypy <file> --ignore-missing-imports
   ```

5. **Testing**
   ```bash
   python -m pytest tests/ -v --tb=short
   ```

6. **Documentation**
   - Add docstrings and comments
   - Update README if needed
   - Create usage examples

## Quality Gates
- All imports resolve
- No syntax errors  
- Tests pass
- Follows project style
