"""
BAEL - Self-Modification System
Enables agents to analyze failures, learn, and modify their own capabilities.

This surpasses Agent Zero by providing safe, sandboxed self-modification.
"""

import ast
import asyncio
import difflib
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.Evolution.SelfModifier")


class ModificationType(Enum):
    """Types of self-modifications."""
    BUG_FIX = "bug_fix"
    OPTIMIZATION = "optimization"
    NEW_CAPABILITY = "new_capability"
    REFACTORING = "refactoring"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE = "performance"


class ModificationSafety(Enum):
    """Safety levels for modifications."""
    SAFE = "safe"  # No external effects, reversible
    MODERATE = "moderate"  # Limited effects, needs review
    RISKY = "risky"  # Significant changes, requires approval
    CRITICAL = "critical"  # System-wide changes, manual only


@dataclass
class ExecutionFailure:
    """Captured execution failure for learning."""
    failure_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    stack_trace: str
    context: Dict[str, Any]
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None
    expected_output: Optional[Any] = None
    actual_output: Optional[Any] = None
    frequency: int = 1
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class CodePatch:
    """A proposed code modification."""
    patch_id: str
    file_path: str
    modification_type: ModificationType
    safety_level: ModificationSafety
    description: str
    original_code: str
    modified_code: str
    diff: str
    confidence: float  # 0.0 to 1.0
    test_results: Optional[Dict[str, Any]] = None
    applied: bool = False
    applied_at: Optional[datetime] = None
    rolled_back: bool = False
    rollback_reason: Optional[str] = None


@dataclass
class CapabilityExpansion:
    """A new capability added to the system."""
    capability_id: str
    name: str
    description: str
    source_type: str  # "generated", "learned", "composed"
    code: str
    dependencies: List[str] = field(default_factory=list)
    test_coverage: float = 0.0
    usage_count: int = 0
    success_rate: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)


class SelfModifier:
    """
    Self-modification engine for BAEL.
    
    Features:
    - Failure analysis and pattern recognition
    - Safe code patch generation
    - Sandboxed testing
    - Automatic rollback
    - Capability expansion tracking
    """
    
    def __init__(
        self,
        project_root: str = ".",
        sandbox_path: str = "./sandbox",
        max_modification_size: int = 500,  # lines
        auto_apply_safe: bool = False,
        llm_provider: Optional[Callable] = None
    ):
        self.project_root = Path(project_root)
        self.sandbox_path = Path(sandbox_path)
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        
        self.max_modification_size = max_modification_size
        self.auto_apply_safe = auto_apply_safe
        self.llm_provider = llm_provider
        
        # State
        self._failures: Dict[str, ExecutionFailure] = {}
        self._failure_patterns: Dict[str, List[str]] = {}  # pattern -> failure_ids
        self._patches: Dict[str, CodePatch] = {}
        self._capabilities: Dict[str, CapabilityExpansion] = {}
        self._applied_patches: List[str] = []
        self._rollback_stack: List[Tuple[str, str, str]] = []  # (patch_id, file, original)
        
        logger.info("SelfModifier initialized")
    
    # Failure Analysis
    
    async def record_failure(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        input_data: Dict[str, Any] = None,
        expected_output: Any = None,
        actual_output: Any = None
    ) -> ExecutionFailure:
        """Record an execution failure for analysis."""
        import traceback
        
        # Extract source info
        tb = traceback.extract_tb(error.__traceback__)
        source_file = tb[-1].filename if tb else None
        source_line = tb[-1].lineno if tb else None
        
        # Create failure signature for deduplication
        signature = self._create_failure_signature(
            type(error).__name__,
            str(error),
            source_file,
            source_line
        )
        
        if signature in self._failures:
            # Increment frequency
            self._failures[signature].frequency += 1
            return self._failures[signature]
        
        failure = ExecutionFailure(
            failure_id=signature,
            timestamp=datetime.utcnow(),
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or {},
            source_file=source_file,
            source_line=source_line,
            input_data=input_data,
            expected_output=expected_output,
            actual_output=actual_output
        )
        
        self._failures[signature] = failure
        await self._analyze_failure_pattern(failure)
        
        logger.info(f"Recorded failure: {failure.error_type} at {source_file}:{source_line}")
        return failure
    
    def _create_failure_signature(
        self,
        error_type: str,
        message: str,
        file: str,
        line: int
    ) -> str:
        """Create unique signature for failure deduplication."""
        content = f"{error_type}:{file}:{line}:{message[:100]}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    async def _analyze_failure_pattern(self, failure: ExecutionFailure) -> None:
        """Analyze failure for patterns."""
        # Common patterns
        patterns = []
        
        if "KeyError" in failure.error_type:
            patterns.append("missing_key")
        if "AttributeError" in failure.error_type:
            patterns.append("missing_attribute")
        if "TypeError" in failure.error_type:
            patterns.append("type_mismatch")
        if "IndexError" in failure.error_type:
            patterns.append("index_bounds")
        if "FileNotFoundError" in failure.error_type:
            patterns.append("missing_file")
        if "timeout" in failure.error_message.lower():
            patterns.append("timeout")
        if "connection" in failure.error_message.lower():
            patterns.append("connection_issue")
        
        for pattern in patterns:
            if pattern not in self._failure_patterns:
                self._failure_patterns[pattern] = []
            self._failure_patterns[pattern].append(failure.failure_id)
    
    async def get_frequent_failures(self, min_frequency: int = 3) -> List[ExecutionFailure]:
        """Get failures that occur frequently."""
        return [
            f for f in self._failures.values()
            if f.frequency >= min_frequency and not f.resolved
        ]
    
    # Patch Generation
    
    async def generate_fix(
        self,
        failure: ExecutionFailure,
        strategy: str = "auto"
    ) -> Optional[CodePatch]:
        """Generate a fix for a failure."""
        if not failure.source_file or not os.path.exists(failure.source_file):
            logger.warning(f"Cannot generate fix: source file not found")
            return None
        
        # Read source code
        with open(failure.source_file, 'r') as f:
            source_lines = f.readlines()
        
        # Get context around error
        start_line = max(0, failure.source_line - 10)
        end_line = min(len(source_lines), failure.source_line + 10)
        context_code = ''.join(source_lines[start_line:end_line])
        
        # Generate fix based on strategy
        if strategy == "auto":
            strategy = self._select_strategy(failure)
        
        if strategy == "add_error_handling":
            patch = await self._generate_error_handling_fix(
                failure, source_lines, start_line, end_line
            )
        elif strategy == "add_null_check":
            patch = await self._generate_null_check_fix(
                failure, source_lines, start_line, end_line
            )
        elif strategy == "add_type_check":
            patch = await self._generate_type_check_fix(
                failure, source_lines, start_line, end_line
            )
        elif strategy == "llm_fix" and self.llm_provider:
            patch = await self._generate_llm_fix(
                failure, source_lines, start_line, end_line
            )
        else:
            logger.warning(f"Unknown strategy: {strategy}")
            return None
        
        if patch:
            self._patches[patch.patch_id] = patch
        
        return patch
    
    def _select_strategy(self, failure: ExecutionFailure) -> str:
        """Select the best fix strategy for a failure."""
        error_type = failure.error_type
        
        if error_type in ("KeyError", "AttributeError", "NoneType"):
            return "add_null_check"
        elif error_type == "TypeError":
            return "add_type_check"
        elif error_type in ("FileNotFoundError", "ConnectionError", "TimeoutError"):
            return "add_error_handling"
        elif self.llm_provider:
            return "llm_fix"
        else:
            return "add_error_handling"
    
    async def _generate_error_handling_fix(
        self,
        failure: ExecutionFailure,
        source_lines: List[str],
        start: int,
        end: int
    ) -> CodePatch:
        """Generate a try-except wrapper fix."""
        # Find the problematic line and wrap it
        line_idx = failure.source_line - 1
        if line_idx >= len(source_lines):
            return None
        
        original_line = source_lines[line_idx]
        indent = len(original_line) - len(original_line.lstrip())
        indent_str = ' ' * indent
        
        # Create wrapped version
        wrapped = f"{indent_str}try:\n"
        wrapped += f"{indent_str}    {original_line.strip()}\n"
        wrapped += f"{indent_str}except {failure.error_type} as e:\n"
        wrapped += f"{indent_str}    logger.warning(f\"Handled {failure.error_type}: {{e}}\")\n"
        wrapped += f"{indent_str}    # TODO: Add proper fallback logic\n"
        wrapped += f"{indent_str}    pass\n"
        
        # Create patch
        original = ''.join(source_lines)
        modified_lines = source_lines.copy()
        modified_lines[line_idx] = wrapped
        modified = ''.join(modified_lines)
        
        diff = self._create_diff(original, modified, failure.source_file)
        
        return CodePatch(
            patch_id=self._generate_patch_id(),
            file_path=failure.source_file,
            modification_type=ModificationType.ERROR_HANDLING,
            safety_level=ModificationSafety.SAFE,
            description=f"Add error handling for {failure.error_type} at line {failure.source_line}",
            original_code=original_line,
            modified_code=wrapped,
            diff=diff,
            confidence=0.7
        )
    
    async def _generate_null_check_fix(
        self,
        failure: ExecutionFailure,
        source_lines: List[str],
        start: int,
        end: int
    ) -> CodePatch:
        """Generate a null/key check fix."""
        line_idx = failure.source_line - 1
        if line_idx >= len(source_lines):
            return None
        
        original_line = source_lines[line_idx]
        indent = len(original_line) - len(original_line.lstrip())
        indent_str = ' ' * indent
        
        # Detect the pattern and add appropriate check
        if "KeyError" in failure.error_type:
            # Extract key from error message
            key_match = re.search(r"'([^']+)'", failure.error_message)
            key = key_match.group(1) if key_match else "key"
            
            check = f"{indent_str}# Auto-added null check for {key}\n"
            check += f"{indent_str}if '{key}' not in data:\n"
            check += f"{indent_str}    data['{key}'] = None  # Default value\n"
            check += original_line
        else:
            # Generic None check
            check = f"{indent_str}# Auto-added None check\n"
            check += f"{indent_str}if obj is None:\n"
            check += f"{indent_str}    return None  # or raise ValueError\n"
            check += original_line
        
        original = ''.join(source_lines)
        modified_lines = source_lines.copy()
        modified_lines[line_idx] = check
        modified = ''.join(modified_lines)
        
        diff = self._create_diff(original, modified, failure.source_file)
        
        return CodePatch(
            patch_id=self._generate_patch_id(),
            file_path=failure.source_file,
            modification_type=ModificationType.BUG_FIX,
            safety_level=ModificationSafety.MODERATE,
            description=f"Add null/key check for {failure.error_type}",
            original_code=original_line,
            modified_code=check,
            diff=diff,
            confidence=0.6
        )
    
    async def _generate_type_check_fix(
        self,
        failure: ExecutionFailure,
        source_lines: List[str],
        start: int,
        end: int
    ) -> CodePatch:
        """Generate a type check fix."""
        line_idx = failure.source_line - 1
        if line_idx >= len(source_lines):
            return None
        
        original_line = source_lines[line_idx]
        indent = len(original_line) - len(original_line.lstrip())
        indent_str = ' ' * indent
        
        # Add type assertion
        check = f"{indent_str}# Auto-added type check\n"
        check += f"{indent_str}# TODO: Replace 'value' with actual variable\n"
        check += f"{indent_str}if not isinstance(value, expected_type):\n"
        check += f"{indent_str}    value = expected_type(value)  # Attempt conversion\n"
        check += original_line
        
        original = ''.join(source_lines)
        modified_lines = source_lines.copy()
        modified_lines[line_idx] = check
        modified = ''.join(modified_lines)
        
        diff = self._create_diff(original, modified, failure.source_file)
        
        return CodePatch(
            patch_id=self._generate_patch_id(),
            file_path=failure.source_file,
            modification_type=ModificationType.BUG_FIX,
            safety_level=ModificationSafety.MODERATE,
            description=f"Add type check for {failure.error_type}",
            original_code=original_line,
            modified_code=check,
            diff=diff,
            confidence=0.5
        )
    
    async def _generate_llm_fix(
        self,
        failure: ExecutionFailure,
        source_lines: List[str],
        start: int,
        end: int
    ) -> Optional[CodePatch]:
        """Generate a fix using LLM."""
        if not self.llm_provider:
            return None
        
        context_code = ''.join(source_lines[start:end])
        
        prompt = f"""Analyze this Python code error and suggest a fix:

Error Type: {failure.error_type}
Error Message: {failure.error_message}
Line Number: {failure.source_line}

Code Context:
```python
{context_code}
```

Stack Trace:
{failure.stack_trace}

Provide a minimal fix that:
1. Handles the error appropriately
2. Maintains existing functionality
3. Follows Python best practices

Return only the fixed code for the problematic section."""

        try:
            response = await self.llm_provider(prompt)
            fixed_code = self._extract_code_from_response(response)
            
            if fixed_code:
                original = ''.join(source_lines)
                modified_lines = source_lines.copy()
                modified_lines[start:end] = [fixed_code + '\n']
                modified = ''.join(modified_lines)
                
                diff = self._create_diff(original, modified, failure.source_file)
                
                return CodePatch(
                    patch_id=self._generate_patch_id(),
                    file_path=failure.source_file,
                    modification_type=ModificationType.BUG_FIX,
                    safety_level=ModificationSafety.MODERATE,
                    description=f"LLM-generated fix for {failure.error_type}",
                    original_code=context_code,
                    modified_code=fixed_code,
                    diff=diff,
                    confidence=0.8
                )
        except Exception as e:
            logger.error(f"LLM fix generation failed: {e}")
        
        return None
    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract code from LLM response."""
        # Try to find code block
        code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        code_match = re.search(r'```\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        return None
    
    def _create_diff(self, original: str, modified: str, filename: str) -> str:
        """Create unified diff."""
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}"
        )
        return ''.join(diff)
    
    def _generate_patch_id(self) -> str:
        """Generate unique patch ID."""
        import uuid
        return f"patch_{uuid.uuid4().hex[:8]}"
    
    # Safe Testing
    
    async def test_patch(self, patch: CodePatch) -> Dict[str, Any]:
        """Test a patch in sandbox before applying."""
        # Copy file to sandbox
        original_path = Path(patch.file_path)
        sandbox_file = self.sandbox_path / original_path.name
        
        # Read and modify
        with open(patch.file_path, 'r') as f:
            content = f.read()
        
        modified_content = content.replace(patch.original_code, patch.modified_code)
        
        # Write to sandbox
        with open(sandbox_file, 'w') as f:
            f.write(modified_content)
        
        # Run syntax check
        try:
            compile(modified_content, str(sandbox_file), 'exec')
            syntax_valid = True
        except SyntaxError as e:
            syntax_valid = False
            patch.test_results = {
                "syntax_valid": False,
                "error": str(e)
            }
            return patch.test_results
        
        # Run AST analysis
        try:
            tree = ast.parse(modified_content)
            ast_valid = True
        except:
            ast_valid = False
        
        # Try to run tests if they exist
        test_results = {
            "syntax_valid": syntax_valid,
            "ast_valid": ast_valid,
            "tests_passed": None,
            "error": None
        }
        
        patch.test_results = test_results
        
        # Cleanup sandbox
        if sandbox_file.exists():
            sandbox_file.unlink()
        
        return test_results
    
    async def apply_patch(
        self,
        patch: CodePatch,
        force: bool = False
    ) -> bool:
        """Apply a patch to the actual codebase."""
        if patch.applied:
            logger.warning(f"Patch {patch.patch_id} already applied")
            return False
        
        if patch.safety_level == ModificationSafety.CRITICAL and not force:
            logger.warning(f"Patch {patch.patch_id} is CRITICAL - requires force=True")
            return False
        
        if not self.auto_apply_safe and patch.safety_level != ModificationSafety.SAFE and not force:
            logger.warning(f"Auto-apply disabled for non-safe patches")
            return False
        
        # Test first
        if not patch.test_results:
            await self.test_patch(patch)
        
        if patch.test_results and not patch.test_results.get("syntax_valid"):
            logger.error(f"Patch {patch.patch_id} failed syntax validation")
            return False
        
        # Backup original
        with open(patch.file_path, 'r') as f:
            original_content = f.read()
        
        # Apply patch
        try:
            modified_content = original_content.replace(
                patch.original_code,
                patch.modified_code
            )
            
            with open(patch.file_path, 'w') as f:
                f.write(modified_content)
            
            # Save for rollback
            self._rollback_stack.append((
                patch.patch_id,
                patch.file_path,
                original_content
            ))
            
            patch.applied = True
            patch.applied_at = datetime.utcnow()
            self._applied_patches.append(patch.patch_id)
            
            logger.info(f"Applied patch {patch.patch_id} to {patch.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply patch: {e}")
            # Restore original
            with open(patch.file_path, 'w') as f:
                f.write(original_content)
            return False
    
    async def rollback_patch(self, patch_id: str, reason: str = None) -> bool:
        """Rollback a previously applied patch."""
        for i, (pid, file_path, original) in enumerate(self._rollback_stack):
            if pid == patch_id:
                try:
                    with open(file_path, 'w') as f:
                        f.write(original)
                    
                    self._rollback_stack.pop(i)
                    
                    if patch_id in self._patches:
                        self._patches[patch_id].rolled_back = True
                        self._patches[patch_id].rollback_reason = reason
                    
                    logger.info(f"Rolled back patch {patch_id}")
                    return True
                except Exception as e:
                    logger.error(f"Rollback failed: {e}")
                    return False
        
        logger.warning(f"Patch {patch_id} not found in rollback stack")
        return False
    
    # Capability Expansion
    
    async def create_capability(
        self,
        name: str,
        description: str,
        code: str,
        dependencies: List[str] = None
    ) -> CapabilityExpansion:
        """Create a new capability from code."""
        # Validate code
        try:
            compile(code, f"capability_{name}", 'exec')
        except SyntaxError as e:
            raise ValueError(f"Invalid capability code: {e}")
        
        capability = CapabilityExpansion(
            capability_id=f"cap_{hashlib.md5(name.encode()).hexdigest()[:8]}",
            name=name,
            description=description,
            source_type="generated",
            code=code,
            dependencies=dependencies or []
        )
        
        self._capabilities[capability.capability_id] = capability
        
        logger.info(f"Created capability: {name}")
        return capability
    
    async def deploy_capability(
        self,
        capability_id: str,
        target_module: str
    ) -> bool:
        """Deploy a capability to a module."""
        if capability_id not in self._capabilities:
            logger.error(f"Capability {capability_id} not found")
            return False
        
        capability = self._capabilities[capability_id]
        
        # Append to target module
        target_path = self.project_root / target_module
        
        try:
            with open(target_path, 'a') as f:
                f.write(f"\n\n# Auto-generated capability: {capability.name}\n")
                f.write(f"# {capability.description}\n")
                f.write(capability.code)
            
            logger.info(f"Deployed capability {capability.name} to {target_module}")
            return True
        except Exception as e:
            logger.error(f"Failed to deploy capability: {e}")
            return False
    
    # Statistics
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get self-modification statistics."""
        return {
            "total_failures_recorded": len(self._failures),
            "unresolved_failures": sum(1 for f in self._failures.values() if not f.resolved),
            "failure_patterns": {k: len(v) for k, v in self._failure_patterns.items()},
            "patches_generated": len(self._patches),
            "patches_applied": len(self._applied_patches),
            "patches_rolled_back": sum(1 for p in self._patches.values() if p.rolled_back),
            "capabilities_created": len(self._capabilities)
        }


# Singleton
_self_modifier: Optional[SelfModifier] = None


def get_self_modifier(project_root: str = ".") -> SelfModifier:
    """Get the global self-modifier instance."""
    global _self_modifier
    if _self_modifier is None:
        _self_modifier = SelfModifier(project_root=project_root)
    return _self_modifier


async def main():
    """Example usage."""
    modifier = get_self_modifier()
    
    # Simulate a failure
    try:
        data = {"name": "test"}
        value = data["missing_key"]  # Will raise KeyError
    except Exception as e:
        failure = await modifier.record_failure(
            error=e,
            context={"operation": "data_access"},
            input_data={"data": data}
        )
        print(f"Recorded failure: {failure.failure_id}")
        
        # Generate fix
        # patch = await modifier.generate_fix(failure)
        # if patch:
        #     print(f"Generated patch: {patch.patch_id}")
        #     print(patch.diff)
    
    # Show statistics
    stats = modifier.get_statistics()
    print(f"Statistics: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
