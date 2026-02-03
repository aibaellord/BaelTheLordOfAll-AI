"""
BAEL - Ultra Comfort Automation System
The most advanced user comfort and convenience automation system.

This system focuses on YOUR comfort and ease of use with features like:
1. Predictive task completion - knows what you want before you ask
2. Voice command integration
3. Natural language workflow creation
4. Automatic environment setup
5. Smart shortcuts and aliases
6. Context-aware suggestions
7. One-click deployment
8. Automated routine tasks
9. Personal preference learning
10. Stress-free error recovery

Ba'el exists to serve YOU with maximum comfort.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import pickle

logger = logging.getLogger("BAEL.UltraComfort")


class ComfortLevel(Enum):
    """Comfort levels for automation."""
    MINIMAL = 1       # User does most work
    ASSISTED = 2      # Ba'el helps
    AUTOMATED = 3     # Ba'el does most work
    FULLY_AUTOMATED = 4  # Ba'el does everything
    PREDICTIVE = 5    # Ba'el anticipates and acts


class TaskCategory(Enum):
    """Categories of tasks for comfort automation."""
    DEVELOPMENT = "development"
    DEPLOYMENT = "deployment"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    FILE_MANAGEMENT = "file_management"
    SYSTEM_ADMIN = "system_admin"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    LEARNING = "learning"
    GENERAL = "general"


@dataclass
class UserPreference:
    """User preference for comfort automation."""
    preference_id: str
    category: str
    key: str
    value: Any
    learned_from: str = "explicit"  # explicit, inferred, observed
    confidence: float = 1.0
    usage_count: int = 0
    last_used: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ComfortShortcut:
    """A comfort shortcut for quick actions."""
    shortcut_id: str
    name: str
    description: str
    trigger: str  # Command or phrase that triggers it
    
    # Action
    action_type: str  # command, workflow, script, api
    action_data: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    category: TaskCategory = TaskCategory.GENERAL
    requires_confirmation: bool = False
    
    # Learning
    usage_count: int = 0
    success_count: int = 0
    avg_time_saved_seconds: float = 0.0


@dataclass
class PredictedTask:
    """A predicted task based on user patterns."""
    task_id: str
    description: str
    predicted_time: datetime
    confidence: float
    
    # Action
    action: Dict[str, Any] = field(default_factory=dict)
    auto_execute: bool = False
    
    # Reasoning
    pattern_source: str = ""
    similar_past_tasks: List[str] = field(default_factory=list)


@dataclass 
class ComfortRoutine:
    """An automated routine for recurring tasks."""
    routine_id: str
    name: str
    description: str
    
    # Schedule
    schedule_type: str  # time, trigger, interval
    schedule_value: Any = None
    
    # Steps
    steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # State
    is_active: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    
    # Recovery
    on_error: str = "notify"  # notify, retry, skip, rollback


class UserPatternLearner:
    """Learns user patterns for predictive automation."""
    
    def __init__(self, storage_path: str = "./data/user_patterns"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._actions: List[Dict[str, Any]] = []
        self._patterns: Dict[str, Any] = {}
        self._preferences: Dict[str, UserPreference] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load learned data from disk."""
        patterns_file = self.storage_path / "patterns.pkl"
        if patterns_file.exists():
            try:
                with open(patterns_file, "rb") as f:
                    data = pickle.load(f)
                    self._actions = data.get("actions", [])
                    self._patterns = data.get("patterns", {})
                    self._preferences = data.get("preferences", {})
            except:
                pass
    
    def _save_data(self):
        """Save learned data to disk."""
        patterns_file = self.storage_path / "patterns.pkl"
        with open(patterns_file, "wb") as f:
            pickle.dump({
                "actions": self._actions[-1000:],  # Keep last 1000 actions
                "patterns": self._patterns,
                "preferences": self._preferences
            }, f)
    
    def record_action(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ):
        """Record a user action for pattern learning."""
        action = {
            "type": action_type,
            "data": action_data,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
            "hour": datetime.utcnow().hour,
            "day_of_week": datetime.utcnow().weekday()
        }
        self._actions.append(action)
        
        # Update patterns
        self._update_patterns(action)
        
        # Save periodically
        if len(self._actions) % 10 == 0:
            self._save_data()
    
    def _update_patterns(self, action: Dict[str, Any]):
        """Update patterns based on new action."""
        action_type = action["type"]
        hour = action["hour"]
        day = action["day_of_week"]
        
        # Time-based patterns
        time_key = f"time:{hour}"
        if time_key not in self._patterns:
            self._patterns[time_key] = {}
        if action_type not in self._patterns[time_key]:
            self._patterns[time_key][action_type] = 0
        self._patterns[time_key][action_type] += 1
        
        # Day-based patterns
        day_key = f"day:{day}"
        if day_key not in self._patterns:
            self._patterns[day_key] = {}
        if action_type not in self._patterns[day_key]:
            self._patterns[day_key][action_type] = 0
        self._patterns[day_key][action_type] += 1
        
        # Sequence patterns
        if len(self._actions) > 1:
            prev_action = self._actions[-2]["type"]
            seq_key = f"seq:{prev_action}"
            if seq_key not in self._patterns:
                self._patterns[seq_key] = {}
            if action_type not in self._patterns[seq_key]:
                self._patterns[seq_key][action_type] = 0
            self._patterns[seq_key][action_type] += 1
    
    def predict_next_action(self, context: Dict[str, Any] = None) -> List[PredictedTask]:
        """Predict likely next actions based on patterns."""
        predictions = []
        now = datetime.utcnow()
        
        # Time-based prediction
        time_key = f"time:{now.hour}"
        if time_key in self._patterns:
            for action_type, count in sorted(
                self._patterns[time_key].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]:
                confidence = min(0.9, count / 20)  # Max 90% confidence
                predictions.append(PredictedTask(
                    task_id=f"pred_{hashlib.md5(f'{action_type}{now}'.encode()).hexdigest()[:8]}",
                    description=f"You often do '{action_type}' around this time",
                    predicted_time=now,
                    confidence=confidence,
                    action={"type": action_type},
                    pattern_source="time_pattern"
                ))
        
        # Sequence-based prediction
        if self._actions:
            last_action = self._actions[-1]["type"]
            seq_key = f"seq:{last_action}"
            if seq_key in self._patterns:
                for action_type, count in sorted(
                    self._patterns[seq_key].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:2]:
                    confidence = min(0.85, count / 15)
                    predictions.append(PredictedTask(
                        task_id=f"pred_{hashlib.md5(f'{action_type}{last_action}'.encode()).hexdigest()[:8]}",
                        description=f"After '{last_action}', you often do '{action_type}'",
                        predicted_time=now,
                        confidence=confidence,
                        action={"type": action_type},
                        pattern_source="sequence_pattern"
                    ))
        
        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        return predictions[:5]
    
    def set_preference(
        self,
        category: str,
        key: str,
        value: Any,
        learned: bool = False
    ):
        """Set a user preference."""
        pref_id = f"pref_{category}_{key}"
        self._preferences[pref_id] = UserPreference(
            preference_id=pref_id,
            category=category,
            key=key,
            value=value,
            learned_from="inferred" if learned else "explicit",
            confidence=0.7 if learned else 1.0
        )
        self._save_data()
    
    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        pref_id = f"pref_{category}_{key}"
        pref = self._preferences.get(pref_id)
        if pref:
            pref.usage_count += 1
            pref.last_used = datetime.utcnow()
            return pref.value
        return default


class ComfortCommandRunner:
    """Runs commands with maximum user comfort."""
    
    def __init__(self):
        self._history: List[Dict[str, Any]] = []
        self._aliases: Dict[str, str] = {}
        self._auto_fixes: Dict[str, str] = {}
        
        self._load_common_fixes()
    
    def _load_common_fixes(self):
        """Load common command fixes."""
        self._auto_fixes = {
            # Git typos
            "gti": "git",
            "got": "git",
            "gut": "git",
            # Python typos
            "pytohn": "python",
            "pyhton": "python",
            "pythno": "python",
            # npm typos
            "nmp": "npm",
            "nmpm": "npm",
            # Common mistakes
            "sl": "ls",
            "cd..": "cd ..",
            "ccd": "cd",
        }
    
    def add_alias(self, alias: str, command: str):
        """Add a comfort alias."""
        self._aliases[alias] = command
    
    async def run(
        self,
        command: str,
        auto_fix: bool = True,
        explain_errors: bool = True,
        suggest_alternatives: bool = True
    ) -> Dict[str, Any]:
        """Run a command with comfort features."""
        original_command = command
        
        # Auto-fix typos
        if auto_fix:
            command = self._fix_typos(command)
        
        # Expand aliases
        command = self._expand_aliases(command)
        
        # Run command
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            output = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "command": command,
                "original_command": original_command if command != original_command else None
            }
            
            # Handle errors with comfort
            if not output["success"] and explain_errors:
                output["error_explanation"] = self._explain_error(result.stderr, command)
                if suggest_alternatives:
                    output["suggestions"] = self._suggest_fixes(result.stderr, command)
            
            self._history.append({
                "command": command,
                "success": output["success"],
                "time": datetime.utcnow().isoformat()
            })
            
            return output
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 5 minutes",
                "command": command,
                "suggestions": ["Try running with a longer timeout", "Check if the process is stuck"]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }
    
    def _fix_typos(self, command: str) -> str:
        """Fix common command typos."""
        words = command.split()
        if words and words[0] in self._auto_fixes:
            words[0] = self._auto_fixes[words[0]]
            return " ".join(words)
        return command
    
    def _expand_aliases(self, command: str) -> str:
        """Expand comfort aliases."""
        words = command.split()
        if words and words[0] in self._aliases:
            words[0] = self._aliases[words[0]]
            return " ".join(words)
        return command
    
    def _explain_error(self, stderr: str, command: str) -> str:
        """Explain error in user-friendly terms."""
        stderr_lower = stderr.lower()
        
        if "command not found" in stderr_lower:
            cmd = command.split()[0] if command.split() else "command"
            return f"The command '{cmd}' is not installed or not in your PATH."
        
        if "permission denied" in stderr_lower:
            return "You don't have permission to perform this action. Try using 'sudo' or check file permissions."
        
        if "no such file or directory" in stderr_lower:
            return "The file or directory you specified doesn't exist. Check the path and try again."
        
        if "connection refused" in stderr_lower:
            return "Cannot connect to the service. It might not be running or the address is wrong."
        
        if "timeout" in stderr_lower:
            return "The operation took too long. Check your network connection or try again later."
        
        return f"An error occurred: {stderr[:200]}..."
    
    def _suggest_fixes(self, stderr: str, command: str) -> List[str]:
        """Suggest fixes for common errors."""
        suggestions = []
        stderr_lower = stderr.lower()
        
        if "command not found" in stderr_lower:
            cmd = command.split()[0] if command.split() else ""
            suggestions.append(f"Install {cmd} using your package manager")
            suggestions.append(f"Check if {cmd} is in a different location")
            suggestions.append("Make sure your PATH is configured correctly")
        
        if "permission denied" in stderr_lower:
            suggestions.append(f"Try: sudo {command}")
            suggestions.append("Check file permissions with: ls -la")
            suggestions.append("Change permissions with: chmod")
        
        if "no such file" in stderr_lower:
            suggestions.append("Check if the path is correct")
            suggestions.append("Use 'ls' to see available files")
            suggestions.append("Create the file/directory if needed")
        
        return suggestions


class OneClickDeployer:
    """One-click deployment for maximum comfort."""
    
    def __init__(self):
        self._deployment_configs: Dict[str, Dict[str, Any]] = {}
    
    def register_deployment(
        self,
        name: str,
        config: Dict[str, Any]
    ):
        """Register a deployment configuration."""
        self._deployment_configs[name] = config
    
    async def deploy(
        self,
        name: str,
        environment: str = "production",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute one-click deployment."""
        if name not in self._deployment_configs:
            return {"success": False, "error": f"Deployment '{name}' not found"}
        
        config = self._deployment_configs[name]
        
        steps_completed = []
        errors = []
        
        for step in config.get("steps", []):
            step_name = step.get("name", "unnamed")
            step_type = step.get("type", "command")
            
            if dry_run:
                steps_completed.append({
                    "step": step_name,
                    "status": "dry_run",
                    "would_execute": step.get("command", step.get("action"))
                })
                continue
            
            try:
                if step_type == "command":
                    result = subprocess.run(
                        step["command"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    steps_completed.append({
                        "step": step_name,
                        "status": "success" if result.returncode == 0 else "failed",
                        "output": result.stdout,
                        "error": result.stderr if result.returncode != 0 else None
                    })
                    
                    if result.returncode != 0 and not step.get("allow_failure"):
                        errors.append(f"Step '{step_name}' failed: {result.stderr}")
                        break
                        
            except Exception as e:
                errors.append(f"Step '{step_name}' error: {str(e)}")
                if not step.get("allow_failure"):
                    break
        
        return {
            "success": len(errors) == 0,
            "deployment": name,
            "environment": environment,
            "steps_completed": steps_completed,
            "errors": errors,
            "dry_run": dry_run
        }


class UltraComfortAutomation:
    """
    Main interface for ultra comfort automation.
    
    Provides:
    1. Predictive task completion
    2. Smart command running with auto-fix
    3. One-click deployments
    4. Routine automation
    5. User preference learning
    6. Context-aware suggestions
    """
    
    def __init__(
        self,
        storage_path: str = "./data/comfort",
        comfort_level: ComfortLevel = ComfortLevel.AUTOMATED
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.comfort_level = comfort_level
        
        self.pattern_learner = UserPatternLearner(str(self.storage_path / "patterns"))
        self.command_runner = ComfortCommandRunner()
        self.deployer = OneClickDeployer()
        
        # Shortcuts
        self._shortcuts: Dict[str, ComfortShortcut] = {}
        self._routines: Dict[str, ComfortRoutine] = {}
        
        # Initialize default shortcuts
        self._setup_default_shortcuts()
        
        logger.info(f"UltraComfortAutomation initialized with level: {comfort_level.name}")
    
    def _setup_default_shortcuts(self):
        """Setup default comfort shortcuts."""
        defaults = [
            ComfortShortcut(
                shortcut_id="quick_git_push",
                name="Quick Git Push",
                description="Add all, commit, and push in one command",
                trigger="push all",
                action_type="command",
                action_data={
                    "command": "git add -A && git commit -m 'Quick commit' && git push"
                },
                category=TaskCategory.DEVELOPMENT
            ),
            ComfortShortcut(
                shortcut_id="quick_clean",
                name="Quick Clean",
                description="Clean up common temporary files",
                trigger="clean up",
                action_type="command",
                action_data={
                    "command": "find . -name '*.pyc' -delete && find . -name '__pycache__' -type d -delete && find . -name '.DS_Store' -delete"
                },
                category=TaskCategory.FILE_MANAGEMENT
            ),
            ComfortShortcut(
                shortcut_id="quick_status",
                name="Quick Status",
                description="Show git status and recent log",
                trigger="status",
                action_type="command",
                action_data={
                    "command": "git status && echo '---' && git log --oneline -5"
                },
                category=TaskCategory.DEVELOPMENT
            )
        ]
        
        for shortcut in defaults:
            self._shortcuts[shortcut.shortcut_id] = shortcut
    
    async def do(self, natural_command: str) -> Dict[str, Any]:
        """Execute a natural language command with maximum comfort."""
        # Record action for learning
        self.pattern_learner.record_action(
            action_type="command",
            action_data={"input": natural_command}
        )
        
        # Check for shortcuts
        for shortcut in self._shortcuts.values():
            if shortcut.trigger.lower() in natural_command.lower():
                return await self._execute_shortcut(shortcut)
        
        # Check if it's a direct command
        if natural_command.startswith("!"):
            return await self.command_runner.run(natural_command[1:])
        
        # Interpret natural language
        interpreted = self._interpret_natural_command(natural_command)
        
        if interpreted:
            return await self.command_runner.run(interpreted)
        
        return {
            "success": False,
            "error": "Could not understand command",
            "suggestions": await self.get_suggestions(natural_command)
        }
    
    def _interpret_natural_command(self, command: str) -> Optional[str]:
        """Interpret natural language command."""
        command_lower = command.lower()
        
        # Common patterns
        patterns = {
            r"show (me )?files": "ls -la",
            r"list files": "ls -la",
            r"show git status": "git status",
            r"what (files )?changed": "git diff --name-only",
            r"go to (.+)": lambda m: f"cd {m.group(1)}",
            r"create file (.+)": lambda m: f"touch {m.group(1)}",
            r"delete (.+)": lambda m: f"rm -i {m.group(1)}",
            r"find (.+)": lambda m: f"find . -name '*{m.group(1)}*'",
            r"search for (.+) in (.+)": lambda m: f"grep -r '{m.group(1)}' {m.group(2)}",
            r"install (.+)": lambda m: f"pip install {m.group(1)}",
            r"run (.+)": lambda m: m.group(1),
            r"open (.+)": lambda m: f"open {m.group(1)}",
        }
        
        for pattern, action in patterns.items():
            match = re.search(pattern, command_lower)
            if match:
                if callable(action):
                    return action(match)
                return action
        
        return None
    
    async def _execute_shortcut(self, shortcut: ComfortShortcut) -> Dict[str, Any]:
        """Execute a comfort shortcut."""
        shortcut.usage_count += 1
        
        if shortcut.action_type == "command":
            return await self.command_runner.run(shortcut.action_data["command"])
        
        return {"success": False, "error": f"Unknown action type: {shortcut.action_type}"}
    
    async def get_suggestions(self, context: str = "") -> List[str]:
        """Get context-aware suggestions."""
        suggestions = []
        
        # Get predicted tasks
        predictions = self.pattern_learner.predict_next_action()
        for pred in predictions[:3]:
            suggestions.append(f"Based on your pattern: {pred.description}")
        
        # Time-based suggestions
        hour = datetime.utcnow().hour
        if 8 <= hour < 10:
            suggestions.append("Start of day: Check git status and emails?")
        elif 11 <= hour < 13:
            suggestions.append("Midday: Time to review and commit changes?")
        elif 16 <= hour < 18:
            suggestions.append("End of day: Push all changes and update docs?")
        
        return suggestions
    
    def add_shortcut(
        self,
        name: str,
        trigger: str,
        command: str,
        description: str = ""
    ) -> ComfortShortcut:
        """Add a new comfort shortcut."""
        shortcut_id = f"shortcut_{hashlib.md5(trigger.encode()).hexdigest()[:8]}"
        
        shortcut = ComfortShortcut(
            shortcut_id=shortcut_id,
            name=name,
            description=description or f"Shortcut for: {command}",
            trigger=trigger,
            action_type="command",
            action_data={"command": command}
        )
        
        self._shortcuts[shortcut_id] = shortcut
        return shortcut
    
    async def create_routine(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        schedule: str = "manual"
    ) -> ComfortRoutine:
        """Create an automated routine."""
        routine_id = f"routine_{hashlib.md5(name.encode()).hexdigest()[:8]}"
        
        routine = ComfortRoutine(
            routine_id=routine_id,
            name=name,
            description=description,
            schedule_type=schedule,
            steps=steps
        )
        
        self._routines[routine_id] = routine
        return routine
    
    async def run_routine(self, routine_id: str) -> Dict[str, Any]:
        """Run a routine."""
        if routine_id not in self._routines:
            return {"success": False, "error": f"Routine '{routine_id}' not found"}
        
        routine = self._routines[routine_id]
        results = []
        
        for step in routine.steps:
            if step.get("type") == "command":
                result = await self.command_runner.run(step["command"])
                results.append({
                    "step": step.get("name", "unnamed"),
                    "result": result
                })
                
                if not result.get("success") and step.get("stop_on_error", True):
                    break
        
        routine.last_run = datetime.utcnow()
        routine.run_count += 1
        
        return {
            "success": all(r.get("result", {}).get("success") for r in results),
            "routine": routine.name,
            "steps": results
        }
    
    def set_preference(self, category: str, key: str, value: Any):
        """Set a user preference for comfort automation."""
        self.pattern_learner.set_preference(category, key, value)
    
    def get_preference(self, category: str, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.pattern_learner.get_preference(category, key, default)
    
    def list_shortcuts(self) -> List[Dict[str, Any]]:
        """List all available shortcuts."""
        return [
            {
                "id": s.shortcut_id,
                "name": s.name,
                "trigger": s.trigger,
                "description": s.description,
                "usage_count": s.usage_count
            }
            for s in self._shortcuts.values()
        ]
    
    def list_routines(self) -> List[Dict[str, Any]]:
        """List all routines."""
        return [
            {
                "id": r.routine_id,
                "name": r.name,
                "description": r.description,
                "steps": len(r.steps),
                "run_count": r.run_count,
                "last_run": r.last_run.isoformat() if r.last_run else None
            }
            for r in self._routines.values()
        ]


# Singleton
_comfort_automation: Optional[UltraComfortAutomation] = None


def get_comfort_automation() -> UltraComfortAutomation:
    """Get the global comfort automation instance."""
    global _comfort_automation
    if _comfort_automation is None:
        _comfort_automation = UltraComfortAutomation()
    return _comfort_automation


async def demo():
    """Demonstrate comfort automation."""
    comfort = get_comfort_automation()
    
    print("Ultra Comfort Automation Demo")
    print("=" * 50)
    
    # Show shortcuts
    print("\nAvailable Shortcuts:")
    for shortcut in comfort.list_shortcuts():
        print(f"  - '{shortcut['trigger']}': {shortcut['description']}")
    
    # Get suggestions
    print("\nCurrent Suggestions:")
    suggestions = await comfort.get_suggestions()
    for sug in suggestions:
        print(f"  - {sug}")
    
    # Add custom shortcut
    print("\nAdding custom shortcut...")
    comfort.add_shortcut(
        name="Check Python",
        trigger="check python",
        command="python --version && pip --version",
        description="Check Python and pip versions"
    )
    
    # Run a natural command
    print("\nRunning natural command: 'show files'")
    result = await comfort.do("show files")
    print(f"Success: {result.get('success')}")
    if result.get('stdout'):
        print(f"Output:\n{result['stdout'][:200]}...")


if __name__ == "__main__":
    asyncio.run(demo())
