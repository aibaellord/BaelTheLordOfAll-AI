"""
BAEL Engine Factory System
===========================

Self-creating engine generation and management.
Enables BAEL to create new capabilities autonomously.

Components:
- EngineGenerator: Generate new engines from specs
- TemplateEngine: Engine templates and patterns
- CodeSynthesizer: AI-powered code generation
- EngineValidator: Validate generated engines
- SelfImproving: Self-improvement capabilities
"""

from .code_synthesizer import (CodeQuality, CodeSynthesizer, SynthesisConfig,
                               SynthesizedCode)
from .engine_generator import (EngineGenerator, EngineSpec, GeneratedEngine,
                               GenerationConfig)
from .engine_validator import (EngineValidator, ValidationLevel,
                               ValidationResult, ValidationRule)
from .self_improving import (ImprovementMetrics, LearningConfig, Optimization,
                             SelfImprovingEngine)
from .template_engine import (EngineTemplate, TemplateCategory, TemplateEngine,
                              TemplateVariable)

__all__ = [
    # Engine Generator
    "EngineGenerator",
    "EngineSpec",
    "GeneratedEngine",
    "GenerationConfig",
    # Template Engine
    "TemplateEngine",
    "EngineTemplate",
    "TemplateVariable",
    "TemplateCategory",
    # Code Synthesizer
    "CodeSynthesizer",
    "SynthesisConfig",
    "SynthesizedCode",
    "CodeQuality",
    # Engine Validator
    "EngineValidator",
    "ValidationResult",
    "ValidationLevel",
    "ValidationRule",
    # Self Improving
    "SelfImprovingEngine",
    "ImprovementMetrics",
    "LearningConfig",
    "Optimization",
]
