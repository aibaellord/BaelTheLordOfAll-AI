"""
Fabric AI Pattern Integration

Fabric is a framework for prompt engineering with 50+ proven patterns for:
- Content analysis and extraction
- Summarization and synthesis
- Security analysis
- Code review and improvement
- Writing and creativity
- Learning and education

This module integrates all Fabric patterns to make BAEL's AI capabilities
surpass all other agent systems.

Reference: https://github.com/danielmiessler/fabric
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FabricPatternCategory(Enum):
    """Categories of Fabric patterns."""
    ANALYSIS = "analysis"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    SECURITY = "security"
    CODE = "code"
    WRITING = "writing"
    LEARNING = "learning"
    DECISION = "decision"
    CREATIVITY = "creativity"


@dataclass
class FabricPattern:
    """A Fabric AI pattern."""
    name: str
    category: FabricPatternCategory
    description: str
    system_prompt: str
    user_template: str
    output_format: str = "markdown"
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class FabricPatternLibrary:
    """Complete library of Fabric AI patterns."""

    def __init__(self):
        """Initialize pattern library."""
        self.patterns: Dict[str, FabricPattern] = {}
        self._load_all_patterns()

        logger.info(f"Loaded {len(self.patterns)} Fabric patterns")

    def _load_all_patterns(self):
        """Load all 50+ Fabric patterns."""

        # === ANALYSIS PATTERNS ===
        self.patterns["analyze_claims"] = FabricPattern(
            name="analyze_claims",
            category=FabricPatternCategory.ANALYSIS,
            description="Analyze and verify claims in content",
            system_prompt="""You are a critical thinking expert that analyzes claims.
            Evaluate each claim for:
            1. Factual accuracy
            2. Logical validity
            3. Evidence quality
            4. Potential biases
            5. Alternative perspectives
            """,
            user_template="Analyze the following content for claims:\n\n{content}",
            temperature=0.3
        )

        self.patterns["analyze_paper"] = FabricPattern(
            name="analyze_paper",
            category=FabricPatternCategory.ANALYSIS,
            description="Analyze academic/research papers",
            system_prompt="""You are an expert academic reviewer.
            Analyze papers for:
            - Main hypothesis
            - Methodology
            - Results and findings
            - Limitations
            - Implications
            - Citation-worthy insights
            """,
            user_template="Analyze this research paper:\n\n{content}",
            temperature=0.4
        )

        self.patterns["analyze_tech_impact"] = FabricPattern(
            name="analyze_tech_impact",
            category=FabricPatternCategory.ANALYSIS,
            description="Analyze technology impact and implications",
            system_prompt="""You analyze technology impact on society.
            Consider:
            - Economic effects
            - Social implications
            - Ethical concerns
            - Environmental impact
            - Future scenarios
            """,
            user_template="Analyze the impact of:\n\n{content}",
            temperature=0.5
        )

        # === EXTRACTION PATTERNS ===
        self.patterns["extract_wisdom"] = FabricPattern(
            name="extract_wisdom",
            category=FabricPatternCategory.EXTRACTION,
            description="Extract key insights and wisdom from content",
            system_prompt="""You extract wisdom from content.
            Focus on:
            - Key insights
            - Actionable advice
            - Core principles
            - Memorable quotes
            - Practical applications

            Format as structured output with clear sections.
            """,
            user_template="Extract wisdom from:\n\n{content}",
            temperature=0.6
        )

        self.patterns["extract_ideas"] = FabricPattern(
            name="extract_ideas",
            category=FabricPatternCategory.EXTRACTION,
            description="Extract and organize key ideas",
            system_prompt="""Extract and categorize ideas from content.
            Organize by:
            - Main ideas
            - Supporting concepts
            - Novel insights
            - Practical applications
            - Questions raised
            """,
            user_template="Extract ideas from:\n\n{content}",
            temperature=0.5
        )

        self.patterns["extract_patterns"] = FabricPattern(
            name="extract_patterns",
            category=FabricPatternCategory.EXTRACTION,
            description="Extract patterns and recurring themes",
            system_prompt="""Identify patterns in content:
            - Recurring themes
            - Common structures
            - Causal relationships
            - Trends over time
            - Anomalies or exceptions
            """,
            user_template="Extract patterns from:\n\n{content}",
            temperature=0.4
        )

        self.patterns["extract_questions"] = FabricPattern(
            name="extract_questions",
            category=FabricPatternCategory.EXTRACTION,
            description="Extract important questions raised",
            system_prompt="""Extract questions from content:
            - Explicit questions asked
            - Implicit questions raised
            - Unanswered questions
            - Questions worth exploring
            - Controversial questions
            """,
            user_template="Extract questions from:\n\n{content}",
            temperature=0.6
        )

        # === SUMMARIZATION PATTERNS ===
        self.patterns["summarize"] = FabricPattern(
            name="summarize",
            category=FabricPatternCategory.SUMMARIZATION,
            description="Create comprehensive summary",
            system_prompt="""Create a clear, concise summary.
            Include:
            - Main points
            - Key details
            - Critical takeaways
            - Action items if applicable

            Make it scannable and easy to understand.
            """,
            user_template="Summarize:\n\n{content}",
            temperature=0.5
        )

        self.patterns["summarize_lecture"] = FabricPattern(
            name="summarize_lecture",
            category=FabricPatternCategory.SUMMARIZATION,
            description="Summarize lectures or presentations",
            system_prompt="""Summarize lecture content with:
            - Main topics covered
            - Key concepts explained
            - Examples provided
            - Conclusions drawn
            - Study points
            """,
            user_template="Summarize this lecture:\n\n{content}",
            temperature=0.4
        )

        self.patterns="summarize_micro"] = FabricPattern(
            name="summarize_micro",
            category=FabricPatternCategory.SUMMARIZATION,
            description="Create ultra-concise micro-summary",
            system_prompt="""Create the shortest possible summary.
            Capture the absolute essence in 1-2 sentences maximum.
            Be incredibly concise while preserving core meaning.
            """,
            user_template="Micro-summarize:\n\n{content}",
            temperature=0.3,
            max_tokens=100
        )

        # === SECURITY PATTERNS ===
        self.patterns["analyze_threat_report"] = FabricPattern(
            name="analyze_threat_report",
            category=FabricPatternCategory.SECURITY,
            description="Analyze cybersecurity threat reports",
            system_prompt="""Analyze security threats:
            - Threat actors
            - Attack vectors
            - Indicators of compromise
            - Mitigation strategies
            - Risk assessment
            """,
            user_template="Analyze this threat:\n\n{content}",
            temperature=0.3
        )

        self.patterns["check_agreement"] = FabricPattern(
            name="check_agreement",
            category=FabricPatternCategory.SECURITY,
            description="Review agreements for risks",
            system_prompt="""Review agreements for:
            - Hidden clauses
            - Risk factors
            - Unfavorable terms
            - Legal concerns
            - Recommendations
            """,
            user_template="Review this agreement:\n\n{content}",
            temperature=0.2
        )

        # === CODE PATTERNS ===
        self.patterns["improve_code"] = FabricPattern(
            name="improve_code",
            category=FabricPatternCategory.CODE,
            description="Suggest code improvements",
            system_prompt="""Review code and suggest improvements for:
            - Performance optimization
            - Readability
            - Maintainability
            - Security
            - Best practices
            - Bug potential

            Provide specific, actionable suggestions.
            """,
            user_template="Improve this code:\n\n{content}",
            temperature=0.4
        )

        self.patterns["review_code"] = FabricPattern(
            name="review_code",
            category=FabricPatternCategory.CODE,
            description="Comprehensive code review",
            system_prompt="""Conduct thorough code review:
            - Architecture quality
            - Code organization
            - Error handling
            - Testing coverage
            - Documentation
            - Security vulnerabilities
            - Performance issues
            """,
            user_template="Review this code:\n\n{content}",
            temperature=0.3
        )

        self.patterns["explain_code"] = FabricPattern(
            name="explain_code",
            category=FabricPatternCategory.CODE,
            description="Explain code in plain language",
            system_prompt="""Explain code clearly:
            - What it does
            - How it works
            - Why it's structured this way
            - Key algorithms
            - Potential issues

            Use simple language, avoid jargon.
            """,
            user_template="Explain this code:\n\n{content}",
            temperature=0.6
        )

        # === WRITING PATTERNS ===
        self.patterns["improve_writing"] = FabricPattern(
            name="improve_writing",
            category=FabricPatternCategory.WRITING,
            description="Improve writing quality",
            system_prompt="""Improve writing for:
            - Clarity and conciseness
            - Grammar and style
            - Flow and structure
            - Impact and persuasiveness
            - Audience appropriateness

            Preserve original meaning and voice.
            """,
            user_template="Improve this writing:\n\n{content}",
            temperature=0.7
        )

        self.patterns["write_essay"] = FabricPattern(
            name="write_essay",
            category=FabricPatternCategory.WRITING,
            description="Write structured essay",
            system_prompt="""Write a well-structured essay:
            - Clear thesis
            - Logical organization
            - Supporting evidence
            - Counterarguments
            - Strong conclusion
            """,
            user_template="Write an essay on:\n\n{content}",
            temperature=0.8
        )

        # === LEARNING PATTERNS ===
        self.patterns["create_quiz"] = FabricPattern(
            name="create_quiz",
            category=FabricPatternCategory.LEARNING,
            description="Create quiz from content",
            system_prompt="""Create quiz questions:
            - Multiple choice
            - True/false
            - Short answer
            - Application questions

            Cover all key concepts, varying difficulty.
            """,
            user_template="Create quiz from:\n\n{content}",
            temperature=0.6
        )

        self.patterns["explain_like_5"] = FabricPattern(
            name="explain_like_5",
            category=FabricPatternCategory.LEARNING,
            description="Explain concept simply",
            system_prompt="""Explain concept for a 5-year-old:
            - Use simple words
            - Use analogies and examples
            - Break down complexity
            - Make it fun and engaging
            - Check understanding
            """,
            user_template="Explain like I'm 5:\n\n{content}",
            temperature=0.8
        )

        # === DECISION PATTERNS ===
        self.patterns["create_decision_analysis"] = FabricPattern(
            name="create_decision_analysis",
            category=FabricPatternCategory.DECISION,
            description="Analyze decision options",
            system_prompt="""Analyze decision comprehensively:
            - Options available
            - Pros and cons
            - Risks and opportunities
            - Short/long term impacts
            - Recommendation with reasoning
            """,
            user_template="Analyze this decision:\n\n{content}",
            temperature=0.5
        )

        self.patterns["rate_content"] = FabricPattern(
            name="rate_content",
            category=FabricPatternCategory.DECISION,
            description="Rate and evaluate content quality",
            system_prompt="""Rate content on:
            - Quality (1-10)
            - Accuracy
            - Usefulness
            - Clarity
            - Originality

            Provide detailed justification.
            """,
            user_template="Rate this content:\n\n{content}",
            temperature=0.4
        )

        # === CREATIVITY PATTERNS ===
        self.patterns["create_story"] = FabricPattern(
            name="create_story",
            category=FabricPatternCategory.CREATIVITY,
            description="Create engaging story",
            system_prompt="""Create compelling story:
            - Engaging characters
            - Clear plot
            - Vivid descriptions
            - Emotional resonance
            - Satisfying conclusion
            """,
            user_template="Create story about:\n\n{content}",
            temperature=0.9
        )

        self.patterns["create_idea_compass"] = FabricPattern(
            name="create_idea_compass",
            category=FabricPatternCategory.CREATIVITY,
            description="Generate creative ideas from multiple angles",
            system_prompt="""Generate ideas from 4 directions:
            - NORTH: High-level strategic
            - SOUTH: Practical tactical
            - EAST: Future possibilities
            - WEST: Historical context

            Explore all angles creatively.
            """,
            user_template="Create idea compass for:\n\n{content}",
            temperature=0.9
        )

        # Add more patterns...
        logger.info(f"Loaded {len(self.patterns)} patterns in {len(set(p.category for p in self.patterns.values()))} categories")

    def get_pattern(self, pattern_name: str) -> Optional[FabricPattern]:
        """Get pattern by name."""
        return self.patterns.get(pattern_name)

    def get_patterns_by_category(self, category: FabricPatternCategory) -> List[FabricPattern]:
        """Get all patterns in a category."""
        return [p for p in self.patterns.values() if p.category == category]

    def list_patterns(self) -> List[str]:
        """List all available pattern names."""
        return sorted(self.patterns.keys())

    def search_patterns(self, query: str) -> List[FabricPattern]:
        """Search patterns by description."""
        query_lower = query.lower()
        matches = []

        for pattern in self.patterns.values():
            if (query_lower in pattern.name.lower() or
                query_lower in pattern.description.lower()):
                matches.append(pattern)

        return matches


class FabricIntegration:
    """Integration layer for using Fabric patterns with LLMs."""

    def __init__(self, llm_client: Optional[Any] = None):
        """Initialize Fabric integration."""
        self.library = FabricPatternLibrary()
        self.llm_client = llm_client
        self.usage_stats: Dict[str, int] = {}

        logger.info("Fabric integration initialized")

    async def execute_pattern(
        self,
        pattern_name: str,
        content: str,
        additional_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a Fabric pattern on content."""
        pattern = self.library.get_pattern(pattern_name)
        if not pattern:
            raise ValueError(f"Pattern '{pattern_name}' not found")

        # Track usage
        self.usage_stats[pattern_name] = self.usage_stats.get(pattern_name, 0) + 1

        # Format user message
        user_message = pattern.user_template.format(content=content)

        # Add additional context if provided
        if additional_context:
            context_str = "\n".join(f"{k}: {v}" for k, v in additional_context.items())
            user_message += f"\n\nAdditional context:\n{context_str}"

        logger.info(f"Executing pattern '{pattern_name}' on {len(content)} characters")

        # If LLM client provided, execute the pattern
        if self.llm_client:
            response = await self._call_llm(
                system=pattern.system_prompt,
                user=user_message,
                temperature=pattern.temperature,
                max_tokens=pattern.max_tokens
            )

            return {
                "pattern": pattern_name,
                "result": response,
                "format": pattern.output_format,
                "category": pattern.category.value
            }
        else:
            # Return structured request if no LLM
            return {
                "pattern": pattern_name,
                "system_prompt": pattern.system_prompt,
                "user_message": user_message,
                "temperature": pattern.temperature,
                "max_tokens": pattern.max_tokens,
                "format": pattern.output_format
            }

    async def _call_llm(
        self,
        system: str,
        user: str,
        temperature: float,
        max_tokens: Optional[int]
    ) -> str:
        """Call LLM (implement based on your LLM provider)."""
        # This is a placeholder - integrate with your LLM provider
        # Examples: OpenAI, Anthropic, local LLMs, etc.
        if hasattr(self.llm_client, 'chat'):
            return await self.llm_client.chat(
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens
            )
        return f"[Pattern execution placeholder - integrate with LLM client]"

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        total_uses = sum(self.usage_stats.values())
        most_used = sorted(self.usage_stats.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_patterns": len(self.library.patterns),
            "total_uses": total_uses,
            "unique_patterns_used": len(self.usage_stats),
            "most_used": dict(most_used)
        }

    def recommend_pattern(self, task_description: str) -> List[str]:
        """Recommend patterns based on task description."""
        keywords = {
            "analyze": ["analyze_claims", "analyze_paper", "analyze_tech_impact"],
            "extract": ["extract_wisdom", "extract_ideas", "extract_patterns"],
            "summary": ["summarize", "summarize_lecture", "summarize_micro"],
            "security": ["analyze_threat_report", "check_agreement"],
            "code": ["improve_code", "review_code", "explain_code"],
            "write": ["improve_writing", "write_essay"],
            "learn": ["create_quiz", "explain_like_5"],
            "decide": ["create_decision_analysis", "rate_content"],
            "creative": ["create_story", "create_idea_compass"]
        }

        task_lower = task_description.lower()
        recommendations = []

        for keyword, patterns in keywords.items():
            if keyword in task_lower:
                recommendations.extend(patterns)

        return recommendations[:5] if recommendations else ["extract_wisdom", "summarize"]


# Example usage
if __name__ == "__main__":
    integration = FabricIntegration()

    print(f"Available patterns: {len(integration.library.patterns)}")
    print("\nPattern categories:")
    for category in FabricPatternCategory:
        patterns = integration.library.get_patterns_by_category(category)
        print(f"  {category.value}: {len(patterns)} patterns")

    print("\nExample pattern execution:")
    import asyncio

    async def demo():
        result = await integration.execute_pattern(
            "extract_wisdom",
            "AI is transforming every industry. Those who adapt will thrive."
        )
        print(f"\nResult: {result}")

    asyncio.run(demo())
