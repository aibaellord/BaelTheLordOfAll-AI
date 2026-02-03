"""
BAEL - VS Code / Copilot Integration
Enables BAEL to integrate with VS Code and GitHub Copilot.

This module provides:
- VS Code extension communication
- Copilot Chat integration
- Editor state awareness
- Workspace integration
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("BAEL.VSCode")


# =============================================================================
# TYPES & ENUMS
# =============================================================================

class EditorEventType(Enum):
    """Types of editor events."""
    FILE_OPENED = "file_opened"
    FILE_SAVED = "file_saved"
    FILE_CLOSED = "file_closed"
    SELECTION_CHANGED = "selection_changed"
    CURSOR_MOVED = "cursor_moved"
    TEXT_CHANGED = "text_changed"
    DIAGNOSTIC = "diagnostic"
    TERMINAL_OUTPUT = "terminal_output"


@dataclass
class EditorContext:
    """Current editor context."""
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    content: Optional[str] = None
    selection: Optional[str] = None
    cursor_line: int = 0
    cursor_column: int = 0
    visible_range: Optional[Dict[str, int]] = None
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    workspace_root: Optional[str] = None
    open_files: List[str] = field(default_factory=list)


@dataclass
class CopilotMessage:
    """Message from/to Copilot."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# VS CODE INTEGRATION
# =============================================================================

class VSCodeIntegration:
    """Integration with VS Code editor."""

    def __init__(self, brain=None):
        self.brain = brain
        self.context = EditorContext()
        self._event_handlers: Dict[EditorEventType, List[Callable]] = {}
        self._connected = False

    async def connect(self, port: int = 9999) -> bool:
        """Connect to VS Code extension host."""
        # In a real implementation, this would establish
        # WebSocket connection to VS Code extension
        logger.info(f"Connecting to VS Code on port {port}")
        self._connected = True
        return True

    def on_event(self, event_type: EditorEventType, handler: Callable) -> None:
        """Register event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def _emit_event(self, event_type: EditorEventType, data: Dict[str, Any]) -> None:
        """Emit event to handlers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error: {e}")

    def update_context(self, context_data: Dict[str, Any]) -> None:
        """Update editor context."""
        for key, value in context_data.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)

    async def get_file_content(self, path: str) -> Optional[str]:
        """Get content of a file."""
        try:
            file_path = Path(path)
            if file_path.exists():
                return file_path.read_text()
        except Exception as e:
            logger.error(f"Error reading file: {e}")
        return None

    async def get_workspace_files(self, pattern: str = "**/*") -> List[str]:
        """Get files in workspace matching pattern."""
        files = []
        if self.context.workspace_root:
            root = Path(self.context.workspace_root)
            files = [str(f) for f in root.glob(pattern) if f.is_file()]
        return files

    async def execute_command(self, command: str, args: List[Any] = None) -> Any:
        """Execute VS Code command."""
        logger.info(f"Executing VS Code command: {command}")
        # In real implementation, send to VS Code extension
        return {"success": True, "command": command}

    async def show_message(self, message: str, level: str = "info") -> None:
        """Show message in VS Code."""
        logger.info(f"VS Code message ({level}): {message}")

    async def open_file(self, path: str, line: int = None) -> bool:
        """Open file in editor."""
        logger.info(f"Opening file: {path}")
        return True

    async def insert_text(self, text: str, position: Dict[str, int] = None) -> bool:
        """Insert text at position."""
        logger.info(f"Inserting text at {position}")
        return True

    async def get_diagnostics(self, path: str = None) -> List[Dict[str, Any]]:
        """Get diagnostics/errors from VS Code."""
        return self.context.diagnostics


# =============================================================================
# COPILOT INTEGRATION
# =============================================================================

class CopilotIntegration:
    """Integration with GitHub Copilot Chat."""

    def __init__(self, brain=None, vscode: VSCodeIntegration = None):
        self.brain = brain
        self.vscode = vscode or VSCodeIntegration(brain)
        self.conversation: List[CopilotMessage] = []
        self._active = False

    async def activate(self) -> bool:
        """Activate Copilot integration."""
        self._active = True
        logger.info("Copilot integration activated")
        return True

    async def process_message(self, message: str, context: Dict[str, Any] = None) -> str:
        """Process incoming Copilot message."""
        # Store user message
        self.conversation.append(CopilotMessage(
            role="user",
            content=message,
            metadata=context or {}
        ))

        # Enhance context with editor info
        enhanced_context = self._build_context(context)

        # Process with BAEL brain
        if self.brain:
            result = await self.brain.think(message, enhanced_context)
            response = result.get("response", "")
        else:
            response = await self._fallback_response(message)

        # Store assistant response
        self.conversation.append(CopilotMessage(
            role="assistant",
            content=response
        ))

        return response

    def _build_context(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build enhanced context."""
        enhanced = context.copy() if context else {}

        # Add editor context
        enhanced["editor"] = {
            "file_path": self.vscode.context.file_path,
            "file_type": self.vscode.context.file_type,
            "selection": self.vscode.context.selection,
            "cursor_line": self.vscode.context.cursor_line,
            "workspace_root": self.vscode.context.workspace_root,
            "diagnostics": self.vscode.context.diagnostics
        }

        # Add conversation history
        enhanced["conversation_history"] = [
            {"role": m.role, "content": m.content[:500]}
            for m in self.conversation[-10:]  # Last 10 messages
        ]

        return enhanced

    async def _fallback_response(self, message: str) -> str:
        """Fallback response when brain not available."""
        return f"I received your message: {message}\nHowever, BAEL brain is not initialized."

    async def provide_completion(self, prefix: str, suffix: str, context: Dict[str, Any] = None) -> List[str]:
        """Provide code completions."""
        if not self.brain:
            return []

        prompt = f"""Provide code completions for:

Prefix (before cursor):
{prefix}

Suffix (after cursor):
{suffix}

File type: {self.vscode.context.file_type or 'unknown'}

Provide 3-5 possible completions, one per line."""

        result = await self.brain.think(prompt, context)
        response = result.get("response", "")

        # Parse completions
        completions = [line.strip() for line in response.split("\n") if line.strip()]
        return completions[:5]

    async def explain_code(self, code: str, language: str = None) -> str:
        """Explain selected code."""
        if not self.brain:
            return "Brain not initialized"

        prompt = f"""Explain this {language or 'code'} in detail:

```{language or ''}
{code}
```

Provide:
1. What this code does
2. How it works step by step
3. Key concepts used
4. Potential improvements"""

        result = await self.brain.think(prompt)
        return result.get("response", "")

    async def fix_code(self, code: str, error: str = None, language: str = None) -> str:
        """Fix code issues."""
        if not self.brain:
            return "Brain not initialized"

        prompt = f"""Fix this {language or 'code'}:

```{language or ''}
{code}
```

{f'Error: {error}' if error else 'Find and fix any issues.'}

Provide the corrected code with explanations."""

        result = await self.brain.think(prompt)
        return result.get("response", "")

    async def generate_tests(self, code: str, language: str = None) -> str:
        """Generate tests for code."""
        if not self.brain:
            return "Brain not initialized"

        prompt = f"""Generate comprehensive tests for this {language or 'code'}:

```{language or ''}
{code}
```

Include:
1. Unit tests for each function/method
2. Edge cases
3. Error handling tests
4. Integration tests if applicable"""

        result = await self.brain.think(prompt)
        return result.get("response", "")

    async def refactor_code(self, code: str, instruction: str = None, language: str = None) -> str:
        """Refactor code."""
        if not self.brain:
            return "Brain not initialized"

        prompt = f"""Refactor this {language or 'code'}:

```{language or ''}
{code}
```

{f'Instruction: {instruction}' if instruction else 'Improve code quality, readability, and performance.'}

Provide refactored code with explanations."""

        result = await self.brain.think(prompt)
        return result.get("response", "")

    async def document_code(self, code: str, language: str = None) -> str:
        """Generate documentation for code."""
        if not self.brain:
            return "Brain not initialized"

        prompt = f"""Generate documentation for this {language or 'code'}:

```{language or ''}
{code}
```

Include:
1. Module/class docstrings
2. Function/method documentation
3. Parameter descriptions
4. Return value descriptions
5. Usage examples"""

        result = await self.brain.think(prompt)
        return result.get("response", "")


# =============================================================================
# CURSOR INTEGRATION
# =============================================================================

class CursorIntegration:
    """Integration with Cursor editor."""

    def __init__(self, brain=None):
        self.brain = brain
        self.vscode = VSCodeIntegration(brain)  # Cursor is VSCode-based
        self.copilot = CopilotIntegration(brain, self.vscode)

    async def activate(self) -> bool:
        """Activate Cursor integration."""
        await self.copilot.activate()
        logger.info("Cursor integration activated")
        return True

    async def process_chat(self, message: str, context: Dict[str, Any] = None) -> str:
        """Process Cursor chat message."""
        return await self.copilot.process_message(message, context)

    async def composer_mode(self, instruction: str, files: List[str] = None) -> Dict[str, str]:
        """Cursor Composer-style multi-file editing."""
        if not self.brain:
            return {"error": "Brain not initialized"}

        # Read relevant files
        file_contents = {}
        for file_path in (files or []):
            content = await self.vscode.get_file_content(file_path)
            if content:
                file_contents[file_path] = content

        prompt = f"""Multi-file editing task: {instruction}

Files to consider:
{chr(10).join(f'--- {path} ---{chr(10)}{content[:1000]}' for path, content in file_contents.items())}

Provide changes for each file that needs modification.
Format: For each file, show the complete updated content."""

        result = await self.brain.think(prompt)

        return {
            "instruction": instruction,
            "response": result.get("response", ""),
            "files_analyzed": list(file_contents.keys())
        }


# =============================================================================
# INTEGRATION MANAGER
# =============================================================================

class IntegrationManager:
    """Manages all editor integrations."""

    def __init__(self, brain=None):
        self.brain = brain
        self.vscode = VSCodeIntegration(brain)
        self.copilot = CopilotIntegration(brain, self.vscode)
        self.cursor = CursorIntegration(brain)

        self._active_integration: Optional[str] = None

    async def detect_environment(self) -> Optional[str]:
        """Detect current editor environment."""
        # Check for environment variables or connection attempts
        # In reality, this would check for specific markers

        # For now, default to vscode
        return "vscode"

    async def activate(self, integration: str = None) -> bool:
        """Activate appropriate integration."""
        if not integration:
            integration = await self.detect_environment()

        if integration == "vscode":
            await self.vscode.connect()
            await self.copilot.activate()
            self._active_integration = "vscode"

        elif integration == "cursor":
            await self.cursor.activate()
            self._active_integration = "cursor"

        else:
            logger.warning(f"Unknown integration: {integration}")
            return False

        logger.info(f"Activated {integration} integration")
        return True

    async def process_message(self, message: str, context: Dict[str, Any] = None) -> str:
        """Process message using active integration."""
        if self._active_integration == "vscode":
            return await self.copilot.process_message(message, context)
        elif self._active_integration == "cursor":
            return await self.cursor.process_chat(message, context)
        else:
            return "No active integration"

    def get_context(self) -> EditorContext:
        """Get current editor context."""
        return self.vscode.context


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Test integrations."""
    manager = IntegrationManager()

    await manager.activate("vscode")

    print("Integration Manager Active")
    print(f"Active: {manager._active_integration}")

    # Test message processing
    response = await manager.process_message("Explain async/await in Python")
    print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())
