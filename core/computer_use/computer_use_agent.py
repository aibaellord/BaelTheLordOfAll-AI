"""
BAEL - Computer Use Agent
High-level orchestrator for desktop automation tasks.
Combines screen reading, action execution, and LLM reasoning.
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from . import (
    ActionType, ComputerAction, ActionResult,
    ScreenRegion, UIElement
)
from .screen_capture import ScreenReader, Screenshot
from .action_executor import ActionExecutor

logger = logging.getLogger("BAEL.ComputerUse.Agent")


class TaskStatus(Enum):
    """Status of a computer use task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class ComputerTask:
    """A high-level computer use task."""
    id: str
    description: str
    steps: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    results: List[ActionResult] = field(default_factory=list)
    screenshots: List[Screenshot] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class AgentConfig:
    """Configuration for computer use agent."""
    max_steps: int = 50
    screenshot_interval: int = 3  # Take screenshot every N actions
    auto_scroll: bool = True
    element_timeout: float = 5.0  # Seconds to wait for element
    retry_failed: bool = True
    max_retries: int = 2
    use_vision_model: bool = True  # Use vision LLM for understanding


class ComputerUseAgent:
    """
    High-level agent for desktop automation.

    Features:
    - Natural language task understanding
    - Automatic action planning
    - Visual verification of actions
    - Error recovery and retry
    - Task decomposition
    - Multi-step workflow execution
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self._screen_reader = ScreenReader()
        self._executor = ActionExecutor()
        self._llm = None
        self._current_task: Optional[ComputerTask] = None

    async def _get_llm(self):
        """Lazy load LLM provider."""
        if self._llm is None:
            try:
                from core.llm import get_provider
                self._llm = get_provider()
            except ImportError:
                logger.warning("LLM provider not available")
        return self._llm

    async def execute_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ComputerTask:
        """
        Execute a high-level computer task.

        Args:
            task_description: Natural language description of task
            context: Additional context (current app, previous actions, etc.)

        Returns:
            ComputerTask with results
        """
        task = ComputerTask(
            id=f"task_{uuid.uuid4().hex[:8]}",
            description=task_description,
            started_at=datetime.now()
        )
        self._current_task = task

        logger.info(f"Starting task: {task_description[:100]}")

        try:
            task.status = TaskStatus.RUNNING

            # Take initial screenshot
            initial_screenshot = await self._screen_reader.capture_screen()
            task.screenshots.append(initial_screenshot)

            # Plan the task steps
            steps = await self._plan_task(task_description, initial_screenshot, context)
            task.steps = steps

            logger.info(f"Planned {len(steps)} steps for task")

            # Execute each step
            for i, step in enumerate(steps):
                if task.status != TaskStatus.RUNNING:
                    break

                logger.info(f"Step {i+1}/{len(steps)}: {step[:50]}...")

                result = await self._execute_step(step, task)
                task.results.append(result)

                if not result.success:
                    if self.config.retry_failed:
                        # Retry with fresh screenshot
                        result = await self._retry_step(step, task)
                        task.results.append(result)

                    if not result.success:
                        task.status = TaskStatus.FAILED
                        task.error = f"Step failed: {step}"
                        break

                # Take periodic screenshots
                if (i + 1) % self.config.screenshot_interval == 0:
                    screenshot = await self._screen_reader.capture_screen()
                    task.screenshots.append(screenshot)

            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.COMPLETED

            task.completed_at = datetime.now()
            logger.info(f"Task completed: {task.status.value}")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            logger.error(f"Task failed with exception: {e}")

        return task

    async def _plan_task(
        self,
        description: str,
        screenshot: Screenshot,
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Plan the steps needed to complete a task."""
        llm = await self._get_llm()

        if llm is None:
            # Fallback: simple parsing
            return self._simple_plan(description)

        # Detect current UI elements
        elements = await self._screen_reader.detect_elements(screenshot)
        elements_text = "\n".join(
            f"- {e.element_type}: '{e.text}' at ({e.region.x}, {e.region.y})"
            for e in elements[:20]
        )

        prompt = f"""You are a desktop automation agent. Plan the steps to complete this task.

TASK: {description}

CURRENT SCREEN ELEMENTS:
{elements_text}

{f"CONTEXT: {context}" if context else ""}

List the specific steps needed. Each step should be a single action like:
- Click on "Button Name"
- Type "text to type"
- Press Ctrl+S
- Scroll down
- Wait 2 seconds

Steps:
1."""

        response = await llm.generate(prompt, temperature=0.3)

        # Parse steps
        steps = []
        for line in response.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Clean up step text
                step = line.lstrip("0123456789.-) ")
                if len(step) > 5:
                    steps.append(step)

        return steps if steps else self._simple_plan(description)

    def _simple_plan(self, description: str) -> List[str]:
        """Simple fallback planning without LLM."""
        steps = []
        desc_lower = description.lower()

        # Extract actions from description
        if "click" in desc_lower:
            steps.append(f"Click on target element")
        if "type" in desc_lower or "enter" in desc_lower:
            # Extract text to type
            if '"' in description:
                text = description.split('"')[1]
                steps.append(f"Type '{text}'")
        if "open" in desc_lower:
            steps.append("Click on target application/file")
        if "save" in desc_lower:
            steps.append("Press Ctrl+S")
        if "copy" in desc_lower:
            steps.append("Press Ctrl+C")
        if "paste" in desc_lower:
            steps.append("Press Ctrl+V")
        if "scroll" in desc_lower:
            steps.append("Scroll down")

        return steps if steps else [description]

    async def _execute_step(
        self,
        step: str,
        task: ComputerTask
    ) -> ActionResult:
        """Execute a single step."""
        step_lower = step.lower()

        # Parse the step to determine action
        if "click" in step_lower:
            return await self._handle_click(step)
        elif "type" in step_lower or "enter" in step_lower:
            return await self._handle_type(step)
        elif "press" in step_lower or "hotkey" in step_lower:
            return await self._handle_hotkey(step)
        elif "scroll" in step_lower:
            return await self._handle_scroll(step)
        elif "wait" in step_lower:
            return await self._handle_wait(step)
        elif "drag" in step_lower:
            return await self._handle_drag(step)
        else:
            # Try to interpret as click on text
            return await self._handle_click(step)

    async def _handle_click(self, step: str) -> ActionResult:
        """Handle a click action."""
        # Extract target text
        target_text = self._extract_quoted_text(step)
        if not target_text:
            # Try to extract from step description
            words = step.split()
            target_text = " ".join(words[-3:]) if len(words) > 3 else step

        # Find element on screen
        screenshot = await self._screen_reader.capture_screen()
        elements = await self._screen_reader.detect_elements(screenshot)

        # Find best matching element
        best_match = None
        best_score = 0

        for element in elements:
            score = self._text_similarity(target_text.lower(), element.text.lower())
            if score > best_score:
                best_score = score
                best_match = element

        if best_match and best_score > 0.3:
            center = best_match.region.center
            return await self._executor.click(center[0], center[1])
        else:
            # No matching element found
            return ActionResult(
                success=False,
                action=ComputerAction(action_type=ActionType.CLICK),
                error=f"Could not find element: {target_text}"
            )

    async def _handle_type(self, step: str) -> ActionResult:
        """Handle a type action."""
        text = self._extract_quoted_text(step)
        if text:
            return await self._executor.type_text(text)
        else:
            return ActionResult(
                success=False,
                action=ComputerAction(action_type=ActionType.TYPE),
                error="No text to type found in step"
            )

    async def _handle_hotkey(self, step: str) -> ActionResult:
        """Handle a hotkey action."""
        # Parse key combination
        step_lower = step.lower()

        # Common shortcuts
        shortcuts = {
            "ctrl+s": ["ctrl", "s"],
            "ctrl+c": ["ctrl", "c"],
            "ctrl+v": ["ctrl", "v"],
            "ctrl+z": ["ctrl", "z"],
            "ctrl+a": ["ctrl", "a"],
            "ctrl+f": ["ctrl", "f"],
            "alt+tab": ["alt", "tab"],
            "alt+f4": ["alt", "f4"],
            "enter": ["enter"],
            "escape": ["escape"],
            "tab": ["tab"],
        }

        for shortcut, keys in shortcuts.items():
            if shortcut in step_lower:
                return await self._executor.press_keys(*keys)

        # Try to parse generic format
        if "+" in step:
            parts = step.split("+")
            keys = [p.strip().lower() for p in parts]
            return await self._executor.press_keys(*keys)

        return ActionResult(
            success=False,
            action=ComputerAction(action_type=ActionType.HOTKEY),
            error="Could not parse hotkey combination"
        )

    async def _handle_scroll(self, step: str) -> ActionResult:
        """Handle a scroll action."""
        step_lower = step.lower()

        clicks = 5  # Default scroll amount
        if "up" in step_lower:
            clicks = 5
        elif "down" in step_lower:
            clicks = -5

        return await self._executor.scroll(clicks)

    async def _handle_wait(self, step: str) -> ActionResult:
        """Handle a wait action."""
        import re

        # Extract duration
        numbers = re.findall(r'[\d.]+', step)
        seconds = float(numbers[0]) if numbers else 1.0

        return await self._executor.wait(seconds)

    async def _handle_drag(self, step: str) -> ActionResult:
        """Handle a drag action."""
        # This would need more sophisticated parsing
        return ActionResult(
            success=False,
            action=ComputerAction(action_type=ActionType.DRAG),
            error="Drag action parsing not fully implemented"
        )

    async def _retry_step(
        self,
        step: str,
        task: ComputerTask
    ) -> ActionResult:
        """Retry a failed step with fresh context."""
        logger.info(f"Retrying step: {step[:30]}...")

        await asyncio.sleep(1)  # Brief pause before retry

        return await self._execute_step(step, task)

    def _extract_quoted_text(self, text: str) -> Optional[str]:
        """Extract text between quotes."""
        import re

        # Try different quote types
        for pattern in [r'"([^"]+)"', r"'([^']+)'", r'"([^"]+)"', r''([^']+)''']:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        if not text1 or not text2:
            return 0.0

        # Exact match
        if text1 == text2:
            return 1.0

        # Substring match
        if text1 in text2 or text2 in text1:
            return 0.8

        # Word overlap
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    async def find_and_click(self, target_text: str) -> ActionResult:
        """Convenience method to find an element and click it."""
        element = await self._screen_reader.find_element_by_text(target_text)

        if element:
            return await self._executor.click_element(element)
        else:
            return ActionResult(
                success=False,
                action=ComputerAction(action_type=ActionType.CLICK),
                error=f"Element not found: {target_text}"
            )

    async def type_in_field(
        self,
        field_label: str,
        text: str
    ) -> ActionResult:
        """Click a field and type text into it."""
        # Find and click the field
        click_result = await self.find_and_click(field_label)

        if not click_result.success:
            return click_result

        await asyncio.sleep(0.2)  # Wait for focus

        # Type the text
        return await self._executor.type_text(text)

    async def get_screen_state(self) -> Dict[str, Any]:
        """Get current screen state for analysis."""
        screenshot = await self._screen_reader.capture_screen()
        elements = await self._screen_reader.detect_elements(screenshot)
        text = await self._screen_reader.extract_text(screenshot)

        return {
            "screenshot": screenshot,
            "elements": elements,
            "text": text[:2000],
            "element_count": len(elements)
        }

    def pause_task(self) -> None:
        """Pause the current task."""
        if self._current_task:
            self._current_task.status = TaskStatus.PAUSED

    def resume_task(self) -> None:
        """Resume the current task."""
        if self._current_task and self._current_task.status == TaskStatus.PAUSED:
            self._current_task.status = TaskStatus.RUNNING


# Global instance
_computer_agent: Optional[ComputerUseAgent] = None


def get_computer_agent(config: Optional[AgentConfig] = None) -> ComputerUseAgent:
    """Get or create computer use agent instance."""
    global _computer_agent
    if _computer_agent is None or config is not None:
        _computer_agent = ComputerUseAgent(config)
    return _computer_agent


async def execute_computer_task(description: str, **kwargs) -> ComputerTask:
    """Convenience function to execute a computer task."""
    agent = get_computer_agent()
    return await agent.execute_task(description, **kwargs)
