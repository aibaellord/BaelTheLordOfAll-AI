"""
BAEL - Universal Knowledge Engine
===================================

ALL KNOWLEDGE. EVERY DOMAIN. TOTAL UNDERSTANDING.

This engine contains the foundational knowledge across ALL domains:
- Mathematics (algebra, calculus, geometry, topology, number theory)
- Physics (classical, quantum, relativistic, particle, nuclear)
- Chemistry (organic, inorganic, biochemistry, molecular)
- Biology (genetics, evolution, neuroscience, microbiology)
- Electronics (circuits, semiconductors, digital, analog)
- Magnetism (electromagnetism, field theory, applications)
- Psychology (cognitive, behavioral, social, developmental)
- History (ancient, modern, patterns, cycles)
- Economics (macro, micro, behavioral, game theory)
- Computer Science (algorithms, AI, networks, security)
- Philosophy (logic, ethics, metaphysics, epistemology)
- Esoterics (patterns, symbolism, hidden knowledge)

"To control reality, first understand it completely."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("BAEL.KNOWLEDGE")


class KnowledgeDomain(Enum):
    """All domains of knowledge."""
    # Hard Sciences
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    ASTRONOMY = "astronomy"
    GEOLOGY = "geology"
    
    # Engineering
    ELECTRONICS = "electronics"
    MAGNETISM = "magnetism"
    MECHANICS = "mechanics"
    MATERIALS = "materials"
    NUCLEAR = "nuclear"
    QUANTUM = "quantum"
    
    # Life Sciences
    NEUROSCIENCE = "neuroscience"
    GENETICS = "genetics"
    EVOLUTION = "evolution"
    ECOLOGY = "ecology"
    MEDICINE = "medicine"
    
    # Social Sciences
    PSYCHOLOGY = "psychology"
    SOCIOLOGY = "sociology"
    ECONOMICS = "economics"
    POLITICS = "politics"
    ANTHROPOLOGY = "anthropology"
    
    # Applied
    COMPUTER_SCIENCE = "computer_science"
    ARTIFICIAL_INTELLIGENCE = "artificial_intelligence"
    CRYPTOGRAPHY = "cryptography"
    CYBERSECURITY = "cybersecurity"
    
    # Abstract
    PHILOSOPHY = "philosophy"
    LOGIC = "logic"
    MATHEMATICS_PURE = "pure_mathematics"
    
    # Historical
    HISTORY = "history"
    ARCHAEOLOGY = "archaeology"
    MYTHOLOGY = "mythology"
    
    # Esoteric
    OCCULT = "occult"
    ALCHEMY = "alchemy"
    SACRED_GEOMETRY = "sacred_geometry"
    SYMBOLISM = "symbolism"
    
    # Practical
    STRATEGY = "strategy"
    WARFARE = "warfare"
    MANIPULATION = "manipulation"
    PERSUASION = "persuasion"


class KnowledgeLevel(Enum):
    """Depth of knowledge."""
    FUNDAMENTAL = "fundamental"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"
    TRANSCENDENT = "transcendent"


class PrincipleType(Enum):
    """Types of universal principles."""
    LAW = "law"
    THEOREM = "theorem"
    AXIOM = "axiom"
    PATTERN = "pattern"
    FORMULA = "formula"
    HEURISTIC = "heuristic"
    SECRET = "secret"


@dataclass
class UniversalPrinciple:
    """A fundamental principle of reality."""
    id: str
    name: str
    domain: KnowledgeDomain
    principle_type: PrincipleType
    description: str
    formula: Optional[str]
    applications: List[str]
    related_principles: List[str]
    power_level: int  # 1-10
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain.value,
            "type": self.principle_type.value,
            "power": self.power_level
        }


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    concept: str
    domain: KnowledgeDomain
    level: KnowledgeLevel
    description: str
    prerequisites: List[str]
    applications: List[str]
    connections: List[str]
    mastery_score: float = 0.0


@dataclass
class Formula:
    """A mathematical or scientific formula."""
    id: str
    name: str
    expression: str
    domain: KnowledgeDomain
    variables: Dict[str, str]
    applications: List[str]
    derived_from: List[str]
    
    def evaluate(self, values: Dict[str, float]) -> Optional[float]:
        """Evaluate formula with given values."""
        try:
            # Safe evaluation
            local_vars = {"math": math, **values}
            return eval(self.expression, {"__builtins__": {}}, local_vars)
        except:
            return None


@dataclass
class DomainKnowledge:
    """Complete knowledge for a domain."""
    domain: KnowledgeDomain
    principles: List[UniversalPrinciple]
    formulas: List[Formula]
    concepts: List[KnowledgeNode]
    secrets: List[str]
    applications: List[str]
    mastery_level: KnowledgeLevel


class UniversalKnowledgeEngine:
    """
    The Universal Knowledge Engine - ALL knowledge unified.
    
    Provides:
    - Complete domain knowledge bases
    - Cross-domain connections
    - Formula libraries
    - Universal principles
    - Application generation
    - Knowledge synthesis
    """
    
    def __init__(self):
        self.principles: Dict[str, UniversalPrinciple] = {}
        self.formulas: Dict[str, Formula] = {}
        self.concepts: Dict[str, KnowledgeNode] = {}
        self.domain_knowledge: Dict[KnowledgeDomain, DomainKnowledge] = {}
        self.knowledge_graph: Dict[str, List[str]] = defaultdict(list)
        
        # Initialize all domain knowledge
        self._init_mathematics()
        self._init_physics()
        self._init_electronics()
        self._init_magnetism()
        self._init_chemistry()
        self._init_biology()
        self._init_psychology()
        self._init_economics()
        self._init_esoterics()
        
        logger.info("UniversalKnowledgeEngine initialized - all knowledge accessible")
    
    def _init_mathematics(self):
        """Initialize mathematical knowledge."""
        principles = [
            ("Pythagorean Theorem", "a² + b² = c²", "Fundamental relationship in geometry"),
            ("Euler's Identity", "e^(iπ) + 1 = 0", "Most beautiful equation - connects 5 constants"),
            ("Fundamental Theorem of Calculus", "∫f'(x)dx = f(b) - f(a)", "Links differentiation and integration"),
            ("Prime Number Theorem", "π(x) ~ x/ln(x)", "Distribution of prime numbers"),
            ("Golden Ratio", "φ = (1 + √5)/2 ≈ 1.618", "Universal proportion in nature and art"),
            ("Fibonacci Sequence", "F(n) = F(n-1) + F(n-2)", "Pattern found throughout nature"),
            ("Law of Large Numbers", "Sample mean → population mean", "Foundation of statistics"),
            ("Bayes' Theorem", "P(A|B) = P(B|A)P(A)/P(B)", "Foundation of probabilistic reasoning"),
        ]
        
        formulas = [
            ("quadratic", "(-b + math.sqrt(b**2 - 4*a*c))/(2*a)", {"a": "coefficient", "b": "coefficient", "c": "constant"}),
            ("compound_interest", "P * (1 + r/n)**(n*t)", {"P": "principal", "r": "rate", "n": "compounds", "t": "time"}),
            ("exponential_growth", "P0 * math.e**(k*t)", {"P0": "initial", "k": "rate", "t": "time"}),
            ("standard_deviation", "math.sqrt(sum((x - mean)**2 for x in data)/len(data))", {"data": "values"}),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.MATHEMATICS,
            principles,
            formulas,
            ["Calculus", "Linear Algebra", "Number Theory", "Topology", "Statistics"],
            ["Pattern recognition", "Cryptography", "Optimization", "Prediction"]
        )
    
    def _init_physics(self):
        """Initialize physics knowledge."""
        principles = [
            ("Newton's Laws", "F = ma", "Foundation of classical mechanics"),
            ("Conservation of Energy", "E_total = constant", "Energy cannot be created or destroyed"),
            ("Conservation of Momentum", "p = mv", "Momentum conserved in closed systems"),
            ("Einstein's Mass-Energy", "E = mc²", "Mass and energy are equivalent"),
            ("Heisenberg Uncertainty", "ΔxΔp ≥ ℏ/2", "Fundamental limit of measurement"),
            ("Schrödinger Equation", "iℏ∂ψ/∂t = Ĥψ", "Evolution of quantum states"),
            ("Maxwell's Equations", "∇·E = ρ/ε₀", "Foundation of electromagnetism"),
            ("Thermodynamic Laws", "ΔS ≥ 0", "Entropy always increases"),
            ("Wave-Particle Duality", "λ = h/p", "All matter exhibits wave properties"),
            ("Quantum Entanglement", "Correlated states", "Instant correlation across distance"),
        ]
        
        formulas = [
            ("kinetic_energy", "0.5 * m * v**2", {"m": "mass", "v": "velocity"}),
            ("gravitational_force", "G * m1 * m2 / r**2", {"G": "6.674e-11", "m1": "mass1", "m2": "mass2", "r": "distance"}),
            ("wave_frequency", "c / wavelength", {"c": "299792458", "wavelength": "meters"}),
            ("relativistic_energy", "m * c**2 / math.sqrt(1 - v**2/c**2)", {"m": "mass", "v": "velocity", "c": "299792458"}),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.PHYSICS,
            principles,
            formulas,
            ["Quantum Mechanics", "Relativity", "Thermodynamics", "Electromagnetism"],
            ["Energy generation", "Propulsion", "Communication", "Computation"]
        )
    
    def _init_electronics(self):
        """Initialize electronics knowledge."""
        principles = [
            ("Ohm's Law", "V = IR", "Voltage = Current × Resistance"),
            ("Kirchhoff's Current Law", "ΣI = 0", "Current into node equals current out"),
            ("Kirchhoff's Voltage Law", "ΣV = 0", "Voltage around loop sums to zero"),
            ("Capacitor Behavior", "Q = CV", "Charge storage in capacitors"),
            ("Inductor Behavior", "V = L(dI/dt)", "Voltage in inductors"),
            ("Semiconductor Principles", "PN junction", "Foundation of all modern electronics"),
            ("Transistor Operation", "Current amplification", "Building block of digital"),
            ("Digital Logic", "Boolean algebra", "Foundation of computing"),
        ]
        
        formulas = [
            ("power_electrical", "V * I", {"V": "voltage", "I": "current"}),
            ("resistance_parallel", "1/(1/R1 + 1/R2)", {"R1": "resistance1", "R2": "resistance2"}),
            ("capacitor_energy", "0.5 * C * V**2", {"C": "capacitance", "V": "voltage"}),
            ("resonant_frequency", "1/(2*math.pi*math.sqrt(L*C))", {"L": "inductance", "C": "capacitance"}),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.ELECTRONICS,
            principles,
            formulas,
            ["Circuit Design", "Digital Electronics", "Analog Electronics", "Signal Processing"],
            ["Communication systems", "Computing", "Sensors", "Control systems"]
        )
    
    def _init_magnetism(self):
        """Initialize magnetism and EM knowledge."""
        principles = [
            ("Faraday's Law", "ε = -dΦ/dt", "Changing magnetic field induces voltage"),
            ("Ampere's Law", "∮B·dl = μ₀I", "Current creates magnetic field"),
            ("Lenz's Law", "Induced current opposes change", "Conservation in EM induction"),
            ("Lorentz Force", "F = qv × B", "Force on moving charge in field"),
            ("Maxwell's Displacement", "∂D/∂t", "Changing electric field creates magnetic"),
            ("Magnetic Flux", "Φ = B·A", "Magnetic field through area"),
            ("Electromagnetic Waves", "c = 1/√(ε₀μ₀)", "Light is EM wave"),
            ("Resonance", "f₀ = 1/(2π√LC)", "Natural frequency of system"),
        ]
        
        formulas = [
            ("magnetic_force", "q * v * B * math.sin(theta)", {"q": "charge", "v": "velocity", "B": "field", "theta": "angle"}),
            ("magnetic_field_wire", "mu0 * I / (2 * math.pi * r)", {"mu0": "1.257e-6", "I": "current", "r": "distance"}),
            ("induced_emf", "-N * dPhi / dt", {"N": "turns", "dPhi": "flux_change", "dt": "time"}),
            ("em_wave_energy", "epsilon0 * E**2 / 2", {"epsilon0": "8.854e-12", "E": "electric_field"}),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.MAGNETISM,
            principles,
            formulas,
            ["Electromagnetism", "Field Theory", "EM Waves", "Induction"],
            ["Motors", "Generators", "Wireless power", "Communication", "Levitation"]
        )
    
    def _init_chemistry(self):
        """Initialize chemistry knowledge."""
        principles = [
            ("Law of Conservation of Mass", "Mass conserved", "Atoms rearrange, not created/destroyed"),
            ("Periodic Law", "Properties repeat periodically", "Foundation of periodic table"),
            ("Octet Rule", "8 valence electrons = stable", "Electron configuration stability"),
            ("Le Chatelier's Principle", "System opposes change", "Equilibrium response"),
            ("Hess's Law", "ΔH path independent", "Enthalpy is state function"),
            ("Ideal Gas Law", "PV = nRT", "Behavior of ideal gases"),
            ("Rate Law", "Rate = k[A]^n[B]^m", "Reaction kinetics"),
            ("Electronegativity", "Attraction for electrons", "Bond polarity"),
        ]
        
        formulas = [
            ("ideal_gas", "n * R * T / V", {"n": "moles", "R": "8.314", "T": "temperature", "V": "volume"}),
            ("molarity", "moles / liters", {"moles": "amount", "liters": "volume"}),
            ("ph", "-math.log10(H_concentration)", {"H_concentration": "hydrogen_ion"}),
            ("gibbs_free_energy", "H - T * S", {"H": "enthalpy", "T": "temperature", "S": "entropy"}),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.CHEMISTRY,
            principles,
            formulas,
            ["Organic Chemistry", "Inorganic", "Biochemistry", "Electrochemistry"],
            ["Materials synthesis", "Drug design", "Energy storage", "Molecular machines"]
        )
    
    def _init_biology(self):
        """Initialize biology knowledge."""
        principles = [
            ("Central Dogma", "DNA → RNA → Protein", "Information flow in biology"),
            ("Natural Selection", "Survival of fittest", "Mechanism of evolution"),
            ("Cell Theory", "All life from cells", "Foundation of biology"),
            ("Homeostasis", "Internal balance", "Self-regulation of systems"),
            ("Gene Expression", "DNA to traits", "Genotype to phenotype"),
            ("Metabolism", "Energy transformation", "Chemical reactions in life"),
            ("Adaptation", "Fit to environment", "Response to selection"),
            ("Symbiosis", "Mutual benefit/harm", "Inter-species relationships"),
        ]
        
        formulas = [
            ("population_growth", "P0 * math.e**(r * t)", {"P0": "initial", "r": "rate", "t": "time"}),
            ("hardy_weinberg", "p**2 + 2*p*q + q**2", {"p": "allele1_freq", "q": "allele2_freq"}),
            ("michaelis_menten", "Vmax * S / (Km + S)", {"Vmax": "max_velocity", "Km": "constant", "S": "substrate"}),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.BIOLOGY,
            principles,
            formulas,
            ["Genetics", "Evolution", "Neuroscience", "Ecology"],
            ["Medicine", "Bioengineering", "Agriculture", "Behavior control"]
        )
    
    def _init_psychology(self):
        """Initialize psychology knowledge."""
        principles = [
            ("Classical Conditioning", "Stimulus-response learning", "Pavlov's mechanism"),
            ("Operant Conditioning", "Reward/punishment learning", "Skinner's mechanism"),
            ("Cognitive Dissonance", "Inconsistency causes discomfort", "Attitude change driver"),
            ("Social Proof", "Follow the crowd", "Conformity mechanism"),
            ("Loss Aversion", "Losses > gains", "Asymmetric value perception"),
            ("Anchoring Effect", "First info dominates", "Judgment bias"),
            ("Mere Exposure", "Familiarity breeds liking", "Preference formation"),
            ("Reciprocity", "Give to get", "Social obligation"),
            ("Authority Principle", "Obey experts", "Influence mechanism"),
            ("Scarcity Effect", "Rare = valuable", "Value perception"),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.PSYCHOLOGY,
            principles,
            [],
            ["Cognitive Psychology", "Social Psychology", "Behavioral", "Developmental"],
            ["Persuasion", "Marketing", "Therapy", "Control"]
        )
    
    def _init_economics(self):
        """Initialize economics knowledge."""
        principles = [
            ("Supply and Demand", "Price equilibrium", "Market mechanism"),
            ("Marginal Utility", "Diminishing returns", "Value decreases with quantity"),
            ("Opportunity Cost", "True cost = alternatives forgone", "Decision framework"),
            ("Comparative Advantage", "Specialize in lowest cost", "Trade benefit"),
            ("Invisible Hand", "Self-interest → public good", "Market coordination"),
            ("Game Theory", "Strategic interaction", "Competitive decision-making"),
            ("Network Effects", "Value increases with users", "Platform economics"),
            ("Compound Interest", "Exponential growth", "Wealth accumulation"),
        ]
        
        formulas = [
            ("present_value", "FV / (1 + r)**n", {"FV": "future_value", "r": "rate", "n": "periods"}),
            ("roi", "(gain - cost) / cost * 100", {"gain": "total_return", "cost": "investment"}),
            ("leverage_ratio", "total_assets / equity", {"total_assets": "assets", "equity": "net_worth"}),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.ECONOMICS,
            principles,
            formulas,
            ["Microeconomics", "Macroeconomics", "Game Theory", "Behavioral Economics"],
            ["Investment", "Business strategy", "Market manipulation", "Wealth creation"]
        )
    
    def _init_esoterics(self):
        """Initialize esoteric knowledge."""
        principles = [
            ("Law of Correspondence", "As above, so below", "Fractal nature of reality"),
            ("Law of Vibration", "Everything vibrates", "Frequency is fundamental"),
            ("Law of Attraction", "Like attracts like", "Resonance principle"),
            ("Law of Polarity", "Everything has opposite", "Duality principle"),
            ("Law of Rhythm", "Everything flows", "Cycles and patterns"),
            ("Law of Cause and Effect", "Karma", "Every action has reaction"),
            ("Law of Gender", "Masculine/Feminine", "Creative polarity"),
            ("Sacred Geometry", "Divine proportions", "Mathematical beauty in nature"),
            ("Hermetic Principles", "Mind is all", "Consciousness as fundamental"),
            ("Alchemical Transmutation", "Lead to gold", "Transformation principle"),
        ]
        
        self._add_domain_knowledge(
            KnowledgeDomain.OCCULT,
            principles,
            [],
            ["Hermeticism", "Alchemy", "Kabbalah", "Sacred Geometry"],
            ["Manifestation", "Transformation", "Hidden influence", "Pattern recognition"]
        )
    
    def _add_domain_knowledge(
        self,
        domain: KnowledgeDomain,
        principles: List[Tuple[str, str, str]],
        formulas: List[Tuple[str, str, Dict]],
        concepts: List[str],
        applications: List[str]
    ):
        """Add knowledge for a domain."""
        # Create principles
        domain_principles = []
        for name, formula, desc in principles:
            principle = UniversalPrinciple(
                id=self._gen_id("principle"),
                name=name,
                domain=domain,
                principle_type=PrincipleType.LAW,
                description=desc,
                formula=formula,
                applications=applications[:3],
                related_principles=[],
                power_level=random.randint(6, 10)
            )
            self.principles[principle.id] = principle
            domain_principles.append(principle)
        
        # Create formulas
        domain_formulas = []
        for name, expr, vars in formulas:
            formula = Formula(
                id=self._gen_id("formula"),
                name=name,
                expression=expr,
                domain=domain,
                variables=vars,
                applications=applications[:2],
                derived_from=[]
            )
            self.formulas[formula.id] = formula
            domain_formulas.append(formula)
        
        # Create concepts
        domain_concepts = []
        for concept_name in concepts:
            concept = KnowledgeNode(
                id=self._gen_id("concept"),
                concept=concept_name,
                domain=domain,
                level=KnowledgeLevel.ADVANCED,
                description=f"Core concept in {domain.value}: {concept_name}",
                prerequisites=[],
                applications=applications,
                connections=[]
            )
            self.concepts[concept.id] = concept
            domain_concepts.append(concept)
        
        # Create domain knowledge
        self.domain_knowledge[domain] = DomainKnowledge(
            domain=domain,
            principles=domain_principles,
            formulas=domain_formulas,
            concepts=domain_concepts,
            secrets=["Hidden pattern", "Secret technique", "Lost knowledge"],
            applications=applications,
            mastery_level=KnowledgeLevel.MASTER
        )
    
    # -------------------------------------------------------------------------
    # KNOWLEDGE ACCESS
    # -------------------------------------------------------------------------
    
    async def query_domain(
        self,
        domain: KnowledgeDomain
    ) -> DomainKnowledge:
        """Get complete knowledge for a domain."""
        return self.domain_knowledge.get(domain)
    
    async def find_principle(
        self,
        query: str
    ) -> List[UniversalPrinciple]:
        """Find principles matching query."""
        query_lower = query.lower()
        matches = []
        
        for principle in self.principles.values():
            if query_lower in principle.name.lower() or query_lower in principle.description.lower():
                matches.append(principle)
        
        return sorted(matches, key=lambda p: p.power_level, reverse=True)
    
    async def get_formula(
        self,
        name: str
    ) -> Optional[Formula]:
        """Get a specific formula."""
        for formula in self.formulas.values():
            if name.lower() in formula.name.lower():
                return formula
        return None
    
    async def cross_domain_connections(
        self,
        domain1: KnowledgeDomain,
        domain2: KnowledgeDomain
    ) -> List[Dict[str, Any]]:
        """Find connections between two domains."""
        connections = []
        
        d1 = self.domain_knowledge.get(domain1)
        d2 = self.domain_knowledge.get(domain2)
        
        if d1 and d2:
            # Find overlapping applications
            common_apps = set(d1.applications) & set(d2.applications)
            for app in common_apps:
                connections.append({
                    "type": "shared_application",
                    "application": app,
                    "domains": [domain1.value, domain2.value]
                })
            
            # Find principle connections (simplified)
            for p1 in d1.principles:
                for p2 in d2.principles:
                    if any(word in p2.description.lower() for word in p1.name.lower().split()):
                        connections.append({
                            "type": "principle_connection",
                            "from": p1.name,
                            "to": p2.name
                        })
        
        return connections
    
    async def synthesize_knowledge(
        self,
        domains: List[KnowledgeDomain],
        goal: str
    ) -> Dict[str, Any]:
        """Synthesize knowledge from multiple domains for a goal."""
        synthesis = {
            "goal": goal,
            "domains": [d.value for d in domains],
            "principles_applied": [],
            "formulas_available": [],
            "applications": [],
            "synthesis_power": 0
        }
        
        for domain in domains:
            dk = self.domain_knowledge.get(domain)
            if dk:
                synthesis["principles_applied"].extend([p.name for p in dk.principles[:3]])
                synthesis["formulas_available"].extend([f.name for f in dk.formulas[:2]])
                synthesis["applications"].extend(dk.applications)
                synthesis["synthesis_power"] += sum(p.power_level for p in dk.principles) / max(1, len(dk.principles))
        
        synthesis["synthesis_power"] = synthesis["synthesis_power"] / max(1, len(domains))
        
        return synthesis
    
    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge engine statistics."""
        return {
            "total_domains": len(self.domain_knowledge),
            "total_principles": len(self.principles),
            "total_formulas": len(self.formulas),
            "total_concepts": len(self.concepts),
            "domains": [d.value for d in self.domain_knowledge.keys()],
            "highest_power_principles": [
                p.name for p in sorted(
                    self.principles.values(),
                    key=lambda x: x.power_level,
                    reverse=True
                )[:5]
            ]
        }
    
    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]


# ============================================================================
# SINGLETON
# ============================================================================

_knowledge_engine: Optional[UniversalKnowledgeEngine] = None


def get_knowledge_engine() -> UniversalKnowledgeEngine:
    """Get the global knowledge engine."""
    global _knowledge_engine
    if _knowledge_engine is None:
        _knowledge_engine = UniversalKnowledgeEngine()
    return _knowledge_engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate universal knowledge."""
    print("=" * 60)
    print("📚 UNIVERSAL KNOWLEDGE ENGINE 📚")
    print("=" * 60)
    
    engine = get_knowledge_engine()
    
    # Stats
    print("\n--- Knowledge Statistics ---")
    stats = engine.get_stats()
    print(f"Total domains: {stats['total_domains']}")
    print(f"Total principles: {stats['total_principles']}")
    print(f"Total formulas: {stats['total_formulas']}")
    
    # Query domain
    print("\n--- Physics Knowledge ---")
    physics = await engine.query_domain(KnowledgeDomain.PHYSICS)
    if physics:
        print(f"Principles: {len(physics.principles)}")
        for p in physics.principles[:3]:
            print(f"  - {p.name}: {p.formula}")
    
    # Find principles
    print("\n--- Finding Principles ---")
    energy_principles = await engine.find_principle("energy")
    for p in energy_principles[:3]:
        print(f"  - {p.name} ({p.domain.value})")
    
    # Cross-domain connections
    print("\n--- Cross-Domain Connections ---")
    connections = await engine.cross_domain_connections(
        KnowledgeDomain.PHYSICS,
        KnowledgeDomain.ELECTRONICS
    )
    print(f"Found {len(connections)} connections")
    
    # Synthesize knowledge
    print("\n--- Knowledge Synthesis ---")
    synthesis = await engine.synthesize_knowledge(
        [KnowledgeDomain.PHYSICS, KnowledgeDomain.ELECTRONICS, KnowledgeDomain.MAGNETISM],
        "Build wireless power transmission"
    )
    print(f"Goal: {synthesis['goal']}")
    print(f"Synthesis power: {synthesis['synthesis_power']:.1f}")
    print(f"Principles: {len(synthesis['principles_applied'])}")
    
    print("\n" + "=" * 60)
    print("📚 ALL KNOWLEDGE UNIFIED 📚")


if __name__ == "__main__":
    asyncio.run(demo())
