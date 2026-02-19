"""
BAEL Dynamic Tool Forge
========================

Runtime tool generation and self-modification system.
Enables automatic tool creation from natural language.

Components:
- ToolGenerator: Creates tools from descriptions
- ToolRegistry: Dynamic tool registration
- CodeSynthesizer: Code generation for tools
- ToolValidator: Safety and correctness checking
- SelfModifier: Self-modification capabilities
- ToolOptimizer: Performance optimization
"""

from .code_synthesizer import (CodeSynthesizer, CodeTemplate, ParameterSpec,
                               SynthesisResult)
from .self_modifier import (Modification, ModificationType, RollbackPoint,
                            SelfModifier)
from .tool_generator import (GeneratedTool, ToolGenerator, ToolSpec,
                             ToolTemplate)
from .tool_optimizer import (OptimizationResult, OptimizationStrategy,
                             PerformanceProfile, ToolOptimizer)
from .tool_registry import (RegisteredTool, ToolCategory, ToolMetadata,
                            ToolRegistry)
from .tool_validator import (SafetyCheck, SecurityLevel, ToolValidator,
                             ValidationResult)

__all__ = [
    # Generator
    "ToolGenerator",
    "ToolSpec",
    "ToolTemplate",
    "GeneratedTool",
    # Registry
    "ToolRegistry",
    "RegisteredTool",
    "ToolCategory",
    "ToolMetadata",
    # Synthesizer
    "CodeSynthesizer",
    "SynthesisResult",
    "CodeTemplate",
    "ParameterSpec",
    # Validator
    "ToolValidator",
    "ValidationResult",
    "SafetyCheck",
    "SecurityLevel",
    # Modifier
    "SelfModifier",
    "Modification",
    "ModificationType",
    "RollbackPoint",
    # Optimizer
    "ToolOptimizer",
    "OptimizationResult",
    "PerformanceProfile",
    "OptimizationStrategy",
]
