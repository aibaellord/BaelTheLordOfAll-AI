"""
BAEL - Action Executor
Executes mouse, keyboard, and system actions.
Uses pyautogui for cross-platform automation.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from . import ActionResult, ActionType, ComputerAction, ScreenRegion

logger = logging.getLogger("BAEL.ComputerUse.Executor")


@dataclass
class ExecutorConfig:
    """Configuration for action executor."""
    mouse_move_duration: float = 0.3  # Seconds for mouse movements
    typing_interval: float = 0.02  # Seconds between keystrokes
    action_delay: float = 0.1  # Delay after each action
    fail_safe: bool = True  # Move mouse to corner to abort
    screenshot_after: bool = True  # Take screenshot after each action
    confirm_before_type: bool = False  # Confirm before typing sensitive data


class ActionExecutor:
    """
    Executes computer actions.

    Features:
    - Mouse control (click, drag, scroll)
    - Keyboard control (type, hotkeys)
    - Safe execution with fail-safes
    - Action logging and screenshots
    - Undo support for some actions
    """

    def __init__(self, config: Optional[ExecutorConfig] = None):
        self.config = config or ExecutorConfig()
        self._pyautogui = None
        self._history: List[ComputerAction] = []
        self._init_dependencies()

    def _init_dependencies(self):
        """Initialize pyautogui."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = self.config.fail_safe
            pyautogui.PAUSE = self.config.action_delay
            self._pyautogui = pyautogui
            logger.info("PyAutoGUI initialized")
        except ImportError:
            logger.error("PyAutoGUI not available - install with: pip install pyautogui")

    async def execute(self, action: ComputerAction) -> ActionResult:
        """
        Execute a single action.

        Args:
            action: The action to execute

        Returns:
            ActionResult with success status
        """
        if self._pyautogui is None:
            return ActionResult(
                success=False,
                action=action,
                error="PyAutoGUI not available"
            )

        try:
            # Execute based on action type
            if action.action_type == ActionType.CLICK:
                await self._execute_click(action)
            elif action.action_type == ActionType.DOUBLE_CLICK:
                await self._execute_double_click(action)
            elif action.action_type == ActionType.RIGHT_CLICK:
                await self._execute_right_click(action)
            elif action.action_type == ActionType.TYPE:
                await self._execute_type(action)
            elif action.action_type == ActionType.HOTKEY:
                await self._execute_hotkey(action)
            elif action.action_type == ActionType.SCROLL:
                await self._execute_scroll(action)
            elif action.action_type == ActionType.DRAG:
                await self._execute_drag(action)
            elif action.action_type == ActionType.MOVE:
                await self._execute_move(action)
            elif action.action_type == ActionType.WAIT:
                await self._execute_wait(action)
            elif action.action_type == ActionType.SCREENSHOT:
                pass  # Screenshot is handled below
            else:
                return ActionResult(
                    success=False,
                    action=action,
                    error=f"Unknown action type: {action.action_type}"
                )

            # Record in history
            self._history.append(action)

            # Take screenshot if configured
            screenshot_bytes = None
            if self.config.screenshot_after:
                from .screen_capture import get_screen_reader
                reader = get_screen_reader()
                screenshot = await reader.capture_screen()
                screenshot_bytes = screenshot.image_bytes

            logger.info(f"Executed action: {action.action_type.value}")

            return ActionResult(
                success=True,
                action=action,
                screenshot_after=screenshot_bytes
            )

        except Exception as e:
            logger.error(f"Action failed: {e}")
            return ActionResult(
                success=False,
                action=action,
                error=str(e)
            )

    async def execute_sequence(
        self,
        actions: List[ComputerAction],
        stop_on_error: bool = True
    ) -> List[ActionResult]:
        """
        Execute a sequence of actions.

        Args:
            actions: List of actions to execute
            stop_on_error: Stop execution if an action fails

        Returns:
            List of ActionResults
        """
        results = []

        for action in actions:
            result = await self.execute(action)
            results.append(result)

            if not result.success and stop_on_error:
                logger.warning(f"Stopping sequence due to error: {result.error}")
                break

        return results

    async def _execute_click(self, action: ComputerAction) -> None:
        """Execute a click action."""
        if action.target:
            x, y = action.target
            await asyncio.to_thread(
                self._pyautogui.click,
                x=x, y=y,
                duration=self.config.mouse_move_duration
            )
        else:
            await asyncio.to_thread(self._pyautogui.click)

    async def _execute_double_click(self, action: ComputerAction) -> None:
        """Execute a double-click action."""
        if action.target:
            x, y = action.target
            await asyncio.to_thread(
                self._pyautogui.doubleClick,
                x=x, y=y,
                duration=self.config.mouse_move_duration
            )
        else:
            await asyncio.to_thread(self._pyautogui.doubleClick)

    async def _execute_right_click(self, action: ComputerAction) -> None:
        """Execute a right-click action."""
        if action.target:
            x, y = action.target
            await asyncio.to_thread(
                self._pyautogui.rightClick,
                x=x, y=y,
                duration=self.config.mouse_move_duration
            )
        else:
            await asyncio.to_thread(self._pyautogui.rightClick)

    async def _execute_type(self, action: ComputerAction) -> None:
        """Execute a type action."""
        if action.text:
            await asyncio.to_thread(
                self._pyautogui.typewrite,
                action.text,
                interval=self.config.typing_interval
            )

    async def _execute_hotkey(self, action: ComputerAction) -> None:
        """Execute a hotkey action."""
        if action.keys:
            await asyncio.to_thread(self._pyautogui.hotkey, *action.keys)

    async def _execute_scroll(self, action: ComputerAction) -> None:
        """Execute a scroll action."""
        clicks = action.metadata.get("clicks", 3)
        if action.target:
            x, y = action.target
            await asyncio.to_thread(self._pyautogui.scroll, clicks, x=x, y=y)
        else:
            await asyncio.to_thread(self._pyautogui.scroll, clicks)

    async def _execute_drag(self, action: ComputerAction) -> None:
        """Execute a drag action."""
        if action.target and "end" in action.metadata:
            start_x, start_y = action.target
            end_x, end_y = action.metadata["end"]

            await asyncio.to_thread(
                self._pyautogui.moveTo,
                start_x, start_y,
                duration=self.config.mouse_move_duration
            )
            await asyncio.to_thread(
                self._pyautogui.drag,
                end_x - start_x, end_y - start_y,
                duration=self.config.mouse_move_duration
            )

    async def _execute_move(self, action: ComputerAction) -> None:
        """Execute a mouse move action."""
        if action.target:
            x, y = action.target
            await asyncio.to_thread(
                self._pyautogui.moveTo,
                x, y,
                duration=self.config.mouse_move_duration
            )

    async def _execute_wait(self, action: ComputerAction) -> None:
        """Execute a wait action."""
        await asyncio.sleep(action.duration)

    # Convenience methods
    async def click(
        self,
        x: int,
        y: int,
        clicks: int = 1,
        button: str = "left"
    ) -> ActionResult:
        """Click at coordinates."""
        action_type = {
            1: ActionType.CLICK,
            2: ActionType.DOUBLE_CLICK
        }.get(clicks, ActionType.CLICK)

        if button == "right":
            action_type = ActionType.RIGHT_CLICK

        return await self.execute(ComputerAction(
            action_type=action_type,
            target=(x, y)
        ))

    async def click_element(self, element) -> ActionResult:
        """Click on a UI element."""
        center = element.region.center
        return await self.click(center[0], center[1])

    async def type_text(self, text: str) -> ActionResult:
        """Type text."""
        return await self.execute(ComputerAction(
            action_type=ActionType.TYPE,
            text=text
        ))

    async def press_keys(self, *keys: str) -> ActionResult:
        """Press a key combination."""
        return await self.execute(ComputerAction(
            action_type=ActionType.HOTKEY,
            keys=list(keys)
        ))

    async def scroll(
        self,
        clicks: int = 3,
        x: Optional[int] = None,
        y: Optional[int] = None
    ) -> ActionResult:
        """Scroll the mouse wheel."""
        target = (x, y) if x is not None and y is not None else None
        return await self.execute(ComputerAction(
            action_type=ActionType.SCROLL,
            target=target,
            metadata={"clicks": clicks}
        ))

    async def drag_to(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int]
    ) -> ActionResult:
        """Drag from start to end coordinates."""
        return await self.execute(ComputerAction(
            action_type=ActionType.DRAG,
            target=start,
            metadata={"end": end}
        ))

    async def wait(self, seconds: float) -> ActionResult:
        """Wait for a duration."""
        return await self.execute(ComputerAction(
            action_type=ActionType.WAIT,
            duration=seconds
        ))

    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        if self._pyautogui:
            pos = self._pyautogui.position()
            return (pos.x, pos.y)
        return (0, 0)

    def get_action_history(self, limit: int = 10) -> List[ComputerAction]:
        """Get recent action history."""
        return self._history[-limit:]

    async def undo_last(self) -> bool:
        """
        Attempt to undo the last action.
        Only works for certain actions like typing.
        """
        if not self._history:
            return False

        last_action = self._history[-1]

        if last_action.action_type == ActionType.TYPE and last_action.text:
            # Select all typed text and delete
            length = len(last_action.text)
            for _ in range(length):
                await self.press_keys("backspace")
            return True

        return False


# Global instance
_action_executor: Optional[ActionExecutor] = None


def get_action_executor(config: Optional[ExecutorConfig] = None) -> ActionExecutor:
    """Get or create action executor instance."""
    global _action_executor
    if _action_executor is None or config is not None:
        _action_executor = ActionExecutor(config)
    return _action_executor
