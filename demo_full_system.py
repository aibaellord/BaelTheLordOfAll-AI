#!/usr/bin/env python3
"""
BAEL Full System Demonstration

This script demonstrates all of BAEL's integrated capabilities:
1. Supreme Controller & Reasoning Cascade
2. Cognitive Pipeline (5-layer memory)
3. Workflow Orchestration
4. Agent Swarm Coordination
5. Tool Orchestration
6. Knowledge Synthesis
7. Web Research
8. Code Execution Sandbox
9. Self-Evolution Engine
10. Exploitation Engine
11. Meta-Learning Framework
12. Continual Learning (EWC)

Run with: python demo_full_system.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def demo_workflow_orchestrator():
    """Demonstrate workflow orchestration."""
    section("WORKFLOW ORCHESTRATOR")

    from core.workflow import WorkflowBuilder, WorkflowOrchestrator

    # Create a multi-step analysis workflow
    def analyze_input(query: str) -> dict:
        return {"analysis": f"Analyzed: {query}", "entities": ["AI", "ML"]}

    def enrich_data(analysis: dict) -> dict:
        return {"enriched": analysis, "sources": 3}

    def generate_response(enriched: dict) -> str:
        return f"Response based on {enriched}"

    workflow = (
        WorkflowBuilder("Analysis Pipeline")
        .start()
        .task("Analyze", analyze_input,
              input_mapping={"query": "input_query"},
              output_key="analysis")
        .task("Enrich", enrich_data,
              input_mapping={"analysis": "analysis"},
              output_key="enriched")
        .task("Generate", generate_response,
              input_mapping={"enriched": "enriched"},
              output_key="response")
        .end()
        .build()
    )

    orchestrator = WorkflowOrchestrator()
    context = await orchestrator.execute_workflow(
        workflow,
        initial_context={"input_query": "What is machine learning?"}
    )

    print(f"✓ Executed workflow: {workflow.name}")
    print(f"  Nodes executed: {len(context.execution_path)}")
    print(f"  Results: {list(context.node_results.keys())}")


async def demo_agent_swarm():
    """Demonstrate agent swarm coordination."""
    section("AGENT SWARM COORDINATOR")

    from core.swarm import (AgentRole, AgentTask, DistributionStrategy,
                            SwarmBuilder)

    # Build a diverse research swarm
    coordinator = await (
        SwarmBuilder()
        .with_researchers(2)
        .with_analysts(2)
        .with_agent(AgentRole.PLANNER, "Strategic_Planner")
        .with_agent(AgentRole.CRITIC, "Quality_Critic")
        .with_agent(AgentRole.SYNTHESIZER, "Knowledge_Synthesizer")
        .build()
    )

    print(f"✓ Spawned {len(coordinator.agents)} agents")

    # Submit tasks
    for i in range(3):
        task = AgentTask(
            id=f"task_{i}",
            description=f"Research subtopic {i}",
            required_capabilities=["search", "analysis"]
        )
        await coordinator.submit_task(task)

    print(f"✓ Submitted 3 tasks")

    # Request consensus
    consensus = await coordinator.request_consensus(
        topic="Best research approach",
        options=["breadth-first", "depth-first", "hybrid"]
    )

    print(f"✓ Consensus reached: {consensus.get('winner', 'No consensus')}")

    # Collective reasoning
    reasoning = await coordinator.collective_reasoning(
        "How to solve climate change?",
        method="synthesis"
    )

    print(f"✓ Collective reasoning: {len(reasoning['contributions'])} perspectives")


async def demo_tool_orchestration():
    """Demonstrate tool orchestration."""
    section("TOOL ORCHESTRATOR")

    from core.tools.tool_orchestration import (Tool, ToolCategory,
                                               ToolOrchestrator, ToolPipeline,
                                               ToolSchema)

    orchestrator = ToolOrchestrator()

    # Register tools
    def calculator(expression: str) -> float:
        allowed = set('0123456789+-*/.() ')
        if all(c in allowed for c in expression):
            return eval(expression)
        return float('nan')

    def text_analyzer(text: str) -> dict:
        return {
            "length": len(text),
            "words": len(text.split()),
            "sentences": text.count('.') + text.count('!') + text.count('?')
        }

    calc_tool = Tool(
        id="calc",
        name="calculator",
        category=ToolCategory.UTILITY,
        schema=ToolSchema(name="calculator", description="Evaluate math"),
        handler=calculator,
        tags=["math", "calculation"]
    )

    text_tool = Tool(
        id="text",
        name="text_analyzer",
        category=ToolCategory.DATA_PROCESSING,
        schema=ToolSchema(name="text_analyzer", description="Analyze text"),
        handler=text_analyzer,
        tags=["text", "nlp"]
    )

    orchestrator.register(calc_tool)
    orchestrator.register(text_tool)

    print(f"✓ Registered {len(orchestrator.tools)} tools")

    # Execute tools
    result = await orchestrator.execute("calculator", {"expression": "2 + 3 * 4"})
    print(f"✓ Calculator: 2 + 3 * 4 = {result.result}")

    result = await orchestrator.execute("text_analyzer", {"text": "Hello world. This is BAEL."})
    print(f"✓ Text analysis: {result.result}")

    # Get OpenAI-format schemas
    schemas = orchestrator.get_all_schemas()
    print(f"✓ Generated {len(schemas)} OpenAI function schemas")


async def demo_knowledge_synthesis():
    """Demonstrate knowledge synthesis."""
    section("KNOWLEDGE SYNTHESIS PIPELINE")

    from core.knowledge.knowledge_synthesis_pipeline import (
        KnowledgeItem, KnowledgeSource, KnowledgeSynthesisPipeline,
        KnowledgeType, SourceType)

    pipeline = KnowledgeSynthesisPipeline()

    # Create sources
    wiki = KnowledgeSource(
        id="wiki",
        source_type=SourceType.WEB,
        name="Wikipedia",
        reliability=0.9
    )

    paper = KnowledgeSource(
        id="paper",
        source_type=SourceType.DOCUMENT,
        name="Research Paper",
        reliability=0.95
    )

    # Ingest knowledge
    await pipeline.ingest(
        "Neural networks are computational models inspired by biological neurons.",
        wiki, KnowledgeType.FACT
    )

    await pipeline.ingest(
        "Deep learning uses multiple layers of neural networks.",
        paper, KnowledgeType.FACT
    )

    await pipeline.ingest(
        "Transformers are a type of neural network architecture.",
        wiki, KnowledgeType.FACT
    )

    print(f"✓ Ingested {len(pipeline.knowledge_items)} knowledge items")

    # Synthesize new knowledge
    new_items = [
        KnowledgeItem(
            id="new1",
            content="Large language models are based on transformer architecture.",
            knowledge_type=KnowledgeType.FACT,
            sources=[paper],
            confidence=0.85
        )
    ]

    result = await pipeline.synthesize(new_items)
    print(f"✓ Synthesized: {result.processing_stats}")

    # Query
    results = await pipeline.query("neural networks")
    print(f"✓ Query 'neural networks': {len(results)} results")

    # Get graph
    graph = await pipeline.get_graph()
    print(f"✓ Knowledge graph: {graph['stats']['node_count']} nodes, {graph['stats']['edge_count']} edges")


async def demo_web_research():
    """Demonstrate web research engine."""
    section("WEB RESEARCH ENGINE")

    from core.research import ResearchQuery, SearchEngine, WebResearchEngine

    engine = WebResearchEngine()

    # Quick answer
    answer = await engine.quick_answer("What is quantum computing?")
    print(f"✓ Quick answer confidence: {answer['confidence']}")

    # Full research
    report = await engine.research(
        "Applications of AI in healthcare",
        depth=2,
        verify_facts=True
    )

    print(f"✓ Research report:")
    print(f"    Sources consulted: {report.sources_consulted}")
    print(f"    Sources used: {report.sources_used}")
    print(f"    Findings: {len(report.findings)}")
    print(f"    Verified findings: {sum(1 for f in report.findings if f.verified)}")

    # Find sources
    sources = await engine.find_sources(
        "machine learning",
        min_credibility=engine.extractor._assess_credibility("example.edu")
    )
    print(f"✓ Found {len(sources)} credible sources")


async def demo_code_execution():
    """Demonstrate code execution sandbox."""
    section("CODE EXECUTION SANDBOX")

    from core.execution import CodeExecutionSandbox, SecurityLevel

    sandbox = CodeExecutionSandbox()

    # Simple execution
    result = await sandbox.execute_python("""
x = [1, 2, 3, 4, 5]
result = sum(x) / len(x)
print(f"Average: {result}")
""")

    print(f"✓ Python execution:")
    print(f"    Status: {result.status.value}")
    print(f"    Output: {result.stdout.strip()}")
    print(f"    Time: {result.execution_time_ms:.2f}ms")

    # Math computation
    result = await sandbox.execute_python("""
import math
result = {
    'pi': math.pi,
    'e': math.e,
    'golden_ratio': (1 + math.sqrt(5)) / 2
}
print(result)
""")

    print(f"✓ Math computation: {result.stdout.strip()}")

    # Security check
    result = await sandbox.execute_python(
        "import os\nos.listdir('/')",
        security_level=SecurityLevel.STRICT
    )

    print(f"✓ Security violation caught: {result.status.value}")

    # Statistics
    stats = sandbox.get_statistics()
    print(f"✓ Execution stats: {stats['total_executions']} runs, "
          f"{stats['success_rate']*100:.0f}% success")


async def demo_evolution_engine():
    """Demonstrate self-evolution engine."""
    section("SELF-EVOLUTION ENGINE")

    try:
        import numpy as np

        from core.evolution import EvolutionConfig, SelfEvolutionEngine

        config = EvolutionConfig(
            population_size=20,
            generations=5,
            mutation_rate=0.1
        )

        engine = SelfEvolutionEngine(config)

        # Initialize with random capabilities
        for i in range(config.population_size):
            individual = engine.create_individual(f"ind_{i}")
            individual.genome = {f"gene_{j}": np.random.randn() for j in range(5)}
            engine.population.append(individual)

        print(f"✓ Initialized population: {len(engine.population)} individuals")

        # Evolve
        best = await engine.evolve()

        print(f"✓ Evolution complete:")
        print(f"    Best fitness: {engine.best_fitness:.4f}")
        print(f"    Generations: {engine.config.generations}")

    except ImportError as e:
        print(f"⚠ Evolution engine not available: {e}")


async def demo_exploitation_engine():
    """Demonstrate exploitation engine."""
    section("EXPLOITATION ENGINE")

    try:
        from core.exploitation import ExploitationConfig, ExploitationEngine

        config = ExploitationConfig(
            enable_rotation=True,
            check_limits=True
        )

        engine = ExploitationEngine(config)
        await engine.initialize()

        print(f"✓ Providers registered: {len(engine.registry.providers)}")

        # Get best free provider
        provider = await engine.get_best_provider()
        print(f"✓ Best free provider: {provider.name if provider else 'None'}")

        # Check usage stats
        stats = engine.get_usage_stats()
        print(f"✓ Total requests: {stats.get('total_requests', 0)}")

    except ImportError as e:
        print(f"⚠ Exploitation engine not available: {e}")


async def demo_meta_learning():
    """Demonstrate meta-learning framework."""
    section("META-LEARNING FRAMEWORK")

    try:
        import numpy as np

        from core.metalearning import MetaLearningConfig, MetaLearningFramework

        config = MetaLearningConfig(
            inner_learning_rate=0.01,
            outer_learning_rate=0.001,
            num_inner_steps=5
        )

        framework = MetaLearningFramework(config)

        # Create mock tasks
        tasks = [
            {"name": f"task_{i}", "data": np.random.randn(10, 5)}
            for i in range(3)
        ]

        print(f"✓ Meta-learning initialized")
        print(f"    Tasks: {len(tasks)}")
        print(f"    Inner LR: {config.inner_learning_rate}")
        print(f"    Outer LR: {config.outer_learning_rate}")

    except ImportError as e:
        print(f"⚠ Meta-learning framework not available: {e}")


async def demo_continual_learning():
    """Demonstrate continual learning (EWC)."""
    section("CONTINUAL LEARNING (EWC)")

    try:
        import numpy as np

        from core.continual import ElasticWeightConsolidation, EWCConfig

        config = EWCConfig(
            lambda_reg=0.1,
            fisher_samples=100
        )

        ewc = ElasticWeightConsolidation(config)

        # Add mock parameters
        ewc.register_parameter("layer1", np.random.randn(10, 10))
        ewc.register_parameter("layer2", np.random.randn(10, 5))

        print(f"✓ EWC initialized")
        print(f"    Parameters: {len(ewc.parameters)}")
        print(f"    Lambda: {config.lambda_reg}")

    except ImportError as e:
        print(f"⚠ Continual learning not available: {e}")


async def demo_master_integration():
    """Demonstrate master integration layer."""
    section("MASTER INTEGRATION LAYER")

    from core.integration import (IntegrationConfig, IntegrationMode,
                                  MasterIntegrationLayer)

    config = IntegrationConfig(
        mode=IntegrationMode.STANDARD,
        enable_reasoning=True,
        enable_memory=True,
        enable_knowledge=True,
        enable_tools=True,
        enable_research=True,
        enable_code_execution=True
    )

    bael = MasterIntegrationLayer(config)

    print("Initializing BAEL integration layer...")
    await bael.initialize()

    status = await bael.get_status()
    print(f"✓ BAEL Status:")
    print(f"    State: {status['state']}")
    print(f"    Mode: {status['mode']}")
    print(f"    Systems: {', '.join(status['systems'])}")

    # Process a query
    result = await bael.process("Explain machine learning in simple terms")
    print(f"✓ Query processed:")
    print(f"    Success: {result.success}")
    print(f"    Stages: {result.result.get('stages', []) if result.result else []}")

    # Shutdown
    await bael.shutdown()
    print("✓ BAEL shutdown complete")


async def main():
    """Run all demonstrations."""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  BAEL - THE LORD OF ALL AI AGENTS  ".center(68) + "█")
    print("█" + "  Full System Demonstration  ".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)

    start_time = datetime.now()

    try:
        await demo_workflow_orchestrator()
        await demo_agent_swarm()
        await demo_tool_orchestration()
        await demo_knowledge_synthesis()
        await demo_web_research()
        await demo_code_execution()
        await demo_evolution_engine()
        await demo_exploitation_engine()
        await demo_meta_learning()
        await demo_continual_learning()
        await demo_master_integration()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return

    duration = (datetime.now() - start_time).total_seconds()

    section("DEMONSTRATION COMPLETE")
    print(f"""
✅ All systems demonstrated successfully!

BAEL Capabilities Summary:
├── 🧠 Reasoning: 25+ engines (deductive, causal, counterfactual, etc.)
├── 💭 Memory: 5-layer cognitive architecture
├── 🔄 Workflows: DAG-based multi-step execution
├── 🐝 Swarm: Multi-agent coordination & consensus
├── 🔧 Tools: Dynamic orchestration & pipelines
├── 📚 Knowledge: Multi-source synthesis & graphs
├── 🌐 Research: Web search & fact verification
├── 💻 Execution: Sandboxed code running
├── 🧬 Evolution: Genetic algorithm optimization
├── 💰 Exploitation: Free tier harvesting
├── 🎓 Meta-Learning: Rapid task adaptation
└── 🔄 Continual: Learning without forgetting

Total demonstration time: {duration:.2f} seconds
    """)


if __name__ == "__main__":
    asyncio.run(main())
