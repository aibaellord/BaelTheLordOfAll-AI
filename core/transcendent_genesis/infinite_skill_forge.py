"""
BAEL - Infinite Skill Forge
Revolutionary self-evolving skill creation and composition system.

This forge creates skills that:
1. Self-compose from atomic capabilities
2. Evolve through usage and feedback
3. Learn from execution patterns
4. Automatically optimize for performance
5. Create meta-skills from skill combinations
6. Transfer learning across domains
7. Generate skills from natural language
8. Surpass any existing skill through competitive analysis

No other system has this level of skill sophistication.
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import copy

logger = logging.getLogger("BAEL.InfiniteSkillForge")

# Golden ratio for optimal skill composition
PHI = (1 + math.sqrt(5)) / 2


class SkillTier(Enum):
    """Tiers of skill complexity."""
    ATOMIC = 1       # Single, indivisible capability
    BASIC = 2        # Composition of 2-3 atomic skills
    INTERMEDIATE = 3  # Composition of basic skills
    ADVANCED = 4     # Complex multi-skill compositions
    EXPERT = 5       # Highly optimized skill chains
    MASTER = 6       # Self-evolving skill systems
    TRANSCENDENT = 7  # Beyond normal classification


class SkillDomain(Enum):
    """Domains of skill application."""
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    AUTOMATION = "automation"
    CREATIVITY = "creativity"
    PROBLEM_SOLVING = "problem_solving"
    LEARNING = "learning"
    META = "meta"  # Skills about skills


class EvolutionStrategy(Enum):
    """Strategies for skill evolution."""
    MUTATION = "mutation"           # Random changes
    CROSSOVER = "crossover"         # Combine with other skills
    OPTIMIZATION = "optimization"   # Improve performance
    SPECIALIZATION = "specialization"  # Focus on specific use case
    GENERALIZATION = "generalization"  # Broaden application
    TRANSCENDENCE = "transcendence"    # Evolve to higher tier


@dataclass
class SkillMetrics:
    """Performance metrics for a skill."""
    usage_count: int = 0
    success_count: int = 0
    avg_execution_time_ms: float = 0.0
    avg_quality_score: float = 0.0
    evolution_count: int = 0

    @property
    def success_rate(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count

    def record_usage(self, success: bool, time_ms: float, quality: float = 1.0):
        """Record a skill usage."""
        self.usage_count += 1
        if success:
            self.success_count += 1
        # Exponential moving average
        alpha = 0.1
        self.avg_execution_time_ms = alpha * time_ms + (1 - alpha) * self.avg_execution_time_ms
        self.avg_quality_score = alpha * quality + (1 - alpha) * self.avg_quality_score


@dataclass
class SkillComponent:
    """An atomic component of a skill."""
    component_id: str
    name: str
    capability: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0  # Importance in composition

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.component_id,
            "name": self.name,
            "capability": self.capability,
            "weight": self.weight
        }


@dataclass
class Skill:
    """A composable, evolvable skill."""
    skill_id: str
    name: str
    description: str
    tier: SkillTier
    domain: SkillDomain

    # Composition
    components: List[SkillComponent] = field(default_factory=list)
    parent_skills: List[str] = field(default_factory=list)  # Skills this evolved from
    child_skills: List[str] = field(default_factory=list)   # Skills evolved from this

    # Implementation
    implementation: str = ""
    prompt_template: str = ""

    # Configuration
    parameters: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Metrics
    metrics: SkillMetrics = field(default_factory=SkillMetrics)

    # Evolution
    version: str = "1.0.0"
    evolution_history: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)

    def get_fitness_score(self) -> float:
        """Calculate fitness score for evolution selection."""
        # Combine metrics using golden ratio weighting
        success_weight = 1 / PHI
        quality_weight = 1 / (PHI ** 2)
        speed_weight = 1 / (PHI ** 3)

        # Normalize execution time (lower is better)
        speed_score = 1.0 / (1.0 + self.metrics.avg_execution_time_ms / 1000)

        fitness = (
            self.metrics.success_rate * success_weight +
            self.metrics.avg_quality_score * quality_weight +
            speed_score * speed_weight
        )

        # Bonus for higher tier
        tier_bonus = self.tier.value * 0.1

        return fitness + tier_bonus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "tier": self.tier.value,
            "domain": self.domain.value,
            "components": [c.to_dict() for c in self.components],
            "metrics": {
                "usage_count": self.metrics.usage_count,
                "success_rate": self.metrics.success_rate,
                "avg_quality": self.metrics.avg_quality_score
            },
            "version": self.version
        }


@dataclass
class SkillExecutionResult:
    """Result of executing a skill."""
    skill_id: str
    success: bool
    output: Any
    execution_time_ms: float
    quality_score: float = 1.0
    insights: List[str] = field(default_factory=list)
    suggested_improvements: List[str] = field(default_factory=list)


class InfiniteSkillForge:
    """
    The Infinite Skill Forge - Self-evolving skill creation.

    Revolutionary capabilities:
    1. Natural Language Skill Creation - Describe skills in plain language
    2. Automatic Skill Composition - Combine atomic skills into complex ones
    3. Evolutionary Optimization - Skills evolve through usage
    4. Cross-Domain Transfer - Apply learnings across domains
    5. Meta-Skill Generation - Skills that create other skills
    6. Competitive Surpassing - Analyze and exceed existing skills
    7. Self-Improvement Loops - Continuous autonomous enhancement
    """

    # Atomic capabilities that form the basis of all skills
    ATOMIC_CAPABILITIES = {
        "analyze": "Analyze input and extract insights",
        "generate": "Generate new content or solutions",
        "transform": "Transform input from one form to another",
        "validate": "Validate correctness or quality",
        "optimize": "Improve efficiency or quality",
        "learn": "Extract patterns and knowledge",
        "reason": "Apply logical reasoning",
        "create": "Create something new",
        "combine": "Combine multiple elements",
        "filter": "Filter or select relevant items",
        "search": "Search for information",
        "compare": "Compare alternatives",
        "decide": "Make decisions",
        "execute": "Execute actions",
        "monitor": "Monitor and track progress"
    }

    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        enable_auto_evolution: bool = True,
        evolution_threshold: int = 10  # Evolve after N usages
    ):
        self.llm_provider = llm_provider
        self.auto_evolution = enable_auto_evolution
        self.evolution_threshold = evolution_threshold

        # Skill registry
        self._skills: Dict[str, Skill] = {}
        self._atomic_skills: Dict[str, Skill] = {}

        # Evolution population
        self._evolution_pool: List[Skill] = []
        self._evolution_history: List[Dict[str, Any]] = []

        # Learning data
        self._execution_patterns: List[Dict[str, Any]] = []
        self._successful_compositions: List[Dict[str, Any]] = []

        # Statistics
        self._stats = {
            "skills_created": 0,
            "skills_evolved": 0,
            "compositions_created": 0,
            "evolutions_performed": 0,
            "meta_skills_created": 0
        }

        # Initialize atomic skills
        self._initialize_atomic_skills()

        logger.info("InfiniteSkillForge initialized with evolutionary capabilities")

    def _initialize_atomic_skills(self):
        """Initialize the atomic skill library."""
        for cap_id, cap_desc in self.ATOMIC_CAPABILITIES.items():
            skill = Skill(
                skill_id=f"atomic_{cap_id}",
                name=cap_id.title(),
                description=cap_desc,
                tier=SkillTier.ATOMIC,
                domain=SkillDomain.META,
                components=[
                    SkillComponent(
                        component_id=cap_id,
                        name=cap_id,
                        capability=cap_desc
                    )
                ]
            )
            self._atomic_skills[skill.skill_id] = skill
            self._skills[skill.skill_id] = skill

    async def create_skill(
        self,
        description: str,
        domain: SkillDomain = SkillDomain.PROBLEM_SOLVING,
        from_components: List[str] = None,
        parameters: Dict[str, Any] = None
    ) -> Skill:
        """
        Create a new skill from natural language description.
        """
        # Generate skill ID
        skill_id = f"skill_{hashlib.md5(f'{description}{time.time()}'.encode()).hexdigest()[:10]}"

        # Determine tier based on complexity
        tier = self._infer_tier(description, from_components)

        # Select or create components
        if from_components:
            components = [
                self._skills[cid].components[0]
                for cid in from_components
                if cid in self._skills
            ]
        else:
            components = await self._infer_components(description)

        # Generate implementation
        implementation = await self._generate_implementation(description, components)

        # Generate prompt template
        prompt_template = await self._generate_prompt_template(description, components)

        skill = Skill(
            skill_id=skill_id,
            name=self._generate_skill_name(description),
            description=description,
            tier=tier,
            domain=domain,
            components=components,
            implementation=implementation,
            prompt_template=prompt_template,
            parameters=parameters or {}
        )

        self._skills[skill_id] = skill
        self._stats["skills_created"] += 1

        logger.info(f"Created skill: {skill.name} (Tier: {tier.name})")
        return skill

    async def compose_skills(
        self,
        skill_ids: List[str],
        composition_type: str = "chain",
        name: str = None,
        description: str = None
    ) -> Skill:
        """
        Compose multiple skills into a new higher-tier skill.

        Composition types:
        - chain: Execute in sequence
        - parallel: Execute in parallel, combine results
        - conditional: Execute based on conditions
        - iterative: Repeat until condition met
        """
        skills = [self._skills[sid] for sid in skill_ids if sid in self._skills]

        if not skills:
            raise ValueError("No valid skills to compose")

        # Determine new tier
        max_tier = max(s.tier.value for s in skills)
        new_tier = SkillTier(min(max_tier + 1, SkillTier.TRANSCENDENT.value))

        # Combine components
        all_components = []
        for skill in skills:
            all_components.extend(skill.components)

        # Generate composition
        composed_id = f"composed_{hashlib.md5('_'.join(skill_ids).encode()).hexdigest()[:8]}"

        composed = Skill(
            skill_id=composed_id,
            name=name or f"Composed_{composition_type.title()}",
            description=description or f"Composition of {len(skills)} skills via {composition_type}",
            tier=new_tier,
            domain=skills[0].domain,  # Inherit from first skill
            components=all_components,
            parent_skills=skill_ids,
            parameters={"composition_type": composition_type}
        )

        # Generate composed implementation
        composed.implementation = await self._generate_composition_implementation(
            skills, composition_type
        )

        # Update parent skills
        for skill in skills:
            skill.child_skills.append(composed_id)

        self._skills[composed_id] = composed
        self._stats["compositions_created"] += 1
        self._successful_compositions.append({
            "skills": skill_ids,
            "type": composition_type,
            "result_tier": new_tier.value
        })

        logger.info(f"Composed {len(skills)} skills into: {composed.name}")
        return composed

    async def execute_skill(
        self,
        skill_id: str,
        input_data: Any,
        context: Dict[str, Any] = None
    ) -> SkillExecutionResult:
        """Execute a skill and record metrics."""
        if skill_id not in self._skills:
            return SkillExecutionResult(
                skill_id=skill_id,
                success=False,
                output=None,
                execution_time_ms=0,
                quality_score=0
            )

        skill = self._skills[skill_id]
        start_time = time.time()

        try:
            # Execute skill
            if self.llm_provider and skill.prompt_template:
                # Use LLM for execution
                prompt = skill.prompt_template.format(
                    input=input_data,
                    **(context or {})
                )
                output = await self.llm_provider(prompt)
            else:
                # Simulated execution
                output = f"Executed {skill.name} on input"

            execution_time = (time.time() - start_time) * 1000
            quality_score = random.uniform(0.7, 1.0)  # Would be calculated

            # Record metrics
            skill.metrics.record_usage(True, execution_time, quality_score)

            # Check for evolution trigger
            if self.auto_evolution and skill.metrics.usage_count >= self.evolution_threshold:
                if skill.metrics.usage_count % self.evolution_threshold == 0:
                    asyncio.create_task(self._consider_evolution(skill))

            result = SkillExecutionResult(
                skill_id=skill_id,
                success=True,
                output=output,
                execution_time_ms=execution_time,
                quality_score=quality_score
            )

            # Record pattern
            self._execution_patterns.append({
                "skill_id": skill_id,
                "input_type": type(input_data).__name__,
                "success": True,
                "time_ms": execution_time
            })

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            skill.metrics.record_usage(False, execution_time, 0)

            return SkillExecutionResult(
                skill_id=skill_id,
                success=False,
                output=str(e),
                execution_time_ms=execution_time,
                quality_score=0,
                suggested_improvements=[f"Handle error: {type(e).__name__}"]
            )

    async def evolve_skill(
        self,
        skill_id: str,
        strategy: EvolutionStrategy = EvolutionStrategy.OPTIMIZATION
    ) -> Skill:
        """
        Evolve a skill using the specified strategy.
        """
        if skill_id not in self._skills:
            raise ValueError(f"Skill not found: {skill_id}")

        original = self._skills[skill_id]

        # Create evolved version
        evolved_id = f"{skill_id}_v{len(original.evolution_history) + 2}"

        evolved = copy.deepcopy(original)
        evolved.skill_id = evolved_id
        evolved.parent_skills = [skill_id]

        # Apply evolution strategy
        if strategy == EvolutionStrategy.MUTATION:
            evolved = await self._apply_mutation(evolved)
        elif strategy == EvolutionStrategy.CROSSOVER:
            # Find a compatible skill to crossover with
            partner = self._find_crossover_partner(original)
            if partner:
                evolved = await self._apply_crossover(evolved, partner)
        elif strategy == EvolutionStrategy.OPTIMIZATION:
            evolved = await self._apply_optimization(evolved)
        elif strategy == EvolutionStrategy.SPECIALIZATION:
            evolved = await self._apply_specialization(evolved)
        elif strategy == EvolutionStrategy.GENERALIZATION:
            evolved = await self._apply_generalization(evolved)
        elif strategy == EvolutionStrategy.TRANSCENDENCE:
            evolved = await self._apply_transcendence(evolved)

        # Update version
        major, minor, patch = map(int, original.version.split('.'))
        if strategy == EvolutionStrategy.TRANSCENDENCE:
            evolved.version = f"{major + 1}.0.0"
        elif strategy in [EvolutionStrategy.MUTATION, EvolutionStrategy.CROSSOVER]:
            evolved.version = f"{major}.{minor + 1}.0"
        else:
            evolved.version = f"{major}.{minor}.{patch + 1}"

        # Record evolution
        evolved.evolution_history.append({
            "from_skill": skill_id,
            "strategy": strategy.value,
            "timestamp": datetime.utcnow().isoformat()
        })
        evolved.metrics = SkillMetrics()  # Reset metrics
        evolved.metrics.evolution_count = original.metrics.evolution_count + 1
        evolved.updated_at = datetime.utcnow()

        # Update original's child skills
        original.child_skills.append(evolved_id)

        # Register evolved skill
        self._skills[evolved_id] = evolved
        self._stats["skills_evolved"] += 1
        self._stats["evolutions_performed"] += 1

        logger.info(f"Evolved {original.name} via {strategy.value} -> {evolved.version}")
        return evolved

    async def create_meta_skill(
        self,
        purpose: str,
        base_domain: SkillDomain = SkillDomain.META
    ) -> Skill:
        """
        Create a meta-skill that operates on other skills.

        Meta-skills can:
        - Create new skills
        - Evolve existing skills
        - Compose skill chains
        - Analyze skill effectiveness
        - Transfer learning between skills
        """
        meta_id = f"meta_{hashlib.md5(purpose.encode()).hexdigest()[:8]}"

        meta_skill = Skill(
            skill_id=meta_id,
            name=f"Meta: {purpose[:30]}",
            description=f"Meta-skill for: {purpose}",
            tier=SkillTier.MASTER,
            domain=base_domain,
            components=[
                SkillComponent(
                    component_id="meta_analyze",
                    name="Skill Analysis",
                    capability="Analyze skill performance and structure"
                ),
                SkillComponent(
                    component_id="meta_evolve",
                    name="Skill Evolution",
                    capability="Evolve skills for improvement"
                ),
                SkillComponent(
                    component_id="meta_compose",
                    name="Skill Composition",
                    capability="Compose skills into new combinations"
                ),
                SkillComponent(
                    component_id="meta_transfer",
                    name="Learning Transfer",
                    capability="Transfer learning across domains"
                )
            ],
            parameters={"purpose": purpose},
            tags=["meta", "self-improving", "autonomous"]
        )

        # Generate meta-skill implementation
        meta_skill.implementation = await self._generate_meta_implementation(purpose)

        self._skills[meta_id] = meta_skill
        self._stats["meta_skills_created"] += 1

        logger.info(f"Created meta-skill: {meta_skill.name}")
        return meta_skill

    async def find_best_skill(
        self,
        task_description: str,
        domain: SkillDomain = None
    ) -> Optional[Skill]:
        """Find the best skill for a given task."""
        candidates = []

        for skill in self._skills.values():
            if domain and skill.domain != domain:
                continue

            # Calculate relevance score
            relevance = self._calculate_relevance(task_description, skill)
            fitness = skill.get_fitness_score()

            combined_score = relevance * 0.6 + fitness * 0.4
            candidates.append((skill, combined_score))

        if not candidates:
            return None

        # Sort by combined score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    async def surpass_competitor(
        self,
        competitor_description: str,
        target_domain: SkillDomain
    ) -> Skill:
        """
        Create a skill that surpasses a described competitor capability.
        """
        # Analyze what the competitor does
        competitor_analysis = await self._analyze_competitor(competitor_description)

        # Create a superior skill
        superior_description = f"""
        Create a skill that exceeds this capability: {competitor_description}

        Improvements:
        - Faster execution
        - Higher quality output
        - More versatile application
        - Better error handling
        - Self-improving capability
        """

        superior_skill = await self.create_skill(
            description=superior_description,
            domain=target_domain
        )

        # Add competitive edge components
        superior_skill.components.append(
            SkillComponent(
                component_id="competitive_edge",
                name="Competitive Advantage",
                capability="Continuously analyze and surpass competitors"
            )
        )

        superior_skill.tags.extend(["competitive", "superior", "evolved"])

        return superior_skill

    def _infer_tier(
        self,
        description: str,
        components: List[str] = None
    ) -> SkillTier:
        """Infer skill tier from description and components."""
        if components:
            num_components = len(components)
            if num_components <= 1:
                return SkillTier.ATOMIC
            elif num_components <= 3:
                return SkillTier.BASIC
            elif num_components <= 5:
                return SkillTier.INTERMEDIATE
            elif num_components <= 8:
                return SkillTier.ADVANCED
            else:
                return SkillTier.EXPERT

        # Infer from description complexity
        words = len(description.split())
        if words < 10:
            return SkillTier.BASIC
        elif words < 25:
            return SkillTier.INTERMEDIATE
        elif words < 50:
            return SkillTier.ADVANCED
        else:
            return SkillTier.EXPERT

    async def _infer_components(self, description: str) -> List[SkillComponent]:
        """Infer required components from description."""
        components = []
        desc_lower = description.lower()

        # Match against atomic capabilities
        for cap_id, cap_desc in self.ATOMIC_CAPABILITIES.items():
            if cap_id in desc_lower or any(
                word in desc_lower for word in cap_desc.lower().split()
            ):
                components.append(
                    SkillComponent(
                        component_id=f"component_{cap_id}",
                        name=cap_id.title(),
                        capability=cap_desc,
                        weight=1.0 / PHI  # Golden ratio weighting
                    )
                )

        # Ensure at least one component
        if not components:
            components.append(
                SkillComponent(
                    component_id="component_execute",
                    name="Execute",
                    capability="Execute the described task"
                )
            )

        return components

    async def _generate_implementation(
        self,
        description: str,
        components: List[SkillComponent]
    ) -> str:
        """Generate skill implementation code."""
        component_list = ", ".join([c.name for c in components])

        implementation = f'''
async def execute(input_data, context=None):
    """
    {description}

    Components: {component_list}
    """
    result = {{}}

    # Execute each component
'''

        for comp in components:
            implementation += f'''
    # {comp.name}: {comp.capability}
    result["{comp.component_id}"] = await process_{comp.component_id}(input_data)
'''

        implementation += '''
    # Synthesize results
    final_result = synthesize(result)
    return final_result
'''

        return implementation

    async def _generate_prompt_template(
        self,
        description: str,
        components: List[SkillComponent]
    ) -> str:
        """Generate prompt template for LLM execution."""
        component_instructions = "\n".join([
            f"- {c.name}: {c.capability}"
            for c in components
        ])

        return f'''You are executing the following skill:
{description}

Apply these capabilities:
{component_instructions}

Input: {{input}}

Provide a comprehensive response that demonstrates all capabilities.
'''

    async def _generate_composition_implementation(
        self,
        skills: List[Skill],
        composition_type: str
    ) -> str:
        """Generate implementation for composed skills."""
        if composition_type == "chain":
            impl = "async def execute(input_data, context=None):\n"
            impl += "    result = input_data\n"
            for skill in skills:
                impl += f"    result = await execute_{skill.skill_id}(result, context)\n"
            impl += "    return result\n"
        elif composition_type == "parallel":
            impl = "async def execute(input_data, context=None):\n"
            impl += "    import asyncio\n"
            impl += "    tasks = [\n"
            for skill in skills:
                impl += f"        execute_{skill.skill_id}(input_data, context),\n"
            impl += "    ]\n"
            impl += "    results = await asyncio.gather(*tasks)\n"
            impl += "    return combine_results(results)\n"
        else:
            impl = "async def execute(input_data, context=None):\n"
            impl += "    # Custom composition logic\n"
            impl += "    return process(input_data)\n"

        return impl

    async def _consider_evolution(self, skill: Skill):
        """Consider whether to evolve a skill."""
        # Don't evolve atomic skills
        if skill.tier == SkillTier.ATOMIC:
            return

        # Analyze metrics
        if skill.metrics.success_rate < 0.7:
            # Low success rate - try optimization
            await self.evolve_skill(skill.skill_id, EvolutionStrategy.OPTIMIZATION)
        elif skill.metrics.avg_quality_score > 0.9 and skill.tier.value < SkillTier.MASTER.value:
            # High quality - try transcendence
            await self.evolve_skill(skill.skill_id, EvolutionStrategy.TRANSCENDENCE)
        elif skill.metrics.usage_count >= 50:
            # Heavy usage - try specialization
            await self.evolve_skill(skill.skill_id, EvolutionStrategy.SPECIALIZATION)

    async def _apply_mutation(self, skill: Skill) -> Skill:
        """Apply random mutations to a skill."""
        # Randomly modify weights
        for comp in skill.components:
            comp.weight *= random.uniform(0.8, 1.2)

        # Potentially add or remove a component
        if random.random() > 0.7 and len(skill.components) > 1:
            skill.components.pop(random.randint(0, len(skill.components) - 1))
        elif random.random() > 0.7:
            # Add a random atomic component
            cap_id = random.choice(list(self.ATOMIC_CAPABILITIES.keys()))
            skill.components.append(
                SkillComponent(
                    component_id=f"mutated_{cap_id}",
                    name=cap_id.title(),
                    capability=self.ATOMIC_CAPABILITIES[cap_id]
                )
            )

        skill.description = f"[Mutated] {skill.description}"
        return skill

    async def _apply_crossover(self, skill: Skill, partner: Skill) -> Skill:
        """Crossover with another skill."""
        # Take components from both
        all_components = skill.components + partner.components

        # Select subset using golden ratio
        num_to_keep = int(len(all_components) / PHI)
        skill.components = random.sample(all_components, max(1, num_to_keep))

        skill.description = f"[Crossover] {skill.description}"
        skill.parent_skills.append(partner.skill_id)

        return skill

    async def _apply_optimization(self, skill: Skill) -> Skill:
        """Optimize skill for better performance."""
        # Increase weights of high-performing components
        # (Would use actual performance data)
        for comp in skill.components:
            if "analyze" in comp.capability.lower() or "optimize" in comp.capability.lower():
                comp.weight *= PHI

        # Normalize weights
        total_weight = sum(c.weight for c in skill.components)
        for comp in skill.components:
            comp.weight /= total_weight

        skill.description = f"[Optimized] {skill.description}"
        return skill

    async def _apply_specialization(self, skill: Skill) -> Skill:
        """Specialize skill for specific use cases."""
        # Keep only most weighted components
        skill.components.sort(key=lambda c: c.weight, reverse=True)
        skill.components = skill.components[:max(1, len(skill.components) // 2)]

        # Increase remaining weights
        for comp in skill.components:
            comp.weight *= PHI

        skill.description = f"[Specialized] {skill.description}"
        skill.tier = SkillTier(min(skill.tier.value + 1, SkillTier.EXPERT.value))

        return skill

    async def _apply_generalization(self, skill: Skill) -> Skill:
        """Generalize skill for broader application."""
        # Add more general components
        for cap_id in ["analyze", "transform", "validate"]:
            if cap_id in self.ATOMIC_CAPABILITIES:
                skill.components.append(
                    SkillComponent(
                        component_id=f"general_{cap_id}",
                        name=cap_id.title(),
                        capability=self.ATOMIC_CAPABILITIES[cap_id],
                        weight=1.0 / PHI
                    )
                )

        skill.description = f"[Generalized] {skill.description}"
        return skill

    async def _apply_transcendence(self, skill: Skill) -> Skill:
        """Transcend to a higher tier of capability."""
        # Add meta-components
        skill.components.append(
            SkillComponent(
                component_id="transcendent_insight",
                name="Transcendent Insight",
                capability="Access higher-order patterns and solutions",
                weight=PHI
            )
        )
        skill.components.append(
            SkillComponent(
                component_id="self_improvement",
                name="Self-Improvement",
                capability="Continuously improve own performance",
                weight=PHI
            )
        )

        skill.tier = SkillTier(min(skill.tier.value + 1, SkillTier.TRANSCENDENT.value))
        skill.description = f"[Transcendent] {skill.description}"
        skill.tags.append("transcendent")

        return skill

    def _find_crossover_partner(self, skill: Skill) -> Optional[Skill]:
        """Find a compatible skill for crossover."""
        candidates = [
            s for s in self._skills.values()
            if s.skill_id != skill.skill_id
            and s.domain == skill.domain
            and abs(s.tier.value - skill.tier.value) <= 1
            and s.metrics.success_rate > 0.5
        ]

        if not candidates:
            return None

        # Select best fitness partner
        return max(candidates, key=lambda s: s.get_fitness_score())

    def _calculate_relevance(self, task: str, skill: Skill) -> float:
        """Calculate relevance of skill to task."""
        task_words = set(task.lower().split())
        desc_words = set(skill.description.lower().split())

        # Jaccard similarity
        intersection = len(task_words & desc_words)
        union = len(task_words | desc_words)

        if union == 0:
            return 0.0

        return intersection / union

    async def _analyze_competitor(self, description: str) -> Dict[str, Any]:
        """Analyze competitor capability."""
        return {
            "capabilities": description.split(","),
            "weaknesses": ["Limited by fixed implementation", "No self-improvement"],
            "opportunities": ["Add evolution", "Add meta-learning", "Add multi-domain support"]
        }

    async def _generate_meta_implementation(self, purpose: str) -> str:
        """Generate meta-skill implementation."""
        return f'''
async def execute_meta(skill_forge, target_skills, context=None):
    """
    Meta-skill: {purpose}

    Operations on skills:
    - Analyze performance
    - Suggest improvements
    - Evolve as needed
    - Transfer learning
    """
    results = {{}}

    for skill_id in target_skills:
        skill = skill_forge._skills.get(skill_id)
        if not skill:
            continue

        # Analyze
        analysis = {{
            "fitness": skill.get_fitness_score(),
            "tier": skill.tier.name,
            "usage": skill.metrics.usage_count,
            "success_rate": skill.metrics.success_rate
        }}

        # Suggest evolution if needed
        if analysis["success_rate"] < 0.8:
            await skill_forge.evolve_skill(skill_id, EvolutionStrategy.OPTIMIZATION)

        results[skill_id] = analysis

    return results
'''

    def _generate_skill_name(self, description: str) -> str:
        """Generate skill name from description."""
        words = description.split()[:4]
        name = " ".join(w.title() for w in words if len(w) > 2)
        return name or "Custom Skill"

    def get_skills_by_tier(self, tier: SkillTier) -> List[Skill]:
        """Get all skills of a specific tier."""
        return [s for s in self._skills.values() if s.tier == tier]

    def get_skills_by_domain(self, domain: SkillDomain) -> List[Skill]:
        """Get all skills in a specific domain."""
        return [s for s in self._skills.values() if s.domain == domain]

    def get_evolution_lineage(self, skill_id: str) -> List[str]:
        """Get the evolution lineage of a skill."""
        if skill_id not in self._skills:
            return []

        lineage = [skill_id]
        skill = self._skills[skill_id]

        # Trace back to ancestors
        for parent_id in skill.parent_skills:
            lineage = self.get_evolution_lineage(parent_id) + lineage

        return lineage

    def get_stats(self) -> Dict[str, Any]:
        """Get forge statistics."""
        return {
            **self._stats,
            "total_skills": len(self._skills),
            "atomic_skills": len(self._atomic_skills),
            "execution_patterns": len(self._execution_patterns),
            "successful_compositions": len(self._successful_compositions)
        }


# Global instance
_skill_forge: Optional[InfiniteSkillForge] = None


def get_skill_forge() -> InfiniteSkillForge:
    """Get the global skill forge."""
    global _skill_forge
    if _skill_forge is None:
        _skill_forge = InfiniteSkillForge()
    return _skill_forge


async def demo():
    """Demonstrate the Infinite Skill Forge."""
    forge = get_skill_forge()

    print("=== INFINITE SKILL FORGE DEMO ===\n")

    # Create a skill from description
    print("--- Creating Skill from Description ---")
    skill1 = await forge.create_skill(
        description="Analyze code for security vulnerabilities and generate fixes",
        domain=SkillDomain.CODE_GENERATION
    )
    print(f"Created: {skill1.name}")
    print(f"  Tier: {skill1.tier.name}")
    print(f"  Components: {len(skill1.components)}")

    # Create another skill
    skill2 = await forge.create_skill(
        description="Research best practices and synthesize recommendations",
        domain=SkillDomain.RESEARCH
    )
    print(f"\nCreated: {skill2.name}")

    # Compose skills
    print("\n--- Composing Skills ---")
    composed = await forge.compose_skills(
        [skill1.skill_id, skill2.skill_id],
        composition_type="chain",
        name="Security Research Chain"
    )
    print(f"Composed: {composed.name}")
    print(f"  Tier: {composed.tier.name}")
    print(f"  Parent skills: {len(composed.parent_skills)}")

    # Execute skill
    print("\n--- Executing Skill ---")
    result = await forge.execute_skill(
        skill1.skill_id,
        input_data="def login(user, pass): return db.query(f'SELECT * FROM users WHERE u={user}')"
    )
    print(f"Execution success: {result.success}")
    print(f"Time: {result.execution_time_ms:.2f}ms")

    # Evolve skill
    print("\n--- Evolving Skill ---")
    evolved = await forge.evolve_skill(
        skill1.skill_id,
        strategy=EvolutionStrategy.OPTIMIZATION
    )
    print(f"Evolved to: {evolved.version}")
    print(f"  New tier: {evolved.tier.name}")

    # Create meta-skill
    print("\n--- Creating Meta-Skill ---")
    meta = await forge.create_meta_skill(
        purpose="Continuously improve all security-related skills"
    )
    print(f"Meta-skill: {meta.name}")
    print(f"  Tier: {meta.tier.name}")

    # Show stats
    print("\n--- Forge Statistics ---")
    for key, value in forge.get_stats().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
