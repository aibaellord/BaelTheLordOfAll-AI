#!/usr/bin/env python3
"""
BAEL - Natural Language Interface
Advanced natural language understanding for commands and queries.

Features:
- Intent recognition
- Entity extraction
- Slot filling
- Context-aware parsing
- Multi-language support
- Command disambiguation
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (Any, Callable, Dict, List, Optional, Pattern, Set, Tuple,
                    Union)

logger = logging.getLogger(__name__)


# =============================================================================
# TYPES
# =============================================================================

class EntityType(Enum):
    """Entity types for extraction."""
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    FILE_PATH = "file_path"
    URL = "url"
    EMAIL = "email"
    CODE = "code"
    LANGUAGE = "language"
    CUSTOM = "custom"


@dataclass
class Entity:
    """Extracted entity."""
    type: EntityType
    value: Any
    raw_value: str
    start: int
    end: int
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "value": self.value,
            "raw_value": self.raw_value,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


@dataclass
class Intent:
    """Recognized intent."""
    name: str
    confidence: float
    entities: Dict[str, Entity] = field(default_factory=dict)
    slots: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "confidence": self.confidence,
            "entities": {k: v.to_dict() for k, v in self.entities.items()},
            "slots": self.slots,
            "metadata": self.metadata
        }


@dataclass
class ParseResult:
    """Full parse result."""
    input_text: str
    intent: Optional[Intent]
    entities: List[Entity]
    alternatives: List[Intent] = field(default_factory=list)
    context_used: bool = False
    processing_time_ms: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_text": self.input_text,
            "intent": self.intent.to_dict() if self.intent else None,
            "entities": [e.to_dict() for e in self.entities],
            "alternatives": [a.to_dict() for a in self.alternatives],
            "processing_time_ms": self.processing_time_ms
        }


# =============================================================================
# ENTITY EXTRACTORS
# =============================================================================

class EntityExtractor(ABC):
    """Base entity extractor."""

    @abstractmethod
    def extract(self, text: str) -> List[Entity]:
        """Extract entities from text."""
        pass


class RegexExtractor(EntityExtractor):
    """Regex-based entity extractor."""

    PATTERNS = {
        EntityType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        EntityType.URL: r'https?://[^\s<>"{}|\\^`\[\]]+',
        EntityType.FILE_PATH: r'(?:[A-Za-z]:)?(?:/|\\)[\w.\-/\\]+',
        EntityType.NUMBER: r'-?\d+(?:\.\d+)?',
    }

    def __init__(self, patterns: Dict[EntityType, str] = None):
        self.patterns = {**self.PATTERNS, **(patterns or {})}
        self._compiled = {
            etype: re.compile(pattern, re.IGNORECASE)
            for etype, pattern in self.patterns.items()
        }

    def extract(self, text: str) -> List[Entity]:
        entities = []

        for etype, pattern in self._compiled.items():
            for match in pattern.finditer(text):
                value = self._parse_value(etype, match.group())
                entities.append(Entity(
                    type=etype,
                    value=value,
                    raw_value=match.group(),
                    start=match.start(),
                    end=match.end()
                ))

        return entities

    def _parse_value(self, etype: EntityType, raw: str) -> Any:
        """Parse raw value to typed value."""
        if etype == EntityType.NUMBER:
            return float(raw) if "." in raw else int(raw)
        return raw


class DateTimeExtractor(EntityExtractor):
    """Extract date and time entities."""

    # Relative date patterns
    RELATIVE_PATTERNS = {
        r'\btoday\b': lambda: datetime.now().date(),
        r'\btomorrow\b': lambda: (datetime.now() + timedelta(days=1)).date(),
        r'\byesterday\b': lambda: (datetime.now() - timedelta(days=1)).date(),
        r'\bnext week\b': lambda: (datetime.now() + timedelta(weeks=1)).date(),
        r'\blast week\b': lambda: (datetime.now() - timedelta(weeks=1)).date(),
        r'\bnext month\b': lambda: (datetime.now() + timedelta(days=30)).date(),
    }

    # Absolute date patterns
    DATE_PATTERNS = [
        (r'\b(\d{4})-(\d{2})-(\d{2})\b', '%Y-%m-%d'),
        (r'\b(\d{2})/(\d{2})/(\d{4})\b', '%m/%d/%Y'),
        (r'\b(\d{2})\.(\d{2})\.(\d{4})\b', '%d.%m.%Y'),
    ]

    # Time patterns
    TIME_PATTERNS = [
        (r'\b(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?\b', None),
        (r'\b(\d{1,2})\s*([AaPp][Mm])\b', None),
    ]

    # Duration patterns
    DURATION_PATTERNS = [
        (r'(\d+)\s*(seconds?|secs?|s)\b', 'seconds'),
        (r'(\d+)\s*(minutes?|mins?|m)\b', 'minutes'),
        (r'(\d+)\s*(hours?|hrs?|h)\b', 'hours'),
        (r'(\d+)\s*(days?|d)\b', 'days'),
        (r'(\d+)\s*(weeks?|w)\b', 'weeks'),
    ]

    def extract(self, text: str) -> List[Entity]:
        entities = []
        text_lower = text.lower()

        # Relative dates
        for pattern, date_func in self.RELATIVE_PATTERNS.items():
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                entities.append(Entity(
                    type=EntityType.DATE,
                    value=date_func(),
                    raw_value=match.group(),
                    start=match.start(),
                    end=match.end()
                ))

        # Absolute dates
        for pattern, format_str in self.DATE_PATTERNS:
            for match in re.finditer(pattern, text):
                try:
                    date_val = datetime.strptime(match.group(), format_str).date()
                    entities.append(Entity(
                        type=EntityType.DATE,
                        value=date_val,
                        raw_value=match.group(),
                        start=match.start(),
                        end=match.end()
                    ))
                except ValueError:
                    pass

        # Durations
        for pattern, unit in self.DURATION_PATTERNS:
            for match in re.finditer(pattern, text_lower):
                value = int(match.group(1))
                entities.append(Entity(
                    type=EntityType.DURATION,
                    value=timedelta(**{unit: value}),
                    raw_value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    metadata={"unit": unit, "value": value}
                ))

        return entities


class CodeExtractor(EntityExtractor):
    """Extract code blocks and language indicators."""

    LANGUAGES = {
        'python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'c++',
        'csharp', 'c#', 'go', 'rust', 'ruby', 'php', 'swift', 'kotlin',
        'scala', 'r', 'julia', 'sql', 'html', 'css', 'shell', 'bash'
    }

    def extract(self, text: str) -> List[Entity]:
        entities = []

        # Code blocks (```...```)
        for match in re.finditer(r'```(\w+)?\n(.*?)```', text, re.DOTALL):
            lang = match.group(1) or "unknown"
            code = match.group(2)
            entities.append(Entity(
                type=EntityType.CODE,
                value=code.strip(),
                raw_value=match.group(),
                start=match.start(),
                end=match.end(),
                metadata={"language": lang}
            ))

        # Inline code (`...`)
        for match in re.finditer(r'`([^`]+)`', text):
            entities.append(Entity(
                type=EntityType.CODE,
                value=match.group(1),
                raw_value=match.group(),
                start=match.start(),
                end=match.end(),
                metadata={"inline": True}
            ))

        # Language mentions
        for match in re.finditer(r'\b(\w+)\b', text.lower()):
            if match.group(1) in self.LANGUAGES:
                entities.append(Entity(
                    type=EntityType.LANGUAGE,
                    value=match.group(1),
                    raw_value=match.group(),
                    start=match.start(),
                    end=match.end()
                ))

        return entities


# =============================================================================
# INTENT PATTERNS
# =============================================================================

@dataclass
class IntentPattern:
    """Pattern for intent matching."""
    intent_name: str
    patterns: List[str]
    required_entities: List[str] = field(default_factory=list)
    optional_entities: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    priority: int = 0


class IntentMatcher:
    """Match intents using patterns."""

    def __init__(self):
        self.patterns: List[IntentPattern] = []
        self._compiled: Dict[str, List[Pattern]] = {}

    def add_pattern(self, pattern: IntentPattern) -> None:
        """Add an intent pattern."""
        self.patterns.append(pattern)

        # Compile regex patterns
        compiled = []
        for p in pattern.patterns:
            # Convert simple patterns to regex
            regex = self._pattern_to_regex(p)
            compiled.append(re.compile(regex, re.IGNORECASE))

        self._compiled[pattern.intent_name] = compiled

    def _pattern_to_regex(self, pattern: str) -> str:
        """Convert simple pattern to regex."""
        # Replace placeholders like {entity} with capture groups
        regex = re.escape(pattern)
        regex = re.sub(r'\\{(\w+)\\}', r'(?P<\1>.+?)', regex)

        # Make whitespace flexible
        regex = re.sub(r'\s+', r'\\s+', regex)

        return f'^{regex}$'

    def match(self, text: str) -> List[Tuple[IntentPattern, float, Dict[str, str]]]:
        """Match text against patterns."""
        matches = []
        text = text.strip()

        for pattern in self.patterns:
            for compiled in self._compiled.get(pattern.intent_name, []):
                match = compiled.match(text)
                if match:
                    # Extract captured groups as entities
                    captured = match.groupdict()

                    # Calculate confidence based on match specificity
                    confidence = 0.9 - (len(captured) * 0.05)

                    matches.append((pattern, confidence, captured))
                    break

        # Sort by priority and confidence
        matches.sort(key=lambda x: (x[0].priority, x[1]), reverse=True)

        return matches


# =============================================================================
# COMMAND PARSER
# =============================================================================

class CommandDefinition:
    """Definition of a command."""

    def __init__(
        self,
        name: str,
        description: str,
        patterns: List[str],
        handler: Callable = None,
        parameters: Dict[str, Dict[str, Any]] = None,
        examples: List[str] = None,
        aliases: List[str] = None
    ):
        self.name = name
        self.description = description
        self.patterns = patterns
        self.handler = handler
        self.parameters = parameters or {}
        self.examples = examples or []
        self.aliases = aliases or []


class CommandParser:
    """Parse commands from natural language."""

    def __init__(self):
        self.commands: Dict[str, CommandDefinition] = {}
        self.intent_matcher = IntentMatcher()
        self.extractors: List[EntityExtractor] = [
            RegexExtractor(),
            DateTimeExtractor(),
            CodeExtractor()
        ]

    def register_command(self, command: CommandDefinition) -> None:
        """Register a command."""
        self.commands[command.name] = command

        # Add to intent matcher
        pattern = IntentPattern(
            intent_name=command.name,
            patterns=command.patterns,
            examples=command.examples
        )
        self.intent_matcher.add_pattern(pattern)

        # Register aliases
        for alias in command.aliases:
            self.commands[alias] = command

    def parse(self, text: str) -> ParseResult:
        """Parse natural language input."""
        import time
        start = time.perf_counter()

        # Extract entities
        all_entities = []
        for extractor in self.extractors:
            entities = extractor.extract(text)
            all_entities.extend(entities)

        # Remove overlapping entities (keep higher confidence)
        all_entities = self._dedupe_entities(all_entities)

        # Match intents
        matches = self.intent_matcher.match(text)

        # Build intent from best match
        intent = None
        alternatives = []

        for pattern, confidence, captured in matches:
            intent_obj = Intent(
                name=pattern.intent_name,
                confidence=confidence,
                slots=captured
            )

            # Add extracted entities
            for entity in all_entities:
                entity_key = f"{entity.type.value}_{len(intent_obj.entities)}"
                intent_obj.entities[entity_key] = entity

            if intent is None:
                intent = intent_obj
            else:
                alternatives.append(intent_obj)

        duration = (time.perf_counter() - start) * 1000

        return ParseResult(
            input_text=text,
            intent=intent,
            entities=all_entities,
            alternatives=alternatives[:5],
            processing_time_ms=duration
        )

    def _dedupe_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove overlapping entities."""
        if not entities:
            return []

        # Sort by position and confidence
        entities.sort(key=lambda e: (e.start, -e.confidence))

        result = []
        last_end = -1

        for entity in entities:
            if entity.start >= last_end:
                result.append(entity)
                last_end = entity.end

        return result


# =============================================================================
# NATURAL LANGUAGE INTERFACE
# =============================================================================

class NLInterface:
    """Natural language interface for BAEL."""

    def __init__(self, llm_provider: Callable = None):
        self.parser = CommandParser()
        self.llm_provider = llm_provider
        self._setup_default_commands()

    def _setup_default_commands(self) -> None:
        """Setup default commands."""
        commands = [
            CommandDefinition(
                name="help",
                description="Get help on available commands",
                patterns=[
                    "help",
                    "help {topic}",
                    "how do I {action}",
                    "what can you do",
                    "show commands"
                ],
                examples=["help", "help with coding", "what can you do"]
            ),
            CommandDefinition(
                name="search",
                description="Search for information",
                patterns=[
                    "search for {query}",
                    "find {query}",
                    "look up {query}",
                    "search {query}"
                ],
                examples=["search for Python tutorials", "find recent news"]
            ),
            CommandDefinition(
                name="code",
                description="Generate or explain code",
                patterns=[
                    "write {language} code for {task}",
                    "generate {language} code to {task}",
                    "code {task}",
                    "explain this code"
                ],
                examples=["write Python code for sorting", "explain this code"]
            ),
            CommandDefinition(
                name="run",
                description="Execute code or commands",
                patterns=[
                    "run {code}",
                    "execute {code}",
                    "run this code"
                ],
                examples=["run print('hello')", "execute this"]
            ),
            CommandDefinition(
                name="file",
                description="File operations",
                patterns=[
                    "create file {path}",
                    "read file {path}",
                    "delete file {path}",
                    "edit file {path}"
                ],
                examples=["create file test.py", "read config.json"]
            ),
            CommandDefinition(
                name="task",
                description="Task management",
                patterns=[
                    "create task {description}",
                    "add todo {description}",
                    "remind me to {action}",
                    "schedule {action}"
                ],
                examples=["create task review PR", "remind me to call at 3pm"]
            ),
            CommandDefinition(
                name="analyze",
                description="Analyze data or code",
                patterns=[
                    "analyze {target}",
                    "review {target}",
                    "check {target}"
                ],
                examples=["analyze this code", "review the PR"]
            ),
            CommandDefinition(
                name="explain",
                description="Explain concepts or code",
                patterns=[
                    "explain {topic}",
                    "what is {topic}",
                    "describe {topic}",
                    "how does {topic} work"
                ],
                examples=["explain async/await", "what is a closure"]
            ),
            CommandDefinition(
                name="refactor",
                description="Refactor code",
                patterns=[
                    "refactor {target}",
                    "improve {target}",
                    "optimize {target}",
                    "clean up {target}"
                ],
                examples=["refactor this function", "optimize the loop"]
            ),
            CommandDefinition(
                name="test",
                description="Generate or run tests",
                patterns=[
                    "test {target}",
                    "write tests for {target}",
                    "generate tests for {target}",
                    "run tests"
                ],
                examples=["test this function", "write tests for UserService"]
            )
        ]

        for cmd in commands:
            self.parser.register_command(cmd)

    async def process(self, input_text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process natural language input."""
        context = context or {}

        # Parse input
        result = self.parser.parse(input_text)

        # If no intent matched, try LLM fallback
        if result.intent is None and self.llm_provider:
            result = await self._llm_fallback(input_text, context)

        # Execute command if handler available
        response = None
        if result.intent:
            command = self.parser.commands.get(result.intent.name)
            if command and command.handler:
                try:
                    response = await command.handler(result.intent, context)
                except Exception as e:
                    logger.error(f"Command execution failed: {e}")
                    response = {"error": str(e)}

        return {
            "parse_result": result.to_dict(),
            "response": response,
            "success": result.intent is not None
        }

    async def _llm_fallback(self, input_text: str, context: Dict[str, Any]) -> ParseResult:
        """Use LLM for intent classification."""
        if not self.llm_provider:
            return ParseResult(input_text=input_text, intent=None, entities=[])

        prompt = f"""Classify the following user input into one of these intents:
{', '.join(self.parser.commands.keys())}

User input: "{input_text}"

Respond with JSON:
{{"intent": "<intent_name>", "confidence": <0.0-1.0>, "slots": {{}}}}"
"""

        try:
            response = await self.llm_provider(prompt)
            data = json.loads(response)

            intent = Intent(
                name=data.get("intent", "unknown"),
                confidence=data.get("confidence", 0.5),
                slots=data.get("slots", {})
            )

            return ParseResult(
                input_text=input_text,
                intent=intent,
                entities=[],
                context_used=True
            )

        except Exception as e:
            logger.error(f"LLM fallback failed: {e}")
            return ParseResult(input_text=input_text, intent=None, entities=[])

    def get_suggestions(self, partial_input: str) -> List[str]:
        """Get command suggestions for partial input."""
        suggestions = []
        partial_lower = partial_input.lower()

        for cmd in self.parser.commands.values():
            # Match by name or alias
            if cmd.name.startswith(partial_lower):
                suggestions.append(cmd.name)
            for alias in cmd.aliases:
                if alias.startswith(partial_lower):
                    suggestions.append(alias)

            # Match by example
            for example in cmd.examples:
                if example.lower().startswith(partial_lower):
                    suggestions.append(example)

        return list(set(suggestions))[:10]


# =============================================================================
# CONVERSATION HANDLER
# =============================================================================

@dataclass
class ConversationTurn:
    """Single conversation turn."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationHandler:
    """Handle multi-turn conversations."""

    def __init__(self, nl_interface: NLInterface, max_history: int = 20):
        self.nl_interface = nl_interface
        self.max_history = max_history
        self.conversations: Dict[str, List[ConversationTurn]] = {}

    def get_or_create(self, session_id: str) -> List[ConversationTurn]:
        """Get or create conversation history."""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        return self.conversations[session_id]

    async def process_turn(
        self,
        session_id: str,
        user_input: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Process a conversation turn."""
        history = self.get_or_create(session_id)

        # Add user turn
        history.append(ConversationTurn(
            role="user",
            content=user_input
        ))

        # Build context from history
        context = {
            "history": [
                {"role": t.role, "content": t.content}
                for t in history[-self.max_history:]
            ],
            "session_id": session_id
        }

        # Process
        result = await self.nl_interface.process(user_input, context)

        # Generate response
        response_text = self._generate_response(result)

        # Add assistant turn
        history.append(ConversationTurn(
            role="assistant",
            content=response_text,
            metadata={"parse_result": result["parse_result"]}
        ))

        # Trim history
        if len(history) > self.max_history * 2:
            self.conversations[session_id] = history[-self.max_history:]

        return response_text, result

    def _generate_response(self, result: Dict[str, Any]) -> str:
        """Generate response text from result."""
        if result.get("response"):
            return str(result["response"])

        parse_result = result.get("parse_result", {})
        intent = parse_result.get("intent")

        if intent:
            return f"Understood command: {intent['name']}"
        else:
            return "I'm not sure what you mean. Try 'help' for available commands."

    def clear_session(self, session_id: str) -> None:
        """Clear conversation history."""
        if session_id in self.conversations:
            del self.conversations[session_id]


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Demo the NL interface."""
    nl = NLInterface()

    test_inputs = [
        "help",
        "write Python code for sorting a list",
        "search for machine learning tutorials",
        "explain what async/await means",
        "create file test.py",
        "remind me to review the PR tomorrow",
        "run print('hello world')"
    ]

    print("BAEL Natural Language Interface Demo")
    print("=" * 50)

    for input_text in test_inputs:
        print(f"\nInput: {input_text}")
        result = await nl.process(input_text)

        if result["parse_result"]["intent"]:
            intent = result["parse_result"]["intent"]
            print(f"Intent: {intent['name']} (confidence: {intent['confidence']:.2f})")
            if intent["slots"]:
                print(f"Slots: {intent['slots']}")
        else:
            print("No intent matched")

        if result["parse_result"]["entities"]:
            print(f"Entities: {len(result['parse_result']['entities'])} found")

    # Test suggestions
    print("\n" + "=" * 50)
    print("Suggestions for 'sea':", nl.get_suggestions("sea"))
    print("Suggestions for 'code':", nl.get_suggestions("code"))


if __name__ == "__main__":
    asyncio.run(main())
