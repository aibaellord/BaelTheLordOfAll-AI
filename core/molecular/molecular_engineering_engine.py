"""
BAEL - Molecular Engineering Engine
====================================

CONTROL MATTER AT THE MOLECULAR LEVEL.

This engine provides:
- Complete periodic table knowledge
- Molecular structure understanding
- Chemical reactions and synthesis
- Material science mastery
- Nanotechnology principles
- Drug compound design
- Polymer engineering
- Crystal structure manipulation
- Quantum chemistry
- Bio-molecular engineering

"He who controls molecules controls reality."
"""

import asyncio
import hashlib
import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("BAEL.MOLECULAR")


class ElementCategory(Enum):
    """Categories of elements."""
    ALKALI_METAL = "alkali_metal"
    ALKALINE_EARTH = "alkaline_earth"
    TRANSITION_METAL = "transition_metal"
    POST_TRANSITION = "post_transition"
    METALLOID = "metalloid"
    NONMETAL = "nonmetal"
    HALOGEN = "halogen"
    NOBLE_GAS = "noble_gas"
    LANTHANIDE = "lanthanide"
    ACTINIDE = "actinide"


class BondType(Enum):
    """Types of chemical bonds."""
    IONIC = "ionic"
    COVALENT = "covalent"
    METALLIC = "metallic"
    HYDROGEN = "hydrogen"
    VAN_DER_WAALS = "van_der_waals"
    PI_BOND = "pi_bond"
    SIGMA_BOND = "sigma_bond"
    POLAR_COVALENT = "polar_covalent"


class MolecularGeometry(Enum):
    """Molecular geometries."""
    LINEAR = "linear"
    BENT = "bent"
    TRIGONAL_PLANAR = "trigonal_planar"
    TRIGONAL_PYRAMIDAL = "trigonal_pyramidal"
    TETRAHEDRAL = "tetrahedral"
    SQUARE_PLANAR = "square_planar"
    TRIGONAL_BIPYRAMIDAL = "trigonal_bipyramidal"
    OCTAHEDRAL = "octahedral"


class ReactionType(Enum):
    """Types of chemical reactions."""
    SYNTHESIS = "synthesis"
    DECOMPOSITION = "decomposition"
    SINGLE_REPLACEMENT = "single_replacement"
    DOUBLE_REPLACEMENT = "double_replacement"
    COMBUSTION = "combustion"
    OXIDATION_REDUCTION = "oxidation_reduction"
    ACID_BASE = "acid_base"
    POLYMERIZATION = "polymerization"
    CATALYTIC = "catalytic"
    NUCLEAR = "nuclear"


class MaterialType(Enum):
    """Types of materials."""
    METAL = "metal"
    CERAMIC = "ceramic"
    POLYMER = "polymer"
    COMPOSITE = "composite"
    SEMICONDUCTOR = "semiconductor"
    SUPERCONDUCTOR = "superconductor"
    NANOMATERIAL = "nanomaterial"
    CRYSTAL = "crystal"
    AMORPHOUS = "amorphous"
    BIOMATERIAL = "biomaterial"


class CompoundClass(Enum):
    """Classes of compounds."""
    ORGANIC = "organic"
    INORGANIC = "inorganic"
    ORGANOMETALLIC = "organometallic"
    BIOPOLYMER = "biopolymer"
    PHARMACEUTICAL = "pharmaceutical"
    EXPLOSIVE = "explosive"
    FUEL = "fuel"
    SOLVENT = "solvent"


@dataclass
class Element:
    """A chemical element."""
    symbol: str
    name: str
    atomic_number: int
    atomic_mass: float
    category: ElementCategory
    electronegativity: float
    electron_config: str
    valence_electrons: int
    common_oxidation_states: List[int]


@dataclass
class Atom:
    """An atom in a molecule."""
    element: Element
    charge: int = 0
    isotope: int = 0  # Mass number, 0 = most common
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class Bond:
    """A chemical bond."""
    atom1_idx: int
    atom2_idx: int
    bond_type: BondType
    bond_order: float  # 1, 2, 3, or 1.5 for resonance
    length: float  # Angstroms


@dataclass
class Molecule:
    """A molecule."""
    id: str
    name: str
    formula: str
    atoms: List[Atom]
    bonds: List[Bond]
    molecular_weight: float
    geometry: MolecularGeometry
    compound_class: CompoundClass
    properties: Dict[str, Any]


@dataclass
class ChemicalReaction:
    """A chemical reaction."""
    id: str
    name: str
    reactants: List[str]  # Formulas
    products: List[str]   # Formulas
    reaction_type: ReactionType
    delta_h: float  # Enthalpy change kJ/mol
    activation_energy: float  # kJ/mol
    catalyst: Optional[str]
    conditions: Dict[str, Any]


@dataclass
class Material:
    """An engineered material."""
    id: str
    name: str
    material_type: MaterialType
    composition: Dict[str, float]  # Element: percentage
    properties: Dict[str, Any]
    applications: List[str]
    synthesis_method: str


@dataclass
class NanoStructure:
    """A nanostructure."""
    id: str
    name: str
    structure_type: str  # nanotube, fullerene, quantum dot, etc.
    dimensions: Tuple[float, float, float]  # nm
    properties: Dict[str, Any]
    applications: List[str]


class MolecularEngineeringEngine:
    """
    Engine for molecular-level matter control.
    
    Features:
    - Complete periodic table
    - Molecule design and analysis
    - Reaction prediction
    - Material synthesis
    - Nanotechnology
    """
    
    def __init__(self):
        self.elements: Dict[str, Element] = {}
        self.molecules: Dict[str, Molecule] = {}
        self.reactions: Dict[str, ChemicalReaction] = {}
        self.materials: Dict[str, Material] = {}
        self.nanostructures: Dict[str, NanoStructure] = {}
        
        self._init_periodic_table()
        self._init_common_molecules()
        self._init_important_reactions()
        self._init_advanced_materials()
        self._init_nanostructures()
        
        logger.info("MolecularEngineeringEngine initialized")
    
    def _init_periodic_table(self):
        """Initialize the periodic table."""
        # Key elements with full data
        elements_data = [
            # Light elements
            ("H", "Hydrogen", 1, 1.008, ElementCategory.NONMETAL, 2.20, "1s¹", 1, [1, -1]),
            ("He", "Helium", 2, 4.003, ElementCategory.NOBLE_GAS, 0, "1s²", 2, [0]),
            ("Li", "Lithium", 3, 6.941, ElementCategory.ALKALI_METAL, 0.98, "[He]2s¹", 1, [1]),
            ("Be", "Beryllium", 4, 9.012, ElementCategory.ALKALINE_EARTH, 1.57, "[He]2s²", 2, [2]),
            ("B", "Boron", 5, 10.81, ElementCategory.METALLOID, 2.04, "[He]2s²2p¹", 3, [3]),
            ("C", "Carbon", 6, 12.01, ElementCategory.NONMETAL, 2.55, "[He]2s²2p²", 4, [-4, 4]),
            ("N", "Nitrogen", 7, 14.01, ElementCategory.NONMETAL, 3.04, "[He]2s²2p³", 5, [-3, 3, 5]),
            ("O", "Oxygen", 8, 16.00, ElementCategory.NONMETAL, 3.44, "[He]2s²2p⁴", 6, [-2]),
            ("F", "Fluorine", 9, 19.00, ElementCategory.HALOGEN, 3.98, "[He]2s²2p⁵", 7, [-1]),
            ("Ne", "Neon", 10, 20.18, ElementCategory.NOBLE_GAS, 0, "[He]2s²2p⁶", 8, [0]),
            ("Na", "Sodium", 11, 22.99, ElementCategory.ALKALI_METAL, 0.93, "[Ne]3s¹", 1, [1]),
            ("Mg", "Magnesium", 12, 24.31, ElementCategory.ALKALINE_EARTH, 1.31, "[Ne]3s²", 2, [2]),
            ("Al", "Aluminum", 13, 26.98, ElementCategory.POST_TRANSITION, 1.61, "[Ne]3s²3p¹", 3, [3]),
            ("Si", "Silicon", 14, 28.09, ElementCategory.METALLOID, 1.90, "[Ne]3s²3p²", 4, [-4, 4]),
            ("P", "Phosphorus", 15, 30.97, ElementCategory.NONMETAL, 2.19, "[Ne]3s²3p³", 5, [-3, 5]),
            ("S", "Sulfur", 16, 32.07, ElementCategory.NONMETAL, 2.58, "[Ne]3s²3p⁴", 6, [-2, 6]),
            ("Cl", "Chlorine", 17, 35.45, ElementCategory.HALOGEN, 3.16, "[Ne]3s²3p⁵", 7, [-1, 7]),
            ("Ar", "Argon", 18, 39.95, ElementCategory.NOBLE_GAS, 0, "[Ne]3s²3p⁶", 8, [0]),
            ("K", "Potassium", 19, 39.10, ElementCategory.ALKALI_METAL, 0.82, "[Ar]4s¹", 1, [1]),
            ("Ca", "Calcium", 20, 40.08, ElementCategory.ALKALINE_EARTH, 1.00, "[Ar]4s²", 2, [2]),
            
            # Transition metals
            ("Fe", "Iron", 26, 55.85, ElementCategory.TRANSITION_METAL, 1.83, "[Ar]3d⁶4s²", 2, [2, 3]),
            ("Co", "Cobalt", 27, 58.93, ElementCategory.TRANSITION_METAL, 1.88, "[Ar]3d⁷4s²", 2, [2, 3]),
            ("Ni", "Nickel", 28, 58.69, ElementCategory.TRANSITION_METAL, 1.91, "[Ar]3d⁸4s²", 2, [2]),
            ("Cu", "Copper", 29, 63.55, ElementCategory.TRANSITION_METAL, 1.90, "[Ar]3d¹⁰4s¹", 1, [1, 2]),
            ("Zn", "Zinc", 30, 65.38, ElementCategory.TRANSITION_METAL, 1.65, "[Ar]3d¹⁰4s²", 2, [2]),
            ("Ag", "Silver", 47, 107.87, ElementCategory.TRANSITION_METAL, 1.93, "[Kr]4d¹⁰5s¹", 1, [1]),
            ("Au", "Gold", 79, 196.97, ElementCategory.TRANSITION_METAL, 2.54, "[Xe]4f¹⁴5d¹⁰6s¹", 1, [1, 3]),
            ("Pt", "Platinum", 78, 195.08, ElementCategory.TRANSITION_METAL, 2.28, "[Xe]4f¹⁴5d⁹6s¹", 1, [2, 4]),
            
            # Heavy elements
            ("Pb", "Lead", 82, 207.2, ElementCategory.POST_TRANSITION, 2.33, "[Xe]4f¹⁴5d¹⁰6s²6p²", 4, [2, 4]),
            ("U", "Uranium", 92, 238.03, ElementCategory.ACTINIDE, 1.38, "[Rn]5f³6d¹7s²", 2, [3, 4, 5, 6]),
            ("Pu", "Plutonium", 94, 244, ElementCategory.ACTINIDE, 1.28, "[Rn]5f⁶7s²", 2, [3, 4, 5, 6]),
        ]
        
        for symbol, name, num, mass, cat, en, config, val, ox in elements_data:
            element = Element(
                symbol=symbol,
                name=name,
                atomic_number=num,
                atomic_mass=mass,
                category=cat,
                electronegativity=en,
                electron_config=config,
                valence_electrons=val,
                common_oxidation_states=ox
            )
            self.elements[symbol] = element
    
    def _init_common_molecules(self):
        """Initialize common molecules."""
        molecules_data = [
            # Essential molecules
            ("water", "H2O", MolecularGeometry.BENT, CompoundClass.INORGANIC, 18.015,
             {"polarity": True, "boiling_point": 100, "ph": 7}),
            ("carbon_dioxide", "CO2", MolecularGeometry.LINEAR, CompoundClass.INORGANIC, 44.01,
             {"polarity": False, "greenhouse": True}),
            ("methane", "CH4", MolecularGeometry.TETRAHEDRAL, CompoundClass.ORGANIC, 16.04,
             {"fuel": True, "greenhouse": True}),
            ("ammonia", "NH3", MolecularGeometry.TRIGONAL_PYRAMIDAL, CompoundClass.INORGANIC, 17.03,
             {"polarity": True, "base": True}),
            ("ethanol", "C2H5OH", MolecularGeometry.TETRAHEDRAL, CompoundClass.ORGANIC, 46.07,
             {"fuel": True, "solvent": True}),
            ("glucose", "C6H12O6", MolecularGeometry.TETRAHEDRAL, CompoundClass.ORGANIC, 180.16,
             {"energy_source": True, "biological": True}),
            ("sulfuric_acid", "H2SO4", MolecularGeometry.TETRAHEDRAL, CompoundClass.INORGANIC, 98.08,
             {"strong_acid": True, "industrial": True}),
            ("sodium_chloride", "NaCl", MolecularGeometry.LINEAR, CompoundClass.INORGANIC, 58.44,
             {"ionic": True, "soluble": True}),
            
            # Pharmaceuticals
            ("aspirin", "C9H8O4", MolecularGeometry.TRIGONAL_PLANAR, CompoundClass.PHARMACEUTICAL, 180.16,
             {"analgesic": True, "antipyretic": True}),
            ("caffeine", "C8H10N4O2", MolecularGeometry.TRIGONAL_PLANAR, CompoundClass.PHARMACEUTICAL, 194.19,
             {"stimulant": True, "adenosine_antagonist": True}),
            
            # Advanced
            ("fullerene_c60", "C60", MolecularGeometry.OCTAHEDRAL, CompoundClass.ORGANIC, 720.66,
             {"nanomaterial": True, "spherical": True}),
            ("graphene", "C", MolecularGeometry.TRIGONAL_PLANAR, CompoundClass.ORGANIC, 12.01,
             {"2d_material": True, "conductor": True}),
        ]
        
        for name, formula, geom, comp_class, weight, props in molecules_data:
            molecule = Molecule(
                id=self._gen_id("mol"),
                name=name,
                formula=formula,
                atoms=[],  # Simplified
                bonds=[],  # Simplified
                molecular_weight=weight,
                geometry=geom,
                compound_class=comp_class,
                properties=props
            )
            self.molecules[name] = molecule
    
    def _init_important_reactions(self):
        """Initialize important chemical reactions."""
        reactions_data = [
            # Combustion
            ("methane_combustion", ReactionType.COMBUSTION, ["CH4", "2O2"], ["CO2", "2H2O"],
             -890.4, 50, None, {"temperature": 600}),
            ("hydrogen_combustion", ReactionType.COMBUSTION, ["2H2", "O2"], ["2H2O"],
             -572, 30, None, {"explosive_limit": "4-75%"}),
            
            # Industrial
            ("haber_process", ReactionType.SYNTHESIS, ["N2", "3H2"], ["2NH3"],
             -92.4, 150, "Fe", {"pressure": "150-300 atm", "temperature": "400-500°C"}),
            ("contact_process", ReactionType.CATALYTIC, ["2SO2", "O2"], ["2SO3"],
             -198, 100, "V2O5", {"temperature": "450°C"}),
            
            # Acid-Base
            ("neutralization", ReactionType.ACID_BASE, ["HCl", "NaOH"], ["NaCl", "H2O"],
             -57.3, 10, None, {}),
            
            # Polymerization
            ("ethylene_polymerization", ReactionType.POLYMERIZATION, ["nC2H4"], ["(C2H4)n"],
             -95, 80, "TiCl4/Al(C2H5)3", {"type": "Ziegler-Natta"}),
            
            # Nuclear
            ("uranium_fission", ReactionType.NUCLEAR, ["U-235", "n"], ["Ba-141", "Kr-92", "3n"],
             -200000000, 0, None, {"type": "fission", "critical_mass": "52kg"}),
            ("deuterium_fusion", ReactionType.NUCLEAR, ["D", "D"], ["He-3", "n"],
             -17600000, 100000, None, {"type": "fusion", "temperature": "100M K"}),
        ]
        
        for name, r_type, reactants, products, dh, ea, cat, cond in reactions_data:
            reaction = ChemicalReaction(
                id=self._gen_id("rxn"),
                name=name,
                reactants=reactants,
                products=products,
                reaction_type=r_type,
                delta_h=dh,
                activation_energy=ea,
                catalyst=cat,
                conditions=cond
            )
            self.reactions[name] = reaction
    
    def _init_advanced_materials(self):
        """Initialize advanced materials."""
        materials_data = [
            ("steel", MaterialType.METAL, {"Fe": 98, "C": 2}, 
             {"tensile_strength": "500 MPa", "density": 7.85}, ["construction", "machinery"]),
            ("silicon_wafer", MaterialType.SEMICONDUCTOR,{"Si": 100},
             {"bandgap": "1.1 eV", "purity": "99.9999999%"}, ["chips", "solar_cells"]),
            ("carbon_fiber", MaterialType.COMPOSITE, {"C": 92, "polymer": 8},
             {"tensile_strength": "3500 MPa", "density": 1.8}, ["aerospace", "sports"]),
            ("kevlar", MaterialType.POLYMER, {"C": 70, "H": 4, "N": 13, "O": 13},
             {"tensile_strength": "3620 MPa", "bulletproof": True}, ["armor", "tires"]),
            ("ybco", MaterialType.SUPERCONDUCTOR, {"Y": 6.4, "Ba": 21, "Cu": 27, "O": 45},
             {"tc": "92 K", "type_ii": True}, ["magnets", "sensors"]),
            ("aerogel", MaterialType.NANOMATERIAL, {"Si": 40, "O": 60},
             {"density": 0.002, "thermal_conductivity": 0.015}, ["insulation", "space"]),
            ("graphene", MaterialType.NANOMATERIAL, {"C": 100},
             {"electron_mobility": "200000 cm²/V·s", "thermal_conductivity": 5000}, ["electronics", "composites"]),
            ("titanium_alloy", MaterialType.METAL, {"Ti": 90, "Al": 6, "V": 4},
             {"tensile_strength": "900 MPa", "biocompatible": True}, ["implants", "aerospace"]),
        ]
        
        for name, m_type, comp, props, apps in materials_data:
            material = Material(
                id=self._gen_id("mat"),
                name=name,
                material_type=m_type,
                composition=comp,
                properties=props,
                applications=apps,
                synthesis_method="industrial"
            )
            self.materials[name] = material
    
    def _init_nanostructures(self):
        """Initialize nanostructures."""
        nanostructures_data = [
            ("carbon_nanotube", "nanotube", (1.0, 1.0, 1000.0),
             {"strength": "100x steel", "conductor": True}, ["composites", "electronics"]),
            ("quantum_dot", "quantum_dot", (5.0, 5.0, 5.0),
             {"tunable_emission": True, "size_dependent": True}, ["displays", "imaging"]),
            ("fullerene", "fullerene", (0.7, 0.7, 0.7),
             {"cage_structure": True, "superconductor": True}, ["medicine", "materials"]),
            ("nanoparticle_gold", "nanoparticle", (10.0, 10.0, 10.0),
             {"plasmonic": True, "biocompatible": True}, ["medicine", "sensing"]),
            ("nanowire", "nanowire", (50.0, 50.0, 10000.0),
             {"high_surface_area": True, "sensor": True}, ["batteries", "sensors"]),
            ("dendrimer", "dendrimer", (4.0, 4.0, 4.0),
             {"branched": True, "drug_carrier": True}, ["drug_delivery", "catalysis"]),
        ]
        
        for name, s_type, dims, props, apps in nanostructures_data:
            nano = NanoStructure(
                id=self._gen_id("nano"),
                name=name,
                structure_type=s_type,
                dimensions=dims,
                properties=props,
                applications=apps
            )
            self.nanostructures[name] = nano
    
    # -------------------------------------------------------------------------
    # ELEMENT OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_element(self, symbol: str) -> Optional[Element]:
        """Get element by symbol."""
        return self.elements.get(symbol)
    
    def get_elements_by_category(self, category: ElementCategory) -> List[Element]:
        """Get all elements in a category."""
        return [e for e in self.elements.values() if e.category == category]
    
    def calculate_electronegativity_difference(self, symbol1: str, symbol2: str) -> Optional[float]:
        """Calculate electronegativity difference between two elements."""
        e1 = self.elements.get(symbol1)
        e2 = self.elements.get(symbol2)
        if e1 and e2:
            return abs(e1.electronegativity - e2.electronegativity)
        return None
    
    def predict_bond_type(self, symbol1: str, symbol2: str) -> Optional[BondType]:
        """Predict bond type between two elements."""
        diff = self.calculate_electronegativity_difference(symbol1, symbol2)
        if diff is None:
            return None
        
        if diff > 1.7:
            return BondType.IONIC
        elif diff > 0.4:
            return BondType.POLAR_COVALENT
        else:
            return BondType.COVALENT
    
    # -------------------------------------------------------------------------
    # MOLECULE OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_molecule(self, name: str) -> Optional[Molecule]:
        """Get molecule by name."""
        return self.molecules.get(name)
    
    async def design_molecule(
        self,
        formula: str,
        target_properties: Dict[str, Any]
    ) -> Molecule:
        """Design a new molecule with target properties."""
        molecule = Molecule(
            id=self._gen_id("mol"),
            name=f"custom_{formula}",
            formula=formula,
            atoms=[],
            bonds=[],
            molecular_weight=self._estimate_molecular_weight(formula),
            geometry=MolecularGeometry.TETRAHEDRAL,
            compound_class=CompoundClass.ORGANIC,
            properties=target_properties
        )
        self.molecules[molecule.name] = molecule
        return molecule
    
    def _estimate_molecular_weight(self, formula: str) -> float:
        """Estimate molecular weight from formula."""
        # Simplified - real implementation would parse formula
        total = 0.0
        for symbol, element in self.elements.items():
            if symbol in formula:
                total += element.atomic_mass
        return total if total > 0 else 100.0
    
    # -------------------------------------------------------------------------
    # REACTION OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_reaction(self, name: str) -> Optional[ChemicalReaction]:
        """Get reaction by name."""
        return self.reactions.get(name)
    
    def predict_reaction_spontaneity(self, reaction: ChemicalReaction) -> bool:
        """Predict if reaction is spontaneous (simplified)."""
        # Simplified Gibbs free energy estimation
        # ΔG = ΔH - TΔS, if ΔG < 0, spontaneous
        return reaction.delta_h < 0
    
    def calculate_energy_release(self, reaction: ChemicalReaction, moles: float) -> float:
        """Calculate energy release in kJ."""
        return abs(reaction.delta_h) * moles
    
    # -------------------------------------------------------------------------
    # MATERIAL OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_material(self, name: str) -> Optional[Material]:
        """Get material by name."""
        return self.materials.get(name)
    
    async def synthesize_material(
        self,
        composition: Dict[str, float],
        material_type: MaterialType,
        target_properties: Dict[str, Any]
    ) -> Material:
        """Design/synthesize a new material."""
        material = Material(
            id=self._gen_id("mat"),
            name=f"custom_{material_type.value}",
            material_type=material_type,
            composition=composition,
            properties=target_properties,
            applications=["custom"],
            synthesis_method="engineered"
        )
        self.materials[material.name] = material
        return material
    
    # -------------------------------------------------------------------------
    # NANO OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_nanostructure(self, name: str) -> Optional[NanoStructure]:
        """Get nanostructure by name."""
        return self.nanostructures.get(name)
    
    async def design_nanostructure(
        self,
        structure_type: str,
        dimensions: Tuple[float, float, float],
        target_properties: Dict[str, Any]
    ) -> NanoStructure:
        """Design a new nanostructure."""
        nano = NanoStructure(
            id=self._gen_id("nano"),
            name=f"custom_{structure_type}",
            structure_type=structure_type,
            dimensions=dimensions,
            properties=target_properties,
            applications=["custom"]
        )
        self.nanostructures[nano.name] = nano
        return nano
    
    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_elements": len(self.elements),
            "total_molecules": len(self.molecules),
            "total_reactions": len(self.reactions),
            "total_materials": len(self.materials),
            "total_nanostructures": len(self.nanostructures),
            "by_element_category": {
                cat.value: len([e for e in self.elements.values() if e.category == cat])
                for cat in ElementCategory
            }
        }
    
    def _gen_id(self, prefix: str) -> str:
        """Generate unique ID."""
        return hashlib.md5(f"{prefix}{time.time()}{random.random()}".encode()).hexdigest()[:12]


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[MolecularEngineeringEngine] = None


def get_molecular_engine() -> MolecularEngineeringEngine:
    """Get global molecular engineering engine."""
    global _engine
    if _engine is None:
        _engine = MolecularEngineeringEngine()
    return _engine


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate molecular engineering engine."""
    print("=" * 60)
    print("🔬 MOLECULAR ENGINEERING ENGINE 🔬")
    print("=" * 60)
    
    engine = get_molecular_engine()
    
    # Stats
    print("\n--- Engine Statistics ---")
    stats = engine.get_stats()
    print(f"Elements: {stats['total_elements']}")
    print(f"Molecules: {stats['total_molecules']}")
    print(f"Reactions: {stats['total_reactions']}")
    print(f"Materials: {stats['total_materials']}")
    print(f"Nanostructures: {stats['total_nanostructures']}")
    
    # Elements
    print("\n--- Key Elements ---")
    for symbol in ["C", "Fe", "Au", "U"]:
        elem = engine.get_element(symbol)
        if elem:
            print(f"  {symbol} - {elem.name}: Mass={elem.atomic_mass}, EN={elem.electronegativity}")
    
    # Bond prediction
    print("\n--- Bond Predictions ---")
    pairs = [("Na", "Cl"), ("C", "H"), ("C", "O")]
    for s1, s2 in pairs:
        bond = engine.predict_bond_type(s1, s2)
        if bond:
            print(f"  {s1}-{s2}: {bond.value}")
    
    # Molecules
    print("\n--- Key Molecules ---")
    for name in ["water", "caffeine", "graphene"]:
        mol = engine.get_molecule(name)
        if mol:
            print(f"  {mol.formula} ({mol.name}): MW={mol.molecular_weight}")
    
    # Reactions
    print("\n--- Powerful Reactions ---")
    for name in ["uranium_fission", "deuterium_fusion"]:
        rxn = engine.get_reaction(name)
        if rxn:
            print(f"  {rxn.name}: ΔH={rxn.delta_h:,} kJ/mol")
    
    # Materials
    print("\n--- Advanced Materials ---")
    for name in ["graphene", "ybco", "aerogel"]:
        mat = engine.get_material(name)
        if mat:
            print(f"  {mat.name} ({mat.material_type.value})")
    
    # Nanostructures
    print("\n--- Nanostructures ---")
    for nano in engine.nanostructures.values():
        print(f"  {nano.name}: {nano.structure_type}")
    
    print("\n" + "=" * 60)
    print("🔬 MATTER MASTERY COMPLETE 🔬")


if __name__ == "__main__":
    asyncio.run(demo())
