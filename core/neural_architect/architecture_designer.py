"""
BAEL - Neural Architecture Designer
An AI that designs, evolves, and optimizes neural network architectures.

Revolutionary concepts:
1. Genetic architecture search with crossover and mutation
2. Performance-guided evolution
3. Multi-objective optimization (accuracy, speed, size)
4. Architecture DNA encoding
5. Transfer learning of architectural patterns
6. Emergent architecture discovery

This is meta-AI: AI that creates AI architectures.
"""

import asyncio
import copy
import hashlib
import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import math

logger = logging.getLogger("BAEL.NeuralArchitect")


class LayerType(Enum):
    """Types of neural network layers."""
    INPUT = "input"
    DENSE = "dense"
    CONV2D = "conv2d"
    CONV1D = "conv1d"
    LSTM = "lstm"
    GRU = "gru"
    TRANSFORMER = "transformer"
    ATTENTION = "attention"
    POOLING = "pooling"
    DROPOUT = "dropout"
    BATCHNORM = "batchnorm"
    RESIDUAL = "residual"
    OUTPUT = "output"
    EMBEDDING = "embedding"
    FLATTEN = "flatten"


class ActivationType(Enum):
    """Activation functions."""
    RELU = "relu"
    GELU = "gelu"
    SWISH = "swish"
    SIGMOID = "sigmoid"
    TANH = "tanh"
    SOFTMAX = "softmax"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    NONE = "none"


class ArchitectureGoal(Enum):
    """Optimization goals."""
    ACCURACY = "accuracy"
    SPEED = "speed"
    SIZE = "size"
    BALANCED = "balanced"
    MEMORY_EFFICIENT = "memory_efficient"


@dataclass
class LayerGene:
    """Genetic encoding of a layer."""
    layer_id: str
    layer_type: LayerType
    parameters: Dict[str, Any] = field(default_factory=dict)
    activation: ActivationType = ActivationType.RELU
    input_connections: List[str] = field(default_factory=list)
    output_connections: List[str] = field(default_factory=list)
    enabled: bool = True
    
    def mutate(self, mutation_rate: float = 0.1) -> "LayerGene":
        """Create a mutated copy of this layer gene."""
        mutated = copy.deepcopy(self)
        
        # Mutate parameters
        for key, value in mutated.parameters.items():
            if random.random() < mutation_rate:
                if isinstance(value, int):
                    mutated.parameters[key] = max(1, int(value * (0.5 + random.random())))
                elif isinstance(value, float):
                    mutated.parameters[key] = value * (0.8 + random.random() * 0.4)
        
        # Mutate activation
        if random.random() < mutation_rate * 0.5:
            mutated.activation = random.choice(list(ActivationType))
        
        return mutated


@dataclass
class ArchitectureDNA:
    """Complete genetic encoding of a neural architecture."""
    dna_id: str
    name: str
    layers: List[LayerGene] = field(default_factory=list)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    
    # Evolution tracking
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutations: List[str] = field(default_factory=list)
    
    # Performance metrics
    fitness: float = 0.0
    accuracy: float = 0.0
    inference_time_ms: float = 0.0
    parameters_count: int = 0
    memory_mb: float = 0.0
    
    @property
    def depth(self) -> int:
        return len([l for l in self.layers if l.enabled])
    
    @property
    def width(self) -> int:
        widths = []
        for layer in self.layers:
            if layer.enabled and "units" in layer.parameters:
                widths.append(layer.parameters["units"])
        return max(widths) if widths else 0
    
    def calculate_fitness(self, goal: ArchitectureGoal) -> float:
        """Calculate fitness based on goal."""
        if goal == ArchitectureGoal.ACCURACY:
            return self.accuracy
        elif goal == ArchitectureGoal.SPEED:
            return 1.0 / (1.0 + self.inference_time_ms / 100)
        elif goal == ArchitectureGoal.SIZE:
            return 1.0 / (1.0 + self.parameters_count / 1000000)
        elif goal == ArchitectureGoal.MEMORY_EFFICIENT:
            return 1.0 / (1.0 + self.memory_mb / 100)
        else:  # BALANCED
            return (
                0.4 * self.accuracy +
                0.3 * (1.0 / (1.0 + self.inference_time_ms / 100)) +
                0.2 * (1.0 / (1.0 + self.parameters_count / 1000000)) +
                0.1 * (1.0 / (1.0 + self.memory_mb / 100))
            )


class ArchitectureBuilder:
    """Builds neural network code from DNA."""
    
    def __init__(self, framework: str = "pytorch"):
        self.framework = framework
    
    def build_code(self, dna: ArchitectureDNA) -> str:
        """Generate neural network code from DNA."""
        if self.framework == "pytorch":
            return self._build_pytorch(dna)
        else:
            return self._build_keras(dna)
    
    def _build_pytorch(self, dna: ArchitectureDNA) -> str:
        """Generate PyTorch code."""
        lines = [
            "import torch",
            "import torch.nn as nn",
            "import torch.nn.functional as F",
            "",
            f"class {dna.name}(nn.Module):",
            "    '''Auto-generated neural network architecture.'''",
            "",
            "    def __init__(self):",
            "        super().__init__()",
        ]
        
        # Generate layers
        prev_size = None
        for layer in dna.layers:
            if not layer.enabled:
                continue
            
            layer_code = self._layer_to_pytorch(layer, prev_size)
            if layer_code:
                lines.append(f"        {layer_code}")
                if "units" in layer.parameters:
                    prev_size = layer.parameters["units"]
        
        # Generate forward method
        lines.extend([
            "",
            "    def forward(self, x):",
        ])
        
        for layer in dna.layers:
            if not layer.enabled:
                continue
            forward_code = self._forward_pytorch(layer)
            if forward_code:
                lines.append(f"        {forward_code}")
        
        lines.append("        return x")
        
        return "\n".join(lines)
    
    def _layer_to_pytorch(self, layer: LayerGene, prev_size: Optional[int]) -> str:
        """Convert layer gene to PyTorch layer definition."""
        params = layer.parameters
        
        if layer.layer_type == LayerType.DENSE:
            in_features = prev_size or params.get("in_features", 256)
            out_features = params.get("units", 128)
            return f"self.{layer.layer_id} = nn.Linear({in_features}, {out_features})"
        
        elif layer.layer_type == LayerType.CONV2D:
            in_ch = params.get("in_channels", 3)
            out_ch = params.get("out_channels", 64)
            kernel = params.get("kernel_size", 3)
            return f"self.{layer.layer_id} = nn.Conv2d({in_ch}, {out_ch}, {kernel}, padding=1)"
        
        elif layer.layer_type == LayerType.LSTM:
            input_size = prev_size or params.get("input_size", 256)
            hidden_size = params.get("units", 128)
            return f"self.{layer.layer_id} = nn.LSTM({input_size}, {hidden_size}, batch_first=True)"
        
        elif layer.layer_type == LayerType.DROPOUT:
            rate = params.get("rate", 0.5)
            return f"self.{layer.layer_id} = nn.Dropout({rate})"
        
        elif layer.layer_type == LayerType.BATCHNORM:
            features = prev_size or params.get("features", 128)
            return f"self.{layer.layer_id} = nn.BatchNorm1d({features})"
        
        elif layer.layer_type == LayerType.EMBEDDING:
            vocab_size = params.get("vocab_size", 10000)
            embed_dim = params.get("embed_dim", 256)
            return f"self.{layer.layer_id} = nn.Embedding({vocab_size}, {embed_dim})"
        
        return None
    
    def _forward_pytorch(self, layer: LayerGene) -> str:
        """Generate forward pass code for layer."""
        activation = self._activation_pytorch(layer.activation)
        
        if layer.layer_type in [LayerType.DENSE, LayerType.CONV2D]:
            if activation:
                return f"x = {activation}(self.{layer.layer_id}(x))"
            return f"x = self.{layer.layer_id}(x)"
        
        elif layer.layer_type == LayerType.LSTM:
            return f"x, _ = self.{layer.layer_id}(x)"
        
        elif layer.layer_type in [LayerType.DROPOUT, LayerType.BATCHNORM]:
            return f"x = self.{layer.layer_id}(x)"
        
        elif layer.layer_type == LayerType.FLATTEN:
            return "x = x.view(x.size(0), -1)"
        
        elif layer.layer_type == LayerType.POOLING:
            pool_type = layer.parameters.get("type", "max")
            size = layer.parameters.get("size", 2)
            if pool_type == "max":
                return f"x = F.max_pool2d(x, {size})"
            return f"x = F.avg_pool2d(x, {size})"
        
        return None
    
    def _activation_pytorch(self, activation: ActivationType) -> str:
        """Get PyTorch activation function."""
        mapping = {
            ActivationType.RELU: "F.relu",
            ActivationType.GELU: "F.gelu",
            ActivationType.SIGMOID: "torch.sigmoid",
            ActivationType.TANH: "torch.tanh",
            ActivationType.LEAKY_RELU: "F.leaky_relu",
            ActivationType.ELU: "F.elu",
            ActivationType.SOFTMAX: "F.softmax",
            ActivationType.NONE: None
        }
        return mapping.get(activation)
    
    def _build_keras(self, dna: ArchitectureDNA) -> str:
        """Generate Keras code."""
        lines = [
            "from tensorflow import keras",
            "from tensorflow.keras import layers",
            "",
            f"def create_{dna.name.lower()}():",
            "    '''Auto-generated neural network architecture.'''",
            "    model = keras.Sequential()",
        ]
        
        for layer in dna.layers:
            if not layer.enabled:
                continue
            layer_code = self._layer_to_keras(layer)
            if layer_code:
                lines.append(f"    model.add({layer_code})")
        
        lines.extend([
            "    return model",
            "",
            f"model = create_{dna.name.lower()}()"
        ])
        
        return "\n".join(lines)
    
    def _layer_to_keras(self, layer: LayerGene) -> str:
        """Convert layer gene to Keras layer."""
        params = layer.parameters
        activation = layer.activation.value if layer.activation != ActivationType.NONE else None
        
        if layer.layer_type == LayerType.DENSE:
            units = params.get("units", 128)
            if activation:
                return f"layers.Dense({units}, activation='{activation}')"
            return f"layers.Dense({units})"
        
        elif layer.layer_type == LayerType.CONV2D:
            filters = params.get("out_channels", 64)
            kernel = params.get("kernel_size", 3)
            if activation:
                return f"layers.Conv2D({filters}, ({kernel}, {kernel}), activation='{activation}', padding='same')"
            return f"layers.Conv2D({filters}, ({kernel}, {kernel}), padding='same')"
        
        elif layer.layer_type == LayerType.LSTM:
            units = params.get("units", 128)
            return f"layers.LSTM({units})"
        
        elif layer.layer_type == LayerType.DROPOUT:
            rate = params.get("rate", 0.5)
            return f"layers.Dropout({rate})"
        
        elif layer.layer_type == LayerType.FLATTEN:
            return "layers.Flatten()"
        
        return None


class NeuralArchitect:
    """
    The Neural Architecture Designer.
    
    Uses evolutionary algorithms to discover optimal neural architectures
    for given tasks and constraints.
    """
    
    def __init__(
        self,
        population_size: int = 20,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        elite_size: int = 2,
        goal: ArchitectureGoal = ArchitectureGoal.BALANCED
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size
        self.goal = goal
        
        self.builder = ArchitectureBuilder()
        
        # Population
        self._population: List[ArchitectureDNA] = []
        self._generation = 0
        self._best_ever: Optional[ArchitectureDNA] = None
        
        # Templates for initialization
        self._templates: Dict[str, List[LayerGene]] = {}
        self._init_templates()
        
        # Statistics
        self._history: List[Dict[str, Any]] = []
        
        logger.info("NeuralArchitect initialized")
    
    def _init_templates(self):
        """Initialize architecture templates."""
        # MLP template
        self._templates["mlp"] = [
            LayerGene("dense1", LayerType.DENSE, {"units": 256}),
            LayerGene("dropout1", LayerType.DROPOUT, {"rate": 0.3}),
            LayerGene("dense2", LayerType.DENSE, {"units": 128}),
            LayerGene("dropout2", LayerType.DROPOUT, {"rate": 0.3}),
            LayerGene("output", LayerType.DENSE, {"units": 10}, ActivationType.SOFTMAX)
        ]
        
        # CNN template
        self._templates["cnn"] = [
            LayerGene("conv1", LayerType.CONV2D, {"in_channels": 3, "out_channels": 32}),
            LayerGene("pool1", LayerType.POOLING, {"size": 2}),
            LayerGene("conv2", LayerType.CONV2D, {"in_channels": 32, "out_channels": 64}),
            LayerGene("pool2", LayerType.POOLING, {"size": 2}),
            LayerGene("flatten", LayerType.FLATTEN, {}),
            LayerGene("dense", LayerType.DENSE, {"units": 128}),
            LayerGene("output", LayerType.DENSE, {"units": 10}, ActivationType.SOFTMAX)
        ]
        
        # LSTM template
        self._templates["lstm"] = [
            LayerGene("embed", LayerType.EMBEDDING, {"vocab_size": 10000, "embed_dim": 128}),
            LayerGene("lstm1", LayerType.LSTM, {"units": 128}),
            LayerGene("dropout", LayerType.DROPOUT, {"rate": 0.5}),
            LayerGene("output", LayerType.DENSE, {"units": 1}, ActivationType.SIGMOID)
        ]
        
        # Transformer-like template
        self._templates["transformer"] = [
            LayerGene("embed", LayerType.EMBEDDING, {"vocab_size": 10000, "embed_dim": 256}),
            LayerGene("attention1", LayerType.ATTENTION, {"heads": 8, "dim": 256}),
            LayerGene("dense1", LayerType.DENSE, {"units": 512}, ActivationType.GELU),
            LayerGene("attention2", LayerType.ATTENTION, {"heads": 8, "dim": 256}),
            LayerGene("dense2", LayerType.DENSE, {"units": 512}, ActivationType.GELU),
            LayerGene("output", LayerType.DENSE, {"units": 10}, ActivationType.SOFTMAX)
        ]
    
    def initialize_population(
        self,
        template: str = "mlp",
        input_shape: Tuple[int, ...] = None,
        output_size: int = 10
    ):
        """Initialize population from template with variations."""
        base_layers = copy.deepcopy(self._templates.get(template, self._templates["mlp"]))
        
        # Update output layer
        base_layers[-1].parameters["units"] = output_size
        
        self._population = []
        
        for i in range(self.population_size):
            dna = ArchitectureDNA(
                dna_id=f"arch_{hashlib.md5(f'{template}{i}{time.time()}'.encode()).hexdigest()[:8]}",
                name=f"Network_{i}",
                layers=copy.deepcopy(base_layers),
                generation=0
            )
            
            # Apply random mutations for diversity
            for _ in range(random.randint(0, 3)):
                self._mutate(dna)
            
            self._population.append(dna)
        
        logger.info(f"Initialized population of {len(self._population)} architectures")
    
    async def evolve(
        self,
        fitness_evaluator: Callable[[ArchitectureDNA], float],
        generations: int = 10,
        early_stop_threshold: float = 0.99
    ) -> ArchitectureDNA:
        """
        Evolve the population to find optimal architecture.
        
        Args:
            fitness_evaluator: Function that evaluates architecture fitness
            generations: Number of generations to evolve
            early_stop_threshold: Stop if fitness exceeds this
        
        Returns:
            Best architecture found
        """
        for gen in range(generations):
            self._generation = gen
            
            # Evaluate fitness
            for dna in self._population:
                dna.fitness = await asyncio.to_thread(fitness_evaluator, dna)
            
            # Sort by fitness
            self._population.sort(key=lambda d: d.fitness, reverse=True)
            
            # Track best
            if self._best_ever is None or self._population[0].fitness > self._best_ever.fitness:
                self._best_ever = copy.deepcopy(self._population[0])
            
            # Record history
            self._history.append({
                "generation": gen,
                "best_fitness": self._population[0].fitness,
                "avg_fitness": sum(d.fitness for d in self._population) / len(self._population),
                "best_id": self._population[0].dna_id
            })
            
            logger.info(f"Generation {gen}: Best fitness = {self._population[0].fitness:.4f}")
            
            # Early stopping
            if self._population[0].fitness >= early_stop_threshold:
                logger.info(f"Early stopping: fitness threshold reached")
                break
            
            # Create next generation
            next_population = []
            
            # Elitism - keep best
            for dna in self._population[:self.elite_size]:
                next_population.append(copy.deepcopy(dna))
            
            # Fill rest with crossover and mutation
            while len(next_population) < self.population_size:
                if random.random() < self.crossover_rate:
                    # Crossover
                    parent1, parent2 = self._select_parents()
                    child = self._crossover(parent1, parent2)
                else:
                    # Clone and mutate
                    parent = self._tournament_select()
                    child = copy.deepcopy(parent)
                
                # Mutate
                if random.random() < self.mutation_rate:
                    self._mutate(child)
                
                child.generation = gen + 1
                child.dna_id = f"arch_{hashlib.md5(f'{gen}{len(next_population)}{time.time()}'.encode()).hexdigest()[:8]}"
                next_population.append(child)
            
            self._population = next_population
        
        return self._best_ever
    
    def _select_parents(self) -> Tuple[ArchitectureDNA, ArchitectureDNA]:
        """Select two parents for crossover."""
        parent1 = self._tournament_select()
        parent2 = self._tournament_select()
        while parent2.dna_id == parent1.dna_id:
            parent2 = self._tournament_select()
        return parent1, parent2
    
    def _tournament_select(self, tournament_size: int = 3) -> ArchitectureDNA:
        """Tournament selection."""
        candidates = random.sample(self._population, min(tournament_size, len(self._population)))
        return max(candidates, key=lambda d: d.fitness)
    
    def _crossover(self, parent1: ArchitectureDNA, parent2: ArchitectureDNA) -> ArchitectureDNA:
        """Crossover two architectures."""
        child_layers = []
        
        # Single-point crossover on layers
        max_layers = max(len(parent1.layers), len(parent2.layers))
        crossover_point = random.randint(1, max_layers - 1)
        
        for i in range(max_layers):
            if i < crossover_point and i < len(parent1.layers):
                child_layers.append(copy.deepcopy(parent1.layers[i]))
            elif i < len(parent2.layers):
                child_layers.append(copy.deepcopy(parent2.layers[i]))
        
        # Crossover hyperparameters
        child_hyperparams = {}
        for key in set(parent1.hyperparameters.keys()) | set(parent2.hyperparameters.keys()):
            if random.random() < 0.5:
                child_hyperparams[key] = parent1.hyperparameters.get(key)
            else:
                child_hyperparams[key] = parent2.hyperparameters.get(key)
        
        return ArchitectureDNA(
            dna_id="",
            name=f"{parent1.name}x{parent2.name}",
            layers=child_layers,
            hyperparameters=child_hyperparams,
            parent_ids=[parent1.dna_id, parent2.dna_id]
        )
    
    def _mutate(self, dna: ArchitectureDNA):
        """Mutate an architecture."""
        mutation_type = random.choice(["layer_param", "add_layer", "remove_layer", "change_activation"])
        
        if mutation_type == "layer_param" and dna.layers:
            # Mutate layer parameters
            layer = random.choice(dna.layers)
            for key, value in layer.parameters.items():
                if random.random() < 0.3:
                    if isinstance(value, int):
                        layer.parameters[key] = max(1, int(value * (0.5 + random.random())))
                    elif isinstance(value, float):
                        layer.parameters[key] = max(0.01, value * (0.8 + random.random() * 0.4))
        
        elif mutation_type == "add_layer" and len(dna.layers) < 20:
            # Add a new layer
            new_layer = LayerGene(
                f"layer_{len(dna.layers)}",
                random.choice([LayerType.DENSE, LayerType.DROPOUT, LayerType.BATCHNORM]),
                {"units": random.choice([64, 128, 256, 512])},
                random.choice([ActivationType.RELU, ActivationType.GELU])
            )
            insert_pos = random.randint(0, len(dna.layers) - 1)
            dna.layers.insert(insert_pos, new_layer)
        
        elif mutation_type == "remove_layer" and len(dna.layers) > 3:
            # Remove a layer (not first or last)
            remove_idx = random.randint(1, len(dna.layers) - 2)
            dna.layers.pop(remove_idx)
        
        elif mutation_type == "change_activation" and dna.layers:
            layer = random.choice(dna.layers)
            layer.activation = random.choice(list(ActivationType))
        
        dna.mutations.append(mutation_type)
    
    def generate_code(self, dna: ArchitectureDNA = None, framework: str = "pytorch") -> str:
        """Generate code for an architecture."""
        target = dna or self._best_ever
        if target is None:
            raise ValueError("No architecture to generate code for")
        
        self.builder.framework = framework
        return self.builder.build_code(target)
    
    def get_best(self) -> Optional[ArchitectureDNA]:
        """Get the best architecture found."""
        return self._best_ever
    
    def get_stats(self) -> Dict[str, Any]:
        """Get evolution statistics."""
        return {
            "generation": self._generation,
            "population_size": len(self._population),
            "best_fitness": self._best_ever.fitness if self._best_ever else 0,
            "best_depth": self._best_ever.depth if self._best_ever else 0,
            "history": self._history[-10:]  # Last 10 generations
        }


import time

# Global instance
_neural_architect: Optional[NeuralArchitect] = None


def get_neural_architect() -> NeuralArchitect:
    """Get the global neural architect."""
    global _neural_architect
    if _neural_architect is None:
        _neural_architect = NeuralArchitect()
    return _neural_architect


async def demo():
    """Demonstrate neural architecture evolution."""
    architect = get_neural_architect()
    
    # Initialize population
    architect.initialize_population(template="mlp", output_size=10)
    
    # Simple fitness evaluator (would use real training in production)
    def mock_evaluator(dna: ArchitectureDNA) -> float:
        # Reward moderate depth
        depth_score = 1.0 - abs(dna.depth - 5) / 10
        # Reward efficient architecture
        total_params = sum(
            l.parameters.get("units", 0) 
            for l in dna.layers if l.enabled
        )
        efficiency_score = 1.0 / (1.0 + total_params / 1000)
        return 0.7 * depth_score + 0.3 * efficiency_score + random.random() * 0.1
    
    # Evolve
    best = await architect.evolve(mock_evaluator, generations=5)
    
    print(f"\n=== BEST ARCHITECTURE ===")
    print(f"ID: {best.dna_id}")
    print(f"Fitness: {best.fitness:.4f}")
    print(f"Depth: {best.depth}")
    print(f"Generation: {best.generation}")
    
    print(f"\n=== GENERATED CODE ===")
    code = architect.generate_code(best)
    print(code)


if __name__ == "__main__":
    asyncio.run(demo())
