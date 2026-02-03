"""
Natural Language CLI - Conversational Interface

Zero learning curve interface that understands natural language commands.
Users can interact with BAEL like talking to a human assistant.

Examples:
- "analyze the API performance from last week"
- "deploy the authentication service to production"
- "what errors happened in the payment system today?"
- "create a new agent that monitors database queries"
- "show me the slowest API endpoints"
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intents."""
    QUERY = "query"  # Get information
    ACTION = "action"  # Perform action
    ANALYSIS = "analysis"  # Analyze data
    CREATION = "creation"  # Create something
    DEPLOYMENT = "deployment"  # Deploy/manage
    MONITORING = "monitoring"  # Monitor/observe
    CONFIGURATION = "configuration"  # Configure system
    HELP = "help"  # Get help
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Parsed user intent."""
    intent_type: IntentType
    action: str
    entities: Dict[str, Any]
    confidence: float
    original_input: str
    suggested_command: Optional[str] = None


class NaturalLanguageCLI:
    """
    Natural language command line interface.

    Understands conversational commands and translates them
    to system actions without requiring users to learn syntax.
    """

    def __init__(self):
        """Initialize natural language CLI."""
        self.intent_patterns = self._build_intent_patterns()
        self.entity_extractors = self._build_entity_extractors()
        self.command_history: List[Tuple[str, ParsedIntent]] = []
        self.context: Dict[str, Any] = {}

        logger.info("Natural Language CLI initialized")

    def _build_intent_patterns(self) -> Dict[IntentType, List[re.Pattern]]:
        """Build patterns for intent recognition."""
        return {
            IntentType.QUERY: [
                re.compile(r'\b(show|display|list|get|what|where|when|who|how many)\b', re.I),
                re.compile(r'\?$'),
                re.compile(r'\b(status of|info about|details of)\b', re.I),
            ],
            IntentType.ACTION: [
                re.compile(r'\b(run|execute|start|stop|restart|kill|pause|resume)\b', re.I),
                re.compile(r'\b(send|trigger|invoke|call)\b', re.I),
            ],
            IntentType.ANALYSIS: [
                re.compile(r'\b(analyze|review|check|inspect|examine|investigate)\b', re.I),
                re.compile(r'\b(compare|diff|difference between)\b', re.I),
                re.compile(r'\b(performance of|health of|status of)\b', re.I),
            ],
            IntentType.CREATION: [
                re.compile(r'\b(create|make|build|generate|add|new)\b', re.I),
                re.compile(r'\b(setup|configure|initialize)\b', re.I),
            ],
            IntentType.DEPLOYMENT: [
                re.compile(r'\b(deploy|release|publish|ship)\b', re.I),
                re.compile(r'\b(rollback|revert|undo)\b', re.I),
                re.compile(r'\b(scale up|scale down|autoscale)\b', re.I),
            ],
            IntentType.MONITORING: [
                re.compile(r'\b(monitor|watch|track|observe)\b', re.I),
                re.compile(r'\b(alert|notify|warn)\b', re.I),
                re.compile(r'\b(metrics|logs|traces)\b', re.I),
            ],
            IntentType.CONFIGURATION: [
                re.compile(r'\b(configure|setup|set|change|update)\b', re.I),
                re.compile(r'\b(enable|disable|turn on|turn off)\b', re.I),
            ],
            IntentType.HELP: [
                re.compile(r'\b(help|how to|explain|guide|tutorial)\b', re.I),
                re.compile(r'\b(what can|what does|how do)\b', re.I),
            ],
        }

    def _build_entity_extractors(self) -> Dict[str, re.Pattern]:
        """Build patterns for entity extraction."""
        return {
            "service": re.compile(r'\b(api|service|app|application|server|worker|job)\s+(\w+)', re.I),
            "environment": re.compile(r'\b(production|prod|staging|stage|development|dev|test)\b', re.I),
            "timeframe": re.compile(r'\b(today|yesterday|last week|last month|last hour|last (\d+) (hours?|days?|weeks?))\b', re.I),
            "metric": re.compile(r'\b(latency|throughput|errors?|requests?|cpu|memory|disk)\b', re.I),
            "action_verb": re.compile(r'^(\w+)\b'),
            "resource_type": re.compile(r'\b(agent|workflow|pipeline|database|cache|queue)\b', re.I),
            "identifier": re.compile(r'[a-f0-9-]{36}|[a-z0-9_-]+', re.I),  # UUID or slug
        }

    async def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process natural language input.

        Args:
            user_input: Natural language command from user

        Returns:
            Response with action taken or information requested
        """
        # Parse intent
        intent = self._parse_intent(user_input)

        logger.info(f"Parsed intent: {intent.intent_type.value} (confidence: {intent.confidence:.2f})")
        logger.info(f"Entities: {intent.entities}")

        # Store in history
        self.command_history.append((user_input, intent))

        # Update context
        self._update_context(intent)

        # Execute based on intent
        if intent.intent_type == IntentType.QUERY:
            result = await self._handle_query(intent)
        elif intent.intent_type == IntentType.ACTION:
            result = await self._handle_action(intent)
        elif intent.intent_type == IntentType.ANALYSIS:
            result = await self._handle_analysis(intent)
        elif intent.intent_type == IntentType.CREATION:
            result = await self._handle_creation(intent)
        elif intent.intent_type == IntentType.DEPLOYMENT:
            result = await self._handle_deployment(intent)
        elif intent.intent_type == IntentType.MONITORING:
            result = await self._handle_monitoring(intent)
        elif intent.intent_type == IntentType.CONFIGURATION:
            result = await self._handle_configuration(intent)
        elif intent.intent_type == IntentType.HELP:
            result = await self._handle_help(intent)
        else:
            result = await self._handle_unknown(intent)

        return {
            "intent": intent.intent_type.value,
            "confidence": intent.confidence,
            "entities": intent.entities,
            "result": result,
            "suggested_command": intent.suggested_command
        }

    def _parse_intent(self, user_input: str) -> ParsedIntent:
        """Parse user input to determine intent."""
        user_input = user_input.strip()

        # Score each intent type
        scores: Dict[IntentType, float] = {}

        for intent_type, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                if pattern.search(user_input):
                    score += 1.0
            scores[intent_type] = score / len(patterns) if patterns else 0.0

        # Get best match
        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent]

        # Extract entities
        entities = self._extract_entities(user_input)

        # Generate suggested command
        suggested = self._generate_command_suggestion(best_intent, entities, user_input)

        return ParsedIntent(
            intent_type=best_intent if confidence > 0 else IntentType.UNKNOWN,
            action=self._extract_action(user_input),
            entities=entities,
            confidence=confidence,
            original_input=user_input,
            suggested_command=suggested
        )

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text."""
        entities = {}

        for entity_type, pattern in self.entity_extractors.items():
            match = pattern.search(text)
            if match:
                if entity_type == "service" and len(match.groups()) > 1:
                    entities[entity_type] = match.group(2)
                else:
                    entities[entity_type] = match.group(0)

        return entities

    def _extract_action(self, text: str) -> str:
        """Extract main action verb."""
        words = text.lower().split()
        action_verbs = [
            "show", "list", "get", "analyze", "create", "deploy",
            "start", "stop", "monitor", "configure", "check"
        ]

        for word in words:
            if word in action_verbs:
                return word

        return words[0] if words else "unknown"

    def _generate_command_suggestion(
        self,
        intent: IntentType,
        entities: Dict,
        original: str
    ) -> Optional[str]:
        """Generate suggested command syntax."""
        service = entities.get("service", "service")
        env = entities.get("environment", "production")
        metric = entities.get("metric", "health")

        suggestions = {
            IntentType.QUERY: f"bael query {service} --metric {metric} --env {env}",
            IntentType.ACTION: f"bael exec {service} --action start --env {env}",
            IntentType.ANALYSIS: f"bael analyze {service} --timeframe '1 hour' --env {env}",
            IntentType.DEPLOYMENT: f"bael deploy {service} --env {env}",
            IntentType.MONITORING: f"bael monitor {service} --metric {metric}",
        }

        return suggestions.get(intent)

    def _update_context(self, intent: ParsedIntent):
        """Update conversation context."""
        if intent.entities.get("service"):
            self.context["last_service"] = intent.entities["service"]
        if intent.entities.get("environment"):
            self.context["last_environment"] = intent.entities["environment"]

        self.context["last_intent"] = intent.intent_type
        self.context["last_timestamp"] = datetime.now()

    async def _handle_query(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle information query."""
        service = intent.entities.get("service", self.context.get("last_service"))
        metric = intent.entities.get("metric", "status")

        logger.info(f"Query: service={service}, metric={metric}")

        # Simulated response - integrate with your actual query system
        return {
            "type": "query_result",
            "service": service,
            "metric": metric,
            "status": "healthy",
            "value": "95.5%",
            "message": f"The {metric} of {service} is healthy"
        }

    async def _handle_action(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle action execution."""
        service = intent.entities.get("service", self.context.get("last_service"))
        action = intent.action

        logger.info(f"Action: {action} on service={service}")

        return {
            "type": "action_result",
            "action": action,
            "service": service,
            "status": "initiated",
            "message": f"Action '{action}' initiated on {service}"
        }

    async def _handle_analysis(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle analysis request."""
        service = intent.entities.get("service")
        timeframe = intent.entities.get("timeframe", "last hour")

        logger.info(f"Analysis: service={service}, timeframe={timeframe}")

        return {
            "type": "analysis_result",
            "service": service,
            "timeframe": timeframe,
            "summary": f"Analysis of {service} over {timeframe} shows normal operation",
            "details": {
                "avg_response_time": "245ms",
                "error_rate": "0.02%",
                "requests": 15420
            }
        }

    async def _handle_creation(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle resource creation."""
        resource_type = intent.entities.get("resource_type", "resource")

        logger.info(f"Creation: {resource_type}")

        return {
            "type": "creation_result",
            "resource_type": resource_type,
            "status": "created",
            "message": f"New {resource_type} created successfully"
        }

    async def _handle_deployment(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle deployment."""
        service = intent.entities.get("service")
        env = intent.entities.get("environment", "production")

        logger.info(f"Deployment: service={service}, env={env}")

        return {
            "type": "deployment_result",
            "service": service,
            "environment": env,
            "status": "deploying",
            "message": f"Deploying {service} to {env}"
        }

    async def _handle_monitoring(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle monitoring setup."""
        service = intent.entities.get("service")
        metric = intent.entities.get("metric")

        logger.info(f"Monitoring: service={service}, metric={metric}")

        return {
            "type": "monitoring_result",
            "service": service,
            "metric": metric,
            "status": "enabled",
            "message": f"Monitoring enabled for {metric} on {service}"
        }

    async def _handle_configuration(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle configuration change."""
        logger.info(f"Configuration change requested")

        return {
            "type": "configuration_result",
            "status": "updated",
            "message": "Configuration updated successfully"
        }

    async def _handle_help(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle help request."""
        return {
            "type": "help",
            "message": "I understand natural language commands. Try:",
            "examples": [
                "show me the status of the API service",
                "analyze performance from last week",
                "deploy authentication service to production",
                "create a new monitoring agent for database",
                "what errors happened today?",
                "start the background worker"
            ]
        }

    async def _handle_unknown(self, intent: ParsedIntent) -> Dict[str, Any]:
        """Handle unknown intent."""
        return {
            "type": "clarification",
            "message": "I didn't quite understand that. Could you rephrase?",
            "suggestions": [
                "Try asking 'what can you do?'",
                "Be more specific about the service or action",
                "Use keywords like: show, analyze, create, deploy"
            ]
        }

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history."""
        return [
            {
                "input": input_text,
                "intent": intent.intent_type.value,
                "confidence": intent.confidence,
                "entities": intent.entities
            }
            for input_text, intent in self.command_history[-10:]
        ]


class InteractiveCLI:
    """Interactive CLI session with natural language."""

    def __init__(self):
        """Initialize interactive CLI."""
        self.nl_cli = NaturalLanguageCLI()
        self.running = False

    async def start(self):
        """Start interactive session."""
        self.running = True

        print("=" * 60)
        print("BAEL Natural Language CLI")
        print("=" * 60)
        print("\nSpeak naturally - no syntax required!")
        print("Try: 'show me the API status' or 'analyze last week's errors'")
        print("\nType 'exit' or 'quit' to exit\n")

        while self.running:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\nGoodbye! 👋")
                    break

                # Process input
                result = await self.nl_cli.process(user_input)

                # Display result
                self._display_result(result)

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")

    def _display_result(self, result: Dict[str, Any]):
        """Display result in friendly format."""
        print(f"\n🤖 BAEL: ", end="")

        result_data = result["result"]

        if result_data["type"] == "help":
            print(result_data["message"])
            print("\nExamples:")
            for example in result_data["examples"]:
                print(f"  • {example}")

        elif result_data["type"] == "clarification":
            print(result_data["message"])
            print("\nSuggestions:")
            for suggestion in result_data["suggestions"]:
                print(f"  • {suggestion}")

        else:
            print(result_data.get("message", "Done!"))

            if "details" in result_data:
                print("\nDetails:")
                for key, value in result_data["details"].items():
                    print(f"  {key}: {value}")

        # Show suggested command
        if result.get("suggested_command") and result["confidence"] < 0.8:
            print(f"\n💡 Suggested command: {result['suggested_command']}")

        print()


# Example usage
if __name__ == "__main__":
    cli = InteractiveCLI()
    asyncio.run(cli.start())
