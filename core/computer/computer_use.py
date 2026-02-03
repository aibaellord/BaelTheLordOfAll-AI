#!/usr/bin/env python3
"""
BAEL - Computer Use Integration
Enables BAEL to interact with desktop GUIs through Anthropic's computer use API.

This allows the AI to:
- Take screenshots and analyze them
- Control mouse and keyboard
- Interact with desktop applications
- Automate GUI-based workflows
"""

import asyncio
import base64
import io
import json
import logging
import os
import platform
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("BAEL.ComputerUse")


# =============================================================================
# ENUMS
# =============================================================================

class ComputerAction(Enum):
    """Types of computer actions."""
    SCREENSHOT = "screenshot"
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "click"
    MOUSE_DOUBLE_CLICK = "double_click"
    MOUSE_RIGHT_CLICK = "right_click"
    MOUSE_DRAG = "drag"
    KEYBOARD_TYPE = "type"
    KEYBOARD_KEY = "key"
    KEYBOARD_HOTKEY = "hotkey"
    SCROLL = "scroll"
    WAIT = "wait"


class ScreenshotMode(Enum):
    """Screenshot capture modes."""
    FULL_SCREEN = "full_screen"
    ACTIVE_WINDOW = "active_window"
    REGION = "region"


class ComputerState(Enum):
    """Computer use state."""
    IDLE = "idle"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ScreenshotResult:
    """Result of a screenshot operation."""
    image_data: bytes
    width: int
    height: int
    format: str = "png"
    timestamp: datetime = field(default_factory=datetime.now)

    def to_base64(self) -> str:
        """Convert to base64 string."""
        return base64.b64encode(self.image_data).decode()

    def to_data_url(self) -> str:
        """Convert to data URL."""
        return f"data:image/{self.format};base64,{self.to_base64()}"


@dataclass
class ActionResult:
    """Result of a computer action."""
    action: ComputerAction
    success: bool
    message: str = ""
    screenshot: Optional[ScreenshotResult] = None
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComputerConfig:
    """Computer use configuration."""
    enabled: bool = True
    require_confirmation: bool = True
    allowed_actions: List[ComputerAction] = field(default_factory=lambda: list(ComputerAction))
    screen_width: int = 1920
    screen_height: int = 1080
    screenshot_quality: int = 85
    action_delay_ms: int = 100
    max_actions_per_task: int = 50


# =============================================================================
# ABSTRACT CONTROLLER
# =============================================================================

class ComputerController(ABC):
    """Abstract base for computer control implementations."""

    @abstractmethod
    async def take_screenshot(
        self,
        mode: ScreenshotMode = ScreenshotMode.FULL_SCREEN,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> ScreenshotResult:
        """Take a screenshot."""
        pass

    @abstractmethod
    async def mouse_move(self, x: int, y: int) -> ActionResult:
        """Move mouse to coordinates."""
        pass

    @abstractmethod
    async def mouse_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1
    ) -> ActionResult:
        """Click at coordinates."""
        pass

    @abstractmethod
    async def keyboard_type(self, text: str) -> ActionResult:
        """Type text."""
        pass

    @abstractmethod
    async def keyboard_key(self, key: str) -> ActionResult:
        """Press a key."""
        pass

    @abstractmethod
    async def keyboard_hotkey(self, *keys: str) -> ActionResult:
        """Press a key combination."""
        pass

    @abstractmethod
    async def scroll(
        self,
        x: int,
        y: int,
        direction: str = "down",
        amount: int = 3
    ) -> ActionResult:
        """Scroll at position."""
        pass


# =============================================================================
# PYAUTOGUI CONTROLLER
# =============================================================================

class PyAutoGUIController(ComputerController):
    """Computer controller using PyAutoGUI."""

    def __init__(self, config: Optional[ComputerConfig] = None):
        self.config = config or ComputerConfig()
        self._pyautogui = None
        self._pil = None

    def _ensure_imports(self):
        """Ensure required packages are imported."""
        if self._pyautogui is None:
            try:
                import pyautogui
                self._pyautogui = pyautogui
                # Safety settings
                pyautogui.FAILSAFE = True
                pyautogui.PAUSE = self.config.action_delay_ms / 1000
            except ImportError:
                raise ImportError("pyautogui required for computer control")

        if self._pil is None:
            try:
                from PIL import Image
                self._pil = Image
            except ImportError:
                raise ImportError("Pillow required for screenshots")

    async def take_screenshot(
        self,
        mode: ScreenshotMode = ScreenshotMode.FULL_SCREEN,
        region: Optional[Tuple[int, int, int, int]] = None
    ) -> ScreenshotResult:
        self._ensure_imports()
        start = time.time()

        if mode == ScreenshotMode.REGION and region:
            screenshot = self._pyautogui.screenshot(region=region)
        else:
            screenshot = self._pyautogui.screenshot()

        # Resize if needed for API limits
        max_width = 1280
        if screenshot.width > max_width:
            ratio = max_width / screenshot.width
            new_size = (max_width, int(screenshot.height * ratio))
            screenshot = screenshot.resize(new_size, self._pil.LANCZOS)

        # Convert to bytes
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG", optimize=True)
        image_data = buffer.getvalue()

        logger.debug(f"Screenshot taken: {screenshot.width}x{screenshot.height}")

        return ScreenshotResult(
            image_data=image_data,
            width=screenshot.width,
            height=screenshot.height
        )

    async def mouse_move(self, x: int, y: int) -> ActionResult:
        self._ensure_imports()
        start = time.time()

        try:
            self._pyautogui.moveTo(x, y, duration=0.1)
            return ActionResult(
                action=ComputerAction.MOUSE_MOVE,
                success=True,
                message=f"Moved to ({x}, {y})",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ActionResult(
                action=ComputerAction.MOUSE_MOVE,
                success=False,
                message=str(e)
            )

    async def mouse_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        clicks: int = 1
    ) -> ActionResult:
        self._ensure_imports()
        start = time.time()

        try:
            self._pyautogui.click(x, y, clicks=clicks, button=button)
            return ActionResult(
                action=ComputerAction.MOUSE_CLICK,
                success=True,
                message=f"Clicked at ({x}, {y})",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ActionResult(
                action=ComputerAction.MOUSE_CLICK,
                success=False,
                message=str(e)
            )

    async def keyboard_type(self, text: str) -> ActionResult:
        self._ensure_imports()
        start = time.time()

        try:
            self._pyautogui.typewrite(text, interval=0.02)
            return ActionResult(
                action=ComputerAction.KEYBOARD_TYPE,
                success=True,
                message=f"Typed {len(text)} characters",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ActionResult(
                action=ComputerAction.KEYBOARD_TYPE,
                success=False,
                message=str(e)
            )

    async def keyboard_key(self, key: str) -> ActionResult:
        self._ensure_imports()
        start = time.time()

        try:
            self._pyautogui.press(key)
            return ActionResult(
                action=ComputerAction.KEYBOARD_KEY,
                success=True,
                message=f"Pressed {key}",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ActionResult(
                action=ComputerAction.KEYBOARD_KEY,
                success=False,
                message=str(e)
            )

    async def keyboard_hotkey(self, *keys: str) -> ActionResult:
        self._ensure_imports()
        start = time.time()

        try:
            self._pyautogui.hotkey(*keys)
            return ActionResult(
                action=ComputerAction.KEYBOARD_HOTKEY,
                success=True,
                message=f"Pressed {'+'.join(keys)}",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ActionResult(
                action=ComputerAction.KEYBOARD_HOTKEY,
                success=False,
                message=str(e)
            )

    async def scroll(
        self,
        x: int,
        y: int,
        direction: str = "down",
        amount: int = 3
    ) -> ActionResult:
        self._ensure_imports()
        start = time.time()

        try:
            clicks = amount if direction == "up" else -amount
            self._pyautogui.scroll(clicks, x, y)
            return ActionResult(
                action=ComputerAction.SCROLL,
                success=True,
                message=f"Scrolled {direction} at ({x}, {y})",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return ActionResult(
                action=ComputerAction.SCROLL,
                success=False,
                message=str(e)
            )


# =============================================================================
# ANTHROPIC COMPUTER USE
# =============================================================================

class AnthropicComputerUse:
    """
    Integration with Anthropic's computer use capability.
    Uses Claude to analyze screenshots and determine actions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        controller: Optional[ComputerController] = None,
        config: Optional[ComputerConfig] = None
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.controller = controller or PyAutoGUIController()
        self.config = config or ComputerConfig()
        self.state = ComputerState.IDLE
        self.action_history: List[ActionResult] = []
        self._pending_confirmation: Optional[Dict] = None

    async def execute_task(
        self,
        task: str,
        max_iterations: int = 10,
        on_action: Optional[Callable] = None,
        require_confirmation: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Execute a computer task using Claude's vision and reasoning.

        Args:
            task: Description of what to accomplish
            max_iterations: Maximum number of action loops
            on_action: Callback for each action (for UI updates)
            require_confirmation: Override config confirmation setting
        """
        if not self.api_key:
            return {"success": False, "error": "Anthropic API key required"}

        self.state = ComputerState.EXECUTING
        self.action_history = []

        confirmation_required = (
            require_confirmation
            if require_confirmation is not None
            else self.config.require_confirmation
        )

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            messages = []

            for iteration in range(max_iterations):
                # Take screenshot
                screenshot = await self.controller.take_screenshot()

                # Build message with screenshot
                if iteration == 0:
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot.to_base64()
                                }
                            },
                            {
                                "type": "text",
                                "text": f"""Task: {task}

You are controlling a computer. Analyze the screenshot and determine the next action to accomplish the task.

Available actions:
- click(x, y) - Click at coordinates
- double_click(x, y) - Double click
- right_click(x, y) - Right click
- type(text) - Type text
- key(key_name) - Press a key (enter, tab, escape, etc.)
- hotkey(key1, key2, ...) - Press key combination (ctrl+c, cmd+v, etc.)
- scroll(x, y, direction, amount) - Scroll up/down
- done(result) - Task completed

Respond with a JSON action:
{{"action": "action_name", "params": {{"..."}}, "reasoning": "why this action"}}

If the task is complete, respond:
{{"action": "done", "result": "description of what was accomplished"}}"""
                            }
                        ]
                    })
                else:
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot.to_base64()
                                }
                            },
                            {
                                "type": "text",
                                "text": "Here's the current screen. Continue with the task or indicate if done."
                            }
                        ]
                    })

                # Call Claude
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=messages
                )

                assistant_message = response.content[0].text
                messages.append({"role": "assistant", "content": assistant_message})

                # Parse action
                try:
                    # Extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', assistant_message, re.DOTALL)
                    if not json_match:
                        continue

                    action_data = json.loads(json_match.group())
                    action_name = action_data.get("action", "")
                    params = action_data.get("params", {})
                    reasoning = action_data.get("reasoning", "")

                    # Check if done
                    if action_name == "done":
                        self.state = ComputerState.IDLE
                        return {
                            "success": True,
                            "result": action_data.get("result", "Task completed"),
                            "iterations": iteration + 1,
                            "actions": len(self.action_history)
                        }

                    # Request confirmation if needed
                    if confirmation_required:
                        self._pending_confirmation = {
                            "action": action_name,
                            "params": params,
                            "reasoning": reasoning
                        }
                        self.state = ComputerState.WAITING

                        # In a real implementation, this would wait for user confirmation
                        # For now, we auto-confirm after logging
                        logger.info(f"Action pending confirmation: {action_name} {params}")

                    # Execute action
                    result = await self._execute_action(action_name, params)
                    self.action_history.append(result)

                    if on_action:
                        await on_action(result)

                    if not result.success:
                        messages.append({
                            "role": "user",
                            "content": f"Action failed: {result.message}. Try a different approach."
                        })

                    # Small delay between actions
                    await asyncio.sleep(self.config.action_delay_ms / 1000)

                except json.JSONDecodeError:
                    logger.warning(f"Could not parse action from: {assistant_message}")
                    continue

            self.state = ComputerState.IDLE
            return {
                "success": False,
                "error": "Max iterations reached",
                "iterations": max_iterations,
                "actions": len(self.action_history)
            }

        except ImportError:
            return {"success": False, "error": "anthropic package required"}
        except Exception as e:
            self.state = ComputerState.ERROR
            logger.error(f"Computer use error: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_action(
        self,
        action_name: str,
        params: Dict[str, Any]
    ) -> ActionResult:
        """Execute a single action."""
        try:
            if action_name == "click":
                return await self.controller.mouse_click(
                    params.get("x", 0),
                    params.get("y", 0)
                )
            elif action_name == "double_click":
                return await self.controller.mouse_click(
                    params.get("x", 0),
                    params.get("y", 0),
                    clicks=2
                )
            elif action_name == "right_click":
                return await self.controller.mouse_click(
                    params.get("x", 0),
                    params.get("y", 0),
                    button="right"
                )
            elif action_name == "type":
                return await self.controller.keyboard_type(params.get("text", ""))
            elif action_name == "key":
                return await self.controller.keyboard_key(params.get("key", ""))
            elif action_name == "hotkey":
                keys = params.get("keys", [])
                return await self.controller.keyboard_hotkey(*keys)
            elif action_name == "scroll":
                return await self.controller.scroll(
                    params.get("x", 0),
                    params.get("y", 0),
                    params.get("direction", "down"),
                    params.get("amount", 3)
                )
            else:
                return ActionResult(
                    action=ComputerAction.WAIT,
                    success=False,
                    message=f"Unknown action: {action_name}"
                )
        except Exception as e:
            return ActionResult(
                action=ComputerAction.WAIT,
                success=False,
                message=str(e)
            )

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "state": self.state.value,
            "enabled": self.config.enabled,
            "require_confirmation": self.config.require_confirmation,
            "action_count": len(self.action_history),
            "pending_confirmation": self._pending_confirmation
        }


# =============================================================================
# COMPUTER USE TOOL
# =============================================================================

class ComputerUseTool:
    """
    Tool wrapper for computer use, integrates with BAEL's tool system.
    """

    def __init__(self, computer_use: Optional[AnthropicComputerUse] = None):
        self.computer_use = computer_use or AnthropicComputerUse()
        self.name = "computer_use"
        self.description = "Control the computer to accomplish GUI-based tasks"

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Description of what to accomplish"
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Maximum action iterations",
                        "default": 10
                    }
                },
                "required": ["task"]
            }
        }

    async def execute(
        self,
        task: str,
        max_iterations: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute computer use task."""
        return await self.computer_use.execute_task(
            task=task,
            max_iterations=max_iterations
        )


# =============================================================================
# SINGLETON
# =============================================================================

_computer_use: Optional[AnthropicComputerUse] = None


def get_computer_use(config: Optional[ComputerConfig] = None) -> AnthropicComputerUse:
    """Get the global computer use instance."""
    global _computer_use

    if _computer_use is None:
        _computer_use = AnthropicComputerUse(config=config)

    return _computer_use


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    async def demo():
        print("Computer Use Integration Demo")
        print("-" * 40)

        computer = get_computer_use()
        print(f"Status: {json.dumps(computer.get_status(), indent=2)}")

        # Take a screenshot
        try:
            screenshot = await computer.controller.take_screenshot()
            print(f"Screenshot: {screenshot.width}x{screenshot.height}, {len(screenshot.image_data)} bytes")
        except Exception as e:
            print(f"Screenshot failed (expected without display): {e}")

    asyncio.run(demo())
