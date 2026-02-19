"""
🏆 COMPETITOR SURPASS MODULE
============================
Implements ALL capabilities that any competitor has,
ensuring BAEL is definitively superior.

This module fills every gap identified in our competitor analysis:
- AutoGPT's visual workflow → Visual DAG Builder
- LangGraph's durable execution → Checkpoint System
- CrewAI's role templates → Role Library
- MetaGPT's SOP generation → Procedure Generator
- Agent Zero's organic learning → Adaptive Learning
- OpenDevin's sandbox → Enhanced Sandbox
- BabyAGI's self-building → Function Synthesis
- Claude CU's vision control → Vision Controller
- Manus.im's autonomy → Full Autonomy Engine
"""

from .visual_workflow import VisualWorkflowBuilder
from .durable_execution import DurableExecutionEngine, Checkpoint
from .role_library import RoleLibrary, Role
from .procedure_generator import ProcedureGenerator, SOP
from .adaptive_learning import AdaptiveLearningEngine
from .enhanced_sandbox import EnhancedSandbox
from .function_synthesis import FunctionSynthesizer
from .vision_controller import VisionController
from .full_autonomy import (
    FullAutonomyEngine,
    AutonomousGoal,
    AutonomousTask,
    AutonomousDecision,
    ExecutionSession,
    Resource,
    AutonomyLevel,
    GoalStatus,
    TaskPriority,
    DecisionType,
    GoalPlanner,
    TaskExecutor,
    DecisionEngine,
    SafetyMonitor
)

__all__ = [
    # Visual Workflow (AutoGPT)
    'VisualWorkflowBuilder',

    # Durable Execution (LangGraph)
    'DurableExecutionEngine',
    'Checkpoint',

    # Role Library (CrewAI)
    'RoleLibrary',
    'Role',

    # Procedure Generator (MetaGPT)
    'ProcedureGenerator',
    'SOP',

    # Adaptive Learning (Agent Zero)
    'AdaptiveLearningEngine',

    # Enhanced Sandbox (OpenDevin)
    'EnhancedSandbox',

    # Function Synthesis (BabyAGI)
    'FunctionSynthesizer',

    # Vision Controller (Claude Computer Use)
    'VisionController',

    # Full Autonomy (Manus.im)
    'FullAutonomyEngine',
    'AutonomousGoal',
    'AutonomousTask',
    'AutonomousDecision',
    'ExecutionSession',
    'Resource',
    'AutonomyLevel',
    'GoalStatus',
    'TaskPriority',
    'DecisionType',
    'GoalPlanner',
    'TaskExecutor',
    'DecisionEngine',
    'SafetyMonitor'
]
