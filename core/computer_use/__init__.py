"""
BAEL - Computer Use System
Desktop automation via screen capture, OCR, and mouse/keyboard control.
Zero-cost implementation using pyautogui, PIL, and local models.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("BAEL.ComputerUse")


class ActionType(Enum):
    """Types of computer actions."""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    HOTKEY = "hotkey"
    SCROLL = "scroll"
    DRAG = "drag"
    SCREENSHOT = "screenshot"
    WAIT = "wait"
    MOVE = "move"


@dataclass
class ScreenRegion:
    """A region of the screen."""
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass
class UIElement:
    """A detected UI element."""
    id: str
    element_type: str  # button, text, input, image, icon, etc.
    text: str
    region: ScreenRegion
    confidence: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComputerAction:
    """An action to perform on the computer."""
    action_type: ActionType
    target: Optional[Tuple[int, int]] = None  # x, y coordinates
    text: Optional[str] = None  # For typing
    keys: Optional[List[str]] = None  # For hotkeys
    duration: float = 0.0  # For waits/animations
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result of a computer action."""
    success: bool
    action: ComputerAction
    screenshot_after: Optional[bytes] = None
    error: Optional[str] = None
    elements_detected: List[UIElement] = field(default_factory=list)


# Lazy imports
def get_computer_agent():
    """Get the computer use agent."""
    from .computer_use_agent import ComputerUseAgent
    return ComputerUseAgent()


def get_screen_reader():
    """Get the screen reader."""
    from .screen_capture import ScreenReader
    return ScreenReader()


def get_action_executor():
    """Get the action executor."""
    from .action_executor import ActionExecutor
    return ActionExecutor()


__all__ = [
    "ActionType",
    "ScreenRegion",
    "UIElement",
    "ComputerAction",
    "ActionResult",
    "get_computer_agent",
    "get_screen_reader",
    "get_action_executor"
]
