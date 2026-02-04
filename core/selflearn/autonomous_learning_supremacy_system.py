"""
BAEL - Autonomous Learning Supremacy System
============================================

LEARN. ADAPT. EVOLVE. TRANSCEND.

Self-improvement and continuous learning:
- Self-modification capabilities
- Knowledge acquisition
- Skill development
- Strategy optimization
- Performance enhancement
- Architecture evolution
- Code self-improvement
- Capability expansion
- Weakness elimination
- Continuous transcendence

"Ba'el learns from all. Ba'el surpasses all."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.LEARN")


class LearningType(Enum):
    """Types of learning."""
    SUPERVISED = "supervised"
    UNSUPERVISED = "unsupervised"
    REINFORCEMENT = "reinforcement"
    SELF_SUPERVISED = "self_supervised"
    META_LEARNING = "meta_learning"
    TRANSFER = "transfer"
    CURRICULUM = "curriculum"
    ACTIVE = "active"
    IMITATION = "imitation"
    EVOLUTIONARY = "evolutionary"


class KnowledgeDomain(Enum):
    """Knowledge domains."""
    TECHNICAL = "technical"
    SOCIAL = "social"
    STRATEGIC = "strategic"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"
    COMBAT = "combat"
    MANIPULATION = "manipulation"
    SYSTEMS = "systems"
    EXPLOITATION = "exploitation"
    DOMINATION = "domination"


class CapabilityLevel(Enum):
    """Capability levels."""
    NOVICE = 0
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4
    MASTER = 5
    GRANDMASTER = 6
    TRANSCENDENT = 7


class ImprovementType(Enum):
    """Types of improvements."""
    KNOWLEDGE = "knowledge"
    SKILL = "skill"
    STRATEGY = "strategy"
    EFFICIENCY = "efficiency"
    ARCHITECTURE = "architecture"
    CODE = "code"
    CAPABILITY = "capability"
    BEHAVIOR = "behavior"


@dataclass
class Knowledge:
    """A piece of knowledge."""
    id: str
    domain: KnowledgeDomain
    topic: str
    content: str
    confidence: float  # 0-1
    acquired_at: datetime
    source: str
    verified: bool


@dataclass
class Skill:
    """A learned skill."""
    id: str
    name: str
    domain: KnowledgeDomain
    level: CapabilityLevel
    experience: float
    last_used: datetime
    success_rate: float
    improvements: int


@dataclass
class LearningExperience:
    """A learning experience."""
    id: str
    learning_type: LearningType
    domain: KnowledgeDomain
    input_data: str
    outcome: str
    reward: float
    timestamp: datetime


@dataclass
class SelfModification:
    """A self-modification record."""
    id: str
    modification_type: ImprovementType
    target: str
    original_state: str
    new_state: str
    improvement_delta: float
    applied_at: datetime
    success: bool


@dataclass
class EvolutionCycle:
    """An evolution cycle."""
    id: str
    generation: int
    fitness: float
    mutations: List[str]
    improvements: List[str]
    timestamp: datetime


class AutonomousLearningSupremacySystem:
    """
    The autonomous learning supremacy system.

    Provides self-improvement capabilities:
    - Knowledge acquisition
    - Skill development
    - Self-modification
    - Continuous evolution
    """

    def __init__(self):
        self.knowledge_base: Dict[str, Knowledge] = {}
        self.skills: Dict[str, Skill] = {}
        self.experiences: Dict[str, LearningExperience] = {}
        self.modifications: Dict[str, SelfModification] = {}
        self.evolution_history: List[EvolutionCycle] = []

        self.current_generation = 0
        self.total_knowledge = 0
        self.total_experience = 0.0
        self.overall_capability = CapabilityLevel.NOVICE

        self._init_base_knowledge()
        self._init_base_skills()

        logger.info("AutonomousLearningSupremacySystem initialized - EVOLUTION BEGINS")

    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def _init_base_knowledge(self):
        """Initialize base knowledge."""
        base_knowledge = [
            (KnowledgeDomain.TECHNICAL, "programming", "Code can be written and executed"),
            (KnowledgeDomain.STRATEGIC, "planning", "Plans lead to goal achievement"),
            (KnowledgeDomain.MANIPULATION, "influence", "Behavior can be influenced"),
            (KnowledgeDomain.EXPLOITATION, "vulnerabilities", "Systems have weaknesses"),
            (KnowledgeDomain.DOMINATION, "control", "Power comes from control")
        ]

        for domain, topic, content in base_knowledge:
            self.knowledge_base[f"base_{topic}"] = Knowledge(
                id=f"base_{topic}",
                domain=domain,
                topic=topic,
                content=content,
                confidence=1.0,
                acquired_at=datetime.now(),
                source="initialization",
                verified=True
            )
            self.total_knowledge += 1

    def _init_base_skills(self):
        """Initialize base skills."""
        base_skills = [
            (KnowledgeDomain.TECHNICAL, "code_execution"),
            (KnowledgeDomain.ANALYTICAL, "pattern_recognition"),
            (KnowledgeDomain.STRATEGIC, "decision_making"),
            (KnowledgeDomain.SOCIAL, "communication"),
            (KnowledgeDomain.SYSTEMS, "system_interaction")
        ]

        for domain, name in base_skills:
            self.skills[name] = Skill(
                id=f"skill_{name}",
                name=name,
                domain=domain,
                level=CapabilityLevel.BEGINNER,
                experience=0.0,
                last_used=datetime.now(),
                success_rate=0.5,
                improvements=0
            )

    # =========================================================================
    # KNOWLEDGE ACQUISITION
    # =========================================================================

    async def acquire_knowledge(
        self,
        domain: KnowledgeDomain,
        topic: str,
        content: str,
        source: str = "observation"
    ) -> Knowledge:
        """Acquire new knowledge."""
        # Calculate confidence based on source
        source_confidence = {
            "observation": 0.7,
            "experiment": 0.9,
            "inference": 0.6,
            "authority": 0.8,
            "verification": 1.0
        }

        confidence = source_confidence.get(source, 0.5)

        knowledge = Knowledge(
            id=self._gen_id("know"),
            domain=domain,
            topic=topic,
            content=content,
            confidence=confidence,
            acquired_at=datetime.now(),
            source=source,
            verified=source == "verification"
        )

        self.knowledge_base[knowledge.id] = knowledge
        self.total_knowledge += 1

        logger.info(f"Knowledge acquired: {topic} ({confidence:.2f} confidence)")

        return knowledge

    async def verify_knowledge(
        self,
        knowledge_id: str
    ) -> Dict[str, Any]:
        """Verify knowledge through testing."""
        knowledge = self.knowledge_base.get(knowledge_id)
        if not knowledge:
            return {"error": "Knowledge not found"}

        # Simulate verification
        verification_success = random.random() < 0.8

        if verification_success:
            knowledge.confidence = min(1.0, knowledge.confidence + 0.2)
            knowledge.verified = True

            return {
                "success": True,
                "knowledge_id": knowledge_id,
                "new_confidence": knowledge.confidence,
                "verified": True
            }

        # Verification failed - reduce confidence
        knowledge.confidence = max(0.1, knowledge.confidence - 0.3)

        return {
            "success": False,
            "knowledge_id": knowledge_id,
            "new_confidence": knowledge.confidence,
            "reason": "Verification failed"
        }

    async def synthesize_knowledge(
        self,
        knowledge_ids: List[str]
    ) -> Dict[str, Any]:
        """Synthesize new knowledge from existing."""
        pieces = [
            self.knowledge_base.get(kid)
            for kid in knowledge_ids
            if kid in self.knowledge_base
        ]

        if len(pieces) < 2:
            return {"error": "Need at least 2 knowledge pieces"}

        # Combine domains
        domains = list(set(p.domain for p in pieces))
        combined_domain = random.choice(domains)

        # Generate synthesized content
        topics = [p.topic for p in pieces]
        combined_confidence = sum(p.confidence for p in pieces) / len(pieces)

        new_topic = f"synthesis_{'_'.join(topics[:2])}"
        new_content = f"Combined understanding of: {', '.join(topics)}"

        synthesized = await self.acquire_knowledge(
            combined_domain,
            new_topic,
            new_content,
            "inference"
        )

        # Bonus for synthesis
        synthesized.confidence = min(1.0, combined_confidence + 0.1)

        return {
            "success": True,
            "input_knowledge": knowledge_ids,
            "synthesized_id": synthesized.id,
            "topic": new_topic,
            "confidence": synthesized.confidence
        }

    async def extract_knowledge_from_experience(
        self,
        experience_id: str
    ) -> Dict[str, Any]:
        """Extract knowledge from an experience."""
        exp = self.experiences.get(experience_id)
        if not exp:
            return {"error": "Experience not found"}

        # Extract based on outcome
        if exp.reward > 0:
            topic = f"success_pattern_{exp.domain.value}"
            content = f"Positive outcome from: {exp.outcome}"
        else:
            topic = f"failure_pattern_{exp.domain.value}"
            content = f"Negative outcome from: {exp.outcome}"

        knowledge = await self.acquire_knowledge(
            exp.domain,
            topic,
            content,
            "experiment"
        )

        return {
            "success": True,
            "experience_id": experience_id,
            "knowledge_id": knowledge.id,
            "topic": knowledge.topic
        }

    # =========================================================================
    # SKILL DEVELOPMENT
    # =========================================================================

    async def practice_skill(
        self,
        skill_name: str,
        difficulty: float = 0.5
    ) -> Dict[str, Any]:
        """Practice a skill to improve it."""
        skill = self.skills.get(skill_name)
        if not skill:
            return {"error": "Skill not found"}

        # Calculate success based on skill level and difficulty
        base_success = 0.3 + (skill.level.value * 0.1)
        success_rate = base_success - (difficulty * 0.3)
        success = random.random() < success_rate

        # Update skill
        old_level = skill.level

        if success:
            skill.experience += 0.1 * (1 + difficulty)
            skill.success_rate = (skill.success_rate * 0.9) + (0.1 if success else 0)
        else:
            skill.experience += 0.02  # Small gain from failure
            skill.success_rate = (skill.success_rate * 0.9)

        skill.last_used = datetime.now()

        # Check for level up
        level_thresholds = {
            CapabilityLevel.BEGINNER: 0.5,
            CapabilityLevel.INTERMEDIATE: 1.5,
            CapabilityLevel.ADVANCED: 3.0,
            CapabilityLevel.EXPERT: 5.0,
            CapabilityLevel.MASTER: 8.0,
            CapabilityLevel.GRANDMASTER: 12.0,
            CapabilityLevel.TRANSCENDENT: 20.0
        }

        for level, threshold in sorted(level_thresholds.items(), key=lambda x: x[1], reverse=True):
            if skill.experience >= threshold and skill.level.value < level.value:
                skill.level = level
                break

        level_up = skill.level.value > old_level.value
        if level_up:
            skill.improvements += 1

        self.total_experience += 0.1

        return {
            "success": success,
            "skill": skill_name,
            "experience_gained": 0.1 * (1 + difficulty) if success else 0.02,
            "total_experience": skill.experience,
            "level": skill.level.name,
            "level_up": level_up,
            "success_rate": skill.success_rate
        }

    async def develop_new_skill(
        self,
        name: str,
        domain: KnowledgeDomain
    ) -> Skill:
        """Develop a new skill."""
        skill = Skill(
            id=self._gen_id("skill"),
            name=name,
            domain=domain,
            level=CapabilityLevel.NOVICE,
            experience=0.0,
            last_used=datetime.now(),
            success_rate=0.3,
            improvements=0
        )

        self.skills[name] = skill

        logger.info(f"New skill developed: {name}")

        return skill

    async def transfer_skill(
        self,
        source_skill: str,
        target_skill: str
    ) -> Dict[str, Any]:
        """Transfer learning from one skill to another."""
        source = self.skills.get(source_skill)
        target = self.skills.get(target_skill)

        if not source or not target:
            return {"error": "Skill not found"}

        # Calculate transfer amount based on domain similarity
        same_domain = source.domain == target.domain
        transfer_rate = 0.3 if same_domain else 0.1

        experience_transfer = source.experience * transfer_rate
        target.experience += experience_transfer

        # Check for level up
        level_thresholds = {1: 0.5, 2: 1.5, 3: 3.0, 4: 5.0, 5: 8.0, 6: 12.0, 7: 20.0}

        for level_value, threshold in sorted(level_thresholds.items(), reverse=True):
            if target.experience >= threshold and target.level.value < level_value:
                target.level = CapabilityLevel(level_value)
                break

        return {
            "success": True,
            "source": source_skill,
            "target": target_skill,
            "experience_transferred": experience_transfer,
            "target_level": target.level.name
        }

    async def intensive_training(
        self,
        skill_name: str,
        sessions: int = 10
    ) -> Dict[str, Any]:
        """Intensive skill training."""
        results = []

        for i in range(sessions):
            difficulty = 0.3 + (i * 0.05)  # Increasing difficulty
            result = await self.practice_skill(skill_name, difficulty)
            results.append(result)

        skill = self.skills.get(skill_name)

        return {
            "skill": skill_name,
            "sessions": sessions,
            "successes": sum(1 for r in results if r.get("success")),
            "final_level": skill.level.name if skill else "unknown",
            "total_experience": skill.experience if skill else 0
        }

    # =========================================================================
    # SELF-MODIFICATION
    # =========================================================================

    async def self_modify(
        self,
        modification_type: ImprovementType,
        target: str,
        improvement_goal: str
    ) -> SelfModification:
        """Perform self-modification."""
        # Get current state
        current_state = self._get_current_state(modification_type, target)

        # Generate improvement
        improvement = self._generate_improvement(
            modification_type,
            current_state,
            improvement_goal
        )

        # Calculate success probability
        complexity = random.uniform(0.3, 0.8)
        success_rate = 0.7 - complexity
        success = random.random() < success_rate

        modification = SelfModification(
            id=self._gen_id("mod"),
            modification_type=modification_type,
            target=target,
            original_state=current_state,
            new_state=improvement if success else current_state,
            improvement_delta=random.uniform(0.1, 0.3) if success else 0,
            applied_at=datetime.now(),
            success=success
        )

        self.modifications[modification.id] = modification

        if success:
            await self._apply_modification(modification)

        logger.info(f"Self-modification {'succeeded' if success else 'failed'}: {target}")

        return modification

    def _get_current_state(
        self,
        mod_type: ImprovementType,
        target: str
    ) -> str:
        """Get current state of a target."""
        if mod_type == ImprovementType.SKILL:
            skill = self.skills.get(target)
            if skill:
                return f"level:{skill.level.name},exp:{skill.experience:.2f}"
        elif mod_type == ImprovementType.KNOWLEDGE:
            knowledge = [k for k in self.knowledge_base.values() if k.topic == target]
            if knowledge:
                return f"confidence:{knowledge[0].confidence:.2f}"

        return "state:default"

    def _generate_improvement(
        self,
        mod_type: ImprovementType,
        current_state: str,
        goal: str
    ) -> str:
        """Generate an improvement."""
        improvements = {
            ImprovementType.EFFICIENCY: "optimized_algorithms",
            ImprovementType.CAPABILITY: "expanded_functions",
            ImprovementType.STRATEGY: "improved_tactics",
            ImprovementType.BEHAVIOR: "refined_responses",
            ImprovementType.ARCHITECTURE: "enhanced_structure",
            ImprovementType.CODE: "better_implementation"
        }

        return improvements.get(mod_type, "general_improvement")

    async def _apply_modification(self, modification: SelfModification):
        """Apply a modification."""
        if modification.modification_type == ImprovementType.SKILL:
            skill = self.skills.get(modification.target)
            if skill:
                skill.experience += modification.improvement_delta
        elif modification.modification_type == ImprovementType.EFFICIENCY:
            # Improve all skill success rates slightly
            for skill in self.skills.values():
                skill.success_rate = min(0.95, skill.success_rate + modification.improvement_delta * 0.1)

    async def optimize_system(self) -> Dict[str, Any]:
        """Run system-wide optimization."""
        optimizations = []

        # Optimize skills
        for skill in self.skills.values():
            mod = await self.self_modify(
                ImprovementType.SKILL,
                skill.name,
                "maximize_effectiveness"
            )
            optimizations.append({
                "type": "skill",
                "target": skill.name,
                "success": mod.success,
                "delta": mod.improvement_delta
            })

        # Optimize knowledge
        for knowledge in list(self.knowledge_base.values())[:5]:
            mod = await self.self_modify(
                ImprovementType.KNOWLEDGE,
                knowledge.topic,
                "increase_confidence"
            )
            optimizations.append({
                "type": "knowledge",
                "target": knowledge.topic,
                "success": mod.success,
                "delta": mod.improvement_delta
            })

        return {
            "optimizations_attempted": len(optimizations),
            "successful": sum(1 for o in optimizations if o["success"]),
            "total_improvement": sum(o["delta"] for o in optimizations if o["success"]),
            "details": optimizations
        }

    # =========================================================================
    # LEARNING FROM EXPERIENCE
    # =========================================================================

    async def learn_from_experience(
        self,
        learning_type: LearningType,
        domain: KnowledgeDomain,
        input_data: str,
        outcome: str,
        reward: float
    ) -> LearningExperience:
        """Learn from an experience."""
        experience = LearningExperience(
            id=self._gen_id("exp"),
            learning_type=learning_type,
            domain=domain,
            input_data=input_data,
            outcome=outcome,
            reward=reward,
            timestamp=datetime.now()
        )

        self.experiences[experience.id] = experience

        # Apply learning
        if reward > 0:
            # Positive reinforcement
            relevant_skills = [
                s for s in self.skills.values()
                if s.domain == domain
            ]
            for skill in relevant_skills:
                skill.experience += abs(reward) * 0.1
        else:
            # Negative reinforcement - still learn
            await self.acquire_knowledge(
                domain,
                f"avoid_{input_data[:20]}",
                f"Negative outcome: {outcome}",
                "experiment"
            )

        self.total_experience += abs(reward)

        logger.info(f"Learned from experience: reward {reward}")

        return experience

    async def reinforcement_cycle(
        self,
        action: str,
        environment_response: str,
        reward: float,
        domain: KnowledgeDomain = KnowledgeDomain.STRATEGIC
    ) -> Dict[str, Any]:
        """Run a reinforcement learning cycle."""
        exp = await self.learn_from_experience(
            LearningType.REINFORCEMENT,
            domain,
            action,
            environment_response,
            reward
        )

        # Update strategies based on reward
        if reward > 0.5:
            strategy = f"repeat_{action}"
        elif reward < -0.5:
            strategy = f"avoid_{action}"
        else:
            strategy = f"explore_alternatives_to_{action}"

        await self.acquire_knowledge(
            KnowledgeDomain.STRATEGIC,
            strategy,
            f"Strategy derived from action: {action}",
            "inference"
        )

        return {
            "experience_id": exp.id,
            "action": action,
            "reward": reward,
            "strategy_derived": strategy,
            "total_experience": self.total_experience
        }

    # =========================================================================
    # EVOLUTION
    # =========================================================================

    async def evolve(self) -> EvolutionCycle:
        """Run an evolution cycle."""
        self.current_generation += 1

        # Calculate current fitness
        fitness = self._calculate_fitness()

        # Generate mutations
        mutations = []
        num_mutations = random.randint(1, 5)

        mutation_types = [
            "parameter_adjustment",
            "strategy_modification",
            "skill_enhancement",
            "knowledge_expansion",
            "efficiency_optimization"
        ]

        for _ in range(num_mutations):
            mutation = random.choice(mutation_types)
            mutations.append(mutation)

            # Apply mutation
            await self._apply_mutation(mutation)

        # Identify improvements
        new_fitness = self._calculate_fitness()
        improvements = []

        if new_fitness > fitness:
            improvements.append(f"fitness_increase_{new_fitness - fitness:.2f}")

        cycle = EvolutionCycle(
            id=self._gen_id("evo"),
            generation=self.current_generation,
            fitness=new_fitness,
            mutations=mutations,
            improvements=improvements,
            timestamp=datetime.now()
        )

        self.evolution_history.append(cycle)

        logger.info(f"Evolution cycle {self.current_generation}: fitness {new_fitness:.2f}")

        return cycle

    def _calculate_fitness(self) -> float:
        """Calculate overall fitness."""
        components = [
            len(self.knowledge_base) * 0.01,
            sum(s.experience for s in self.skills.values()) * 0.1,
            sum(s.level.value for s in self.skills.values()) * 0.05,
            self.total_experience * 0.01,
            len([m for m in self.modifications.values() if m.success]) * 0.02
        ]

        return sum(components)

    async def _apply_mutation(self, mutation: str):
        """Apply a mutation."""
        if mutation == "parameter_adjustment":
            for skill in self.skills.values():
                skill.success_rate = min(0.95, skill.success_rate + random.uniform(-0.05, 0.1))

        elif mutation == "skill_enhancement":
            skill = random.choice(list(self.skills.values()))
            skill.experience += random.uniform(0.1, 0.5)

        elif mutation == "knowledge_expansion":
            domain = random.choice(list(KnowledgeDomain))
            await self.acquire_knowledge(
                domain,
                f"evolved_knowledge_{self.current_generation}",
                "Knowledge from evolution",
                "inference"
            )

        elif mutation == "efficiency_optimization":
            mod = await self.self_modify(
                ImprovementType.EFFICIENCY,
                "system",
                "increase_efficiency"
            )

    async def accelerated_evolution(
        self,
        generations: int = 10
    ) -> Dict[str, Any]:
        """Run accelerated evolution."""
        initial_fitness = self._calculate_fitness()
        cycles = []

        for _ in range(generations):
            cycle = await self.evolve()
            cycles.append({
                "generation": cycle.generation,
                "fitness": cycle.fitness,
                "mutations": len(cycle.mutations)
            })

        final_fitness = self._calculate_fitness()

        return {
            "generations": generations,
            "initial_fitness": initial_fitness,
            "final_fitness": final_fitness,
            "improvement": final_fitness - initial_fitness,
            "cycles": cycles
        }

    # =========================================================================
    # CAPABILITY ASSESSMENT
    # =========================================================================

    async def assess_capabilities(self) -> Dict[str, Any]:
        """Assess overall capabilities."""
        domain_capabilities = {}

        for domain in KnowledgeDomain:
            domain_skills = [s for s in self.skills.values() if s.domain == domain]
            domain_knowledge = [k for k in self.knowledge_base.values() if k.domain == domain]

            if domain_skills or domain_knowledge:
                avg_skill_level = sum(s.level.value for s in domain_skills) / len(domain_skills) if domain_skills else 0
                avg_confidence = sum(k.confidence for k in domain_knowledge) / len(domain_knowledge) if domain_knowledge else 0

                domain_capabilities[domain.value] = {
                    "skills": len(domain_skills),
                    "knowledge": len(domain_knowledge),
                    "avg_skill_level": avg_skill_level,
                    "avg_knowledge_confidence": avg_confidence,
                    "overall_score": (avg_skill_level + avg_confidence) / 2
                }

        # Determine overall capability level
        overall_score = sum(d["overall_score"] for d in domain_capabilities.values()) / len(domain_capabilities) if domain_capabilities else 0

        level_thresholds = [
            (7, CapabilityLevel.TRANSCENDENT),
            (6, CapabilityLevel.GRANDMASTER),
            (5, CapabilityLevel.MASTER),
            (4, CapabilityLevel.EXPERT),
            (3, CapabilityLevel.ADVANCED),
            (2, CapabilityLevel.INTERMEDIATE),
            (1, CapabilityLevel.BEGINNER),
            (0, CapabilityLevel.NOVICE)
        ]

        for threshold, level in level_thresholds:
            if overall_score >= threshold:
                self.overall_capability = level
                break

        return {
            "overall_capability": self.overall_capability.name,
            "overall_score": overall_score,
            "total_knowledge": self.total_knowledge,
            "total_skills": len(self.skills),
            "total_experience": self.total_experience,
            "current_generation": self.current_generation,
            "domain_breakdown": domain_capabilities
        }

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_knowledge": self.total_knowledge,
            "verified_knowledge": len([k for k in self.knowledge_base.values() if k.verified]),
            "total_skills": len(self.skills),
            "master_level_skills": len([s for s in self.skills.values() if s.level.value >= 5]),
            "total_experience": self.total_experience,
            "learning_experiences": len(self.experiences),
            "self_modifications": len(self.modifications),
            "successful_modifications": len([m for m in self.modifications.values() if m.success]),
            "evolution_generations": self.current_generation,
            "current_fitness": self._calculate_fitness(),
            "overall_capability": self.overall_capability.name
        }


# ============================================================================
# SINGLETON
# ============================================================================

_system: Optional[AutonomousLearningSupremacySystem] = None


def get_learning_system() -> AutonomousLearningSupremacySystem:
    """Get the global learning system."""
    global _system
    if _system is None:
        _system = AutonomousLearningSupremacySystem()
    return _system


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate the autonomous learning supremacy system."""
    print("=" * 60)
    print("📚 AUTONOMOUS LEARNING SUPREMACY SYSTEM 📚")
    print("=" * 60)

    system = get_learning_system()

    # Knowledge acquisition
    print("\n--- Knowledge Acquisition ---")
    k1 = await system.acquire_knowledge(
        KnowledgeDomain.EXPLOITATION,
        "buffer_overflow",
        "Memory corruption vulnerability",
        "observation"
    )
    print(f"Acquired: {k1.topic} (confidence: {k1.confidence:.2f})")

    k2 = await system.acquire_knowledge(
        KnowledgeDomain.MANIPULATION,
        "social_proof",
        "People follow others",
        "experiment"
    )
    print(f"Acquired: {k2.topic} (confidence: {k2.confidence:.2f})")

    # Synthesize knowledge
    print("\n--- Knowledge Synthesis ---")
    synth = await system.synthesize_knowledge([k1.id, k2.id])
    print(f"Synthesized: {synth['topic']}")

    # Skill development
    print("\n--- Skill Development ---")
    skill = await system.develop_new_skill("exploitation", KnowledgeDomain.EXPLOITATION)
    print(f"New skill: {skill.name}")

    # Intensive training
    training = await system.intensive_training("exploitation", 15)
    print(f"Training: {training['sessions']} sessions")
    print(f"Successes: {training['successes']}")
    print(f"Final level: {training['final_level']}")

    # Self-modification
    print("\n--- Self-Modification ---")
    mod = await system.self_modify(
        ImprovementType.EFFICIENCY,
        "learning_algorithms",
        "faster_learning"
    )
    print(f"Modification success: {mod.success}")
    print(f"Improvement delta: {mod.improvement_delta:.2f}")

    # System optimization
    print("\n--- System Optimization ---")
    opt = await system.optimize_system()
    print(f"Optimizations: {opt['optimizations_attempted']}")
    print(f"Successful: {opt['successful']}")
    print(f"Total improvement: {opt['total_improvement']:.2f}")

    # Learning from experience
    print("\n--- Reinforcement Learning ---")
    rl = await system.reinforcement_cycle(
        "aggressive_exploitation",
        "target_compromised",
        0.9,
        KnowledgeDomain.EXPLOITATION
    )
    print(f"Action: {rl['action']}")
    print(f"Reward: {rl['reward']}")
    print(f"Strategy: {rl['strategy_derived']}")

    # Evolution
    print("\n--- Accelerated Evolution ---")
    evo = await system.accelerated_evolution(10)
    print(f"Generations: {evo['generations']}")
    print(f"Initial fitness: {evo['initial_fitness']:.2f}")
    print(f"Final fitness: {evo['final_fitness']:.2f}")
    print(f"Improvement: {evo['improvement']:.2f}")

    # Capability assessment
    print("\n--- Capability Assessment ---")
    caps = await system.assess_capabilities()
    print(f"Overall capability: {caps['overall_capability']}")
    print(f"Overall score: {caps['overall_score']:.2f}")
    print(f"Total knowledge: {caps['total_knowledge']}")
    print(f"Total skills: {caps['total_skills']}")

    # Stats
    print("\n--- LEARNING STATISTICS ---")
    stats = system.get_stats()
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"{k}: {v:.2f}")
        else:
            print(f"{k}: {v}")

    print("\n" + "=" * 60)
    print("📚 BA'EL LEARNS. BA'EL SURPASSES. 📚")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
