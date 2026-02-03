"""
Context Management Engine for BAEL

Handles dynamic context windows, attention mechanisms, context summarization,
and coherent conversation state management across long interactions.
"""

import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ContextItem:
    """Single context item with relevance scoring."""
    content: str
    timestamp: datetime
    relevance: float = 0.5
    access_count: int = 0
    token_count: int = 0
    source: str = "system"
    importance: float = 1.0

    def decay_relevance(self, hours_since: float) -> float:
        """Decay relevance over time."""
        decay_rate = 0.05  # 5% per hour
        return self.relevance * math.exp(-decay_rate * hours_since)


class AttentionMechanism:
    """Attention mechanism for focusing on relevant context."""

    def __init__(self, num_heads: int = 8):
        self.num_heads = num_heads
        self.attention_scores: Dict[str, float] = {}
        self.query_history: deque = deque(maxlen=100)

    def compute_attention(self, items: List[ContextItem], query: str) -> Dict[str, float]:
        """Compute attention weights for items given query."""
        if not items:
            return {}

        # Multi-head attention
        attention_weights = {}
        total_score = 0

        for item in items:
            # Relevance-based attention
            relevance_score = item.relevance * item.importance

            # Recency bonus
            hours_since = (datetime.now() - item.timestamp).total_seconds() / 3600
            recency_bonus = math.exp(-0.1 * hours_since)

            # Access frequency boost
            frequency_boost = math.log(item.access_count + 1) / 10

            # Combined attention
            score = (relevance_score * 0.6 + recency_bonus * 0.3 + frequency_boost * 0.1)
            attention_weights[item.content[:50]] = score
            total_score += score

        # Normalize
        if total_score > 0:
            attention_weights = {k: v / total_score for k, v in attention_weights.items()}

        self.query_history.append({
            "query": query,
            "weights": attention_weights,
            "timestamp": datetime.now()
        })

        return attention_weights

    def top_k_attention(self, items: List[ContextItem], query: str, k: int = 5) -> List[Tuple[str, float]]:
        """Get top-k attended items."""
        weights = self.compute_attention(items, query)
        sorted_items = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:k]


class ContextWindow:
    """Sliding context window with dynamic sizing."""

    def __init__(self, max_tokens: int = 4096, target_usage: float = 0.8):
        self.max_tokens = max_tokens
        self.target_usage = target_usage  # 80% usage target
        self.items: deque = deque()
        self.total_tokens = 0
        self.priority_items: Set[str] = set()

    def add_item(self, item: ContextItem, priority: bool = False) -> bool:
        """Add item to context window."""
        if item.token_count + self.total_tokens > self.max_tokens:
            # Try to make room
            if not self._make_room(item.token_count):
                return False

        self.items.append(item)
        self.total_tokens += item.token_count

        if priority:
            self.priority_items.add(item.content[:50])

        return True

    def _make_room(self, needed_tokens: int) -> bool:
        """Remove lowest relevance items to make room."""
        while self.items and self.total_tokens + needed_tokens > self.max_tokens:
            item = self.items.popleft()
            if item.content[:50] not in self.priority_items:
                self.total_tokens -= item.token_count
                return self.total_tokens + needed_tokens <= self.max_tokens

        return False

    def get_items(self) -> List[ContextItem]:
        """Get all items in context."""
        return list(self.items)

    def get_summary_targets(self, compression_ratio: float = 0.5) -> List[ContextItem]:
        """Get items that should be summarized for compression."""
        target_count = max(1, int(len(self.items) * compression_ratio))
        sorted_items = sorted(
            self.items,
            key=lambda x: x.relevance * x.importance,
            reverse=True
        )
        return sorted_items[target_count:]

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get context window usage statistics."""
        return {
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": (self.total_tokens / self.max_tokens) * 100,
            "item_count": len(self.items),
            "priority_items": len(self.priority_items)
        }


class ContextSummarizer:
    """Summarizes context to maintain coherence with compression."""

    def __init__(self, compression_ratio: float = 0.5):
        self.compression_ratio = compression_ratio
        self.summary_cache: Dict[str, str] = {}

    def summarize_items(self, items: List[ContextItem]) -> str:
        """Summarize multiple context items."""
        if not items:
            return ""

        # Create cache key
        cache_key = "_".join([item.content[:30] for item in items[:5]])

        if cache_key in self.summary_cache:
            return self.summary_cache[cache_key]

        # Build summary
        key_points = []
        for item in items:
            if item.importance > 0.7:
                key_points.append(item.content[:200])

        summary = f"Summary: {len(items)} items consolidated. Key points: {'; '.join(key_points[:3])}"

        self.summary_cache[cache_key] = summary
        return summary

    def create_checkpoint(self, items: List[ContextItem], title: str) -> Dict[str, Any]:
        """Create a checkpoint summary of context state."""
        return {
            "title": title,
            "timestamp": datetime.now().isoformat(),
            "item_count": len(items),
            "total_tokens": sum(item.token_count for item in items),
            "summary": self.summarize_items(items),
            "key_entities": self._extract_key_entities(items)
        }

    def _extract_key_entities(self, items: List[ContextItem]) -> List[str]:
        """Extract key entities from items."""
        entities = set()
        for item in items:
            if item.importance > 0.8:
                words = item.content.split()[:5]
                entities.update(words)
        return list(entities)[:10]


class ConversationState:
    """Manages state across conversation turns."""

    def __init__(self):
        self.turns: List[Dict[str, Any]] = []
        self.user_intent: Optional[str] = None
        self.goal_stack: deque = deque()
        self.context_variables: Dict[str, Any] = {}
        self.dialog_acts: List[str] = []

    def add_turn(self, user_input: str, assistant_output: str,
                 metadata: Optional[Dict] = None) -> None:
        """Add conversation turn."""
        self.turns.append({
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": assistant_output,
            "metadata": metadata or {}
        })

    def set_intent(self, intent: str, confidence: float = 0.8) -> None:
        """Set user intent."""
        self.user_intent = intent
        self.context_variables["intent_confidence"] = confidence

    def push_goal(self, goal: str) -> None:
        """Push goal onto stack."""
        self.goal_stack.append(goal)

    def pop_goal(self) -> Optional[str]:
        """Pop goal from stack."""
        if self.goal_stack:
            return self.goal_stack.pop()
        return None

    def get_dialog_state(self) -> Dict[str, Any]:
        """Get current dialog state."""
        return {
            "turn_count": len(self.turns),
            "user_intent": self.user_intent,
            "active_goals": list(self.goal_stack),
            "context_vars": self.context_variables,
            "dialog_acts": self.dialog_acts
        }


class ContextBridge:
    """Bridges between conversation turns and context windows."""

    def __init__(self, window_size: int = 4096):
        self.context_window = ContextWindow(max_tokens=window_size)
        self.attention = AttentionMechanism()
        self.summarizer = ContextSummarizer()
        self.conversation_state = ConversationState()
        self.checkpoints: List[Dict] = []

    def process_turn(self, user_input: str, assistant_output: str, tokens: int) -> None:
        """Process new conversation turn."""
        # Create context items
        user_item = ContextItem(
            content=f"User: {user_input}",
            timestamp=datetime.now(),
            token_count=tokens // 2,
            source="user",
            importance=0.9
        )

        assistant_item = ContextItem(
            content=f"Assistant: {assistant_output[:200]}",
            timestamp=datetime.now(),
            token_count=tokens // 2,
            source="assistant",
            importance=0.8
        )

        # Add to context window
        self.context_window.add_item(user_item, priority=True)
        self.context_window.add_item(assistant_item)

        # Update conversation state
        self.conversation_state.add_turn(user_input, assistant_output)

    def get_relevant_context(self, query: str, k: int = 5) -> List[str]:
        """Get relevant context items for query."""
        items = self.context_window.get_items()
        attended = self.attention.top_k_attention(items, query, k)
        return [item for item, _ in attended]

    def compress_context(self) -> Dict[str, Any]:
        """Compress old context to make room."""
        items_to_summarize = self.context_window.get_summary_targets()

        if items_to_summarize:
            summary = self.summarizer.summarize_items(items_to_summarize)

            # Create checkpoint
            checkpoint = self.summarizer.create_checkpoint(
                items_to_summarize,
                f"Checkpoint {len(self.checkpoints)}"
            )
            self.checkpoints.append(checkpoint)

            # Replace items with summary
            for _ in range(len(items_to_summarize)):
                if self.context_window.items:
                    self.context_window.items.popleft()

            # Add summary as single item
            summary_item = ContextItem(
                content=summary,
                timestamp=datetime.now(),
                token_count=len(summary.split()),
                source="system",
                importance=0.6
            )
            self.context_window.add_item(summary_item)

            return {
                "summarized_count": len(items_to_summarize),
                "summary": summary,
                "checkpoint": checkpoint
            }

        return {}

    def get_context_summary(self) -> Dict[str, Any]:
        """Get current context summary."""
        return {
            "window_stats": self.context_window.get_usage_stats(),
            "conversation_state": self.conversation_state.get_dialog_state(),
            "active_checkpoints": len(self.checkpoints),
            "attended_items": len(self.attention.attention_scores)
        }


class ContextManager:
    """Main context management orchestrator."""

    def __init__(self, max_context_tokens: int = 8192):
        self.bridges: Dict[str, ContextBridge] = defaultdict(
            lambda: ContextBridge(window_size=max_context_tokens)
        )
        self.global_state: Dict[str, Any] = {}

    def get_bridge(self, session_id: str) -> ContextBridge:
        """Get context bridge for session."""
        return self.bridges[session_id]

    def process_interaction(self, session_id: str, user_input: str,
                           assistant_output: str, tokens: int) -> None:
        """Process interaction in session."""
        bridge = self.get_bridge(session_id)
        bridge.process_turn(user_input, assistant_output, tokens)

    def get_context_for_inference(self, session_id: str, query: str,
                                 max_items: int = 10) -> List[str]:
        """Get context for model inference."""
        bridge = self.get_bridge(session_id)

        # Check if compression needed
        stats = bridge.context_window.get_usage_stats()
        if stats["usage_percent"] > 85:
            bridge.compress_context()

        return bridge.get_relevant_context(query, max_items)

    def save_session(self, session_id: str) -> Dict[str, Any]:
        """Save session context."""
        bridge = self.get_bridge(session_id)
        return {
            "session_id": session_id,
            "turns": bridge.conversation_state.turns,
            "checkpoints": bridge.checkpoints,
            "context_summary": bridge.get_context_summary()
        }

    def load_session(self, session_data: Dict[str, Any]) -> None:
        """Load session context."""
        session_id = session_data["session_id"]
        bridge = self.get_bridge(session_id)

        # Restore turns
        for turn in session_data.get("turns", []):
            bridge.conversation_state.add_turn(turn["user"], turn["assistant"])

    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall context system statistics."""
        return {
            "active_sessions": len(self.bridges),
            "total_turns": sum(
                len(bridge.conversation_state.turns)
                for bridge in self.bridges.values()
            ),
            "total_checkpoints": sum(
                len(bridge.checkpoints)
                for bridge in self.bridges.values()
            ),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
_context_manager = None


def get_context_manager() -> ContextManager:
    """Get or create global context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
