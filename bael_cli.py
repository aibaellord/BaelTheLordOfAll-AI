"""
BAEL Unified CLI
================

Unified command-line interface for all BAEL capabilities.

"One command to rule them all." — Ba'el
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def print_banner():
    """Print BAEL banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║    ██████╗  █████╗ ███████╗██╗         ██╗   ██╗██████╗              ║
║    ██╔══██╗██╔══██╗██╔════╝██║         ██║   ██║╚════██╗             ║
║    ██████╔╝███████║█████╗  ██║         ██║   ██║ █████╔╝             ║
║    ██╔══██╗██╔══██║██╔══╝  ██║         ╚██╗ ██╔╝ ╚═══██╗             ║
║    ██████╔╝██║  ██║███████╗███████╗     ╚████╔╝ ██████╔╝             ║
║    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝      ╚═══╝  ╚═════╝              ║
║                                                                       ║
║                    THE LORD OF ALL AI AGENTS                          ║
║                                                                       ║
║  500+ Modules • 25+ Reasoning Engines • 5-Layer Memory • 8 Levels    ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_status(title: str, items: Dict[str, Any], color: bool = True):
    """Print status information."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

    for key, value in items.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        elif isinstance(value, list):
            print(f"  {key}: {len(value)} items")
            for item in value[:5]:
                print(f"    - {item}")
            if len(value) > 5:
                print(f"    ... and {len(value) - 5} more")
        else:
            print(f"  {key}: {value}")


async def cmd_status(args):
    """Show system status."""
    print_banner()

    status = {
        "mode": "MAXIMUM",
        "uptime": "Ready",
        "timestamp": datetime.now().isoformat()
    }

    # Check available modules
    modules = {
        "self_healing": False,
        "maximum_power": False,
        "advanced_intelligence": False,
        "predictive_engine": False,
        "nlu_engine": False,
        "codegen_engine": False,
        "security_engine": False,
        "master_orchestrator": False
    }

    try:
        from core.self_healing import self_healing_system
        modules["self_healing"] = True
    except ImportError:
        pass

    try:
        from core.maximum_power import quantum_optimizer, nas, swarm, meta_learner
        modules["maximum_power"] = True
    except ImportError:
        pass

    try:
        from core.advanced_intelligence import knowledge_engine, cognitive_engine
        modules["advanced_intelligence"] = True
    except ImportError:
        pass

    try:
        from core.predictive_engine import predictive_engine
        modules["predictive_engine"] = True
    except ImportError:
        pass

    try:
        from core.nlu_engine import nlu_engine
        modules["nlu_engine"] = True
    except ImportError:
        pass

    try:
        from core.codegen_engine import codegen_engine
        modules["codegen_engine"] = True
    except ImportError:
        pass

    try:
        from core.security_engine import security_engine
        modules["security_engine"] = True
    except ImportError:
        pass

    try:
        from core.master_orchestrator import UltimateMasterOrchestrator
        modules["master_orchestrator"] = True
    except ImportError:
        pass

    active = sum(1 for v in modules.values() if v)
    total = len(modules)

    print_status("System Status", status)
    print_status("Module Status", {
        "active": f"{active}/{total}",
        "modules": {k: "✓" if v else "✗" for k, v in modules.items()}
    })

    # Calculate capabilities
    capabilities = []
    if modules["self_healing"]:
        capabilities.extend(["error_recovery", "auto_scaling", "improvement"])
    if modules["maximum_power"]:
        capabilities.extend(["quantum_optimization", "neural_architecture_search", "swarm_intelligence", "meta_learning"])
    if modules["advanced_intelligence"]:
        capabilities.extend(["knowledge_fusion", "cognitive_reasoning", "multimodal_processing", "distributed_computing"])
    if modules["predictive_engine"]:
        capabilities.extend(["time_series_forecasting", "anomaly_detection", "causal_inference"])
    if modules["nlu_engine"]:
        capabilities.extend(["entity_extraction", "intent_classification", "sentiment_analysis", "summarization"])
    if modules["codegen_engine"]:
        capabilities.extend(["code_generation", "pattern_generation", "test_generation"])
    if modules["security_engine"]:
        capabilities.extend(["encryption", "vulnerability_scanning", "token_management"])

    print_status("Capabilities", {
        "total": len(capabilities),
        "list": capabilities
    })


async def cmd_think(args):
    """Execute thinking operation."""
    from core.master_orchestrator import create_master, MasterMode

    mode = MasterMode.MAXIMUM if args.mode == "maximum" else MasterMode.STANDARD
    master = await create_master(mode)

    print(f"\n🧠 Thinking about: {args.query}")
    print("-" * 50)

    result = await master.think(args.query, depth=args.depth)

    if result.success:
        print(f"✓ Success (took {result.duration_ms:.1f}ms)")
        print(f"\nSystems used: {', '.join(result.systems_used)}")
        print(f"\nResult:")
        print(json.dumps(result.result, indent=2))
    else:
        print(f"✗ Failed: {result.error}")


async def cmd_analyze(args):
    """Analyze content."""
    from core.master_orchestrator import create_master, MasterMode

    master = await create_master(MasterMode.MAXIMUM)

    # Read content from file or use provided string
    if args.file:
        content = Path(args.file).read_text()
    else:
        content = args.content

    print(f"\n📊 Analyzing content...")
    print("-" * 50)

    result = await master.analyze(content, args.modality)

    if result.success:
        print(f"✓ Analysis complete (took {result.duration_ms:.1f}ms)")
        print(json.dumps(result.result, indent=2))
    else:
        print(f"✗ Failed: {result.error}")


async def cmd_generate(args):
    """Generate code."""
    from core.codegen_engine import (
        CodeGenerationEngine, CodeSpec, Language, ComponentType
    )

    engine = CodeGenerationEngine()

    # Parse language
    try:
        language = Language(args.language.lower())
    except ValueError:
        language = Language.PYTHON

    # Parse component type
    try:
        component = ComponentType(args.type.lower())
    except ValueError:
        component = ComponentType.FUNCTION

    spec = CodeSpec(
        name=args.name,
        language=language,
        component_type=component,
        description=args.description or f"Generated {args.type}",
        inputs=[
            {"name": p.split(":")[0], "type": p.split(":")[1] if ":" in p else "Any"}
            for p in (args.params or [])
        ]
    )

    print(f"\n💻 Generating {args.type}...")
    print("-" * 50)

    result = await engine.generate(spec)

    print(f"\n{result.code}")

    if args.output:
        Path(args.output).write_text(result.code)
        print(f"\n✓ Saved to {args.output}")


async def cmd_scan(args):
    """Security scan."""
    from core.security_engine import SecurityEngine

    engine = SecurityEngine()

    # Read content
    if args.file:
        content = Path(args.file).read_text()
        content_type = "code"
    else:
        content = args.content
        content_type = args.type or "input"

    print(f"\n🔒 Security scan...")
    print("-" * 50)

    report = await engine.scan(content, content_type)

    print(f"\nResult: {report.result.value.upper()}")
    print(f"Score: {report.score:.1f}/100")
    print(f"Vulnerabilities: {len(report.vulnerabilities)}")

    if report.vulnerabilities:
        print("\nVulnerabilities found:")
        for v in report.vulnerabilities:
            print(f"  - [{v.severity.name}] {v.threat_type.value}: {v.description}")
            print(f"    Location: {v.location}")
            print(f"    Recommendation: {v.recommendation}")

    if report.recommendations:
        print("\nRecommendations:")
        for r in report.recommendations:
            print(f"  • {r}")


async def cmd_predict(args):
    """Make predictions."""
    from core.predictive_engine import PredictiveAnalyticsEngine, TimeSeries
    from datetime import datetime, timedelta

    engine = PredictiveAnalyticsEngine()

    # Create sample data if not provided
    if args.data:
        data = json.loads(Path(args.data).read_text())
    else:
        # Generate sample data
        base_time = datetime.now() - timedelta(hours=24)
        data = [
            (base_time + timedelta(hours=i), 100 + i * 2 + (i % 3) * 5)
            for i in range(24)
        ]

    series_name = args.name or "sample_series"
    await engine.ingest_series(series_name, data)

    print(f"\n📈 Forecasting...")
    print("-" * 50)

    forecast = await engine.forecast(series_name, horizon=args.horizon)

    print(f"\nForecast ({forecast.model_type.value}):")
    for i, pred in enumerate(forecast.predictions, 1):
        interval = f" [{pred.interval[0]:.2f}, {pred.interval[1]:.2f}]" if pred.interval else ""
        print(f"  +{i}: {pred.predicted_value:.2f} (conf: {pred.confidence:.2f}){interval}")


async def cmd_nlu(args):
    """Natural Language Understanding."""
    from core.nlu_engine import NLUEngine

    engine = NLUEngine()

    print(f"\n📝 Analyzing: {args.text}")
    print("-" * 50)

    doc = await engine.process(args.text)

    print(f"\nSentences: {len(doc.sentences)}")

    if doc.overall_sentiment:
        print(f"Sentiment: {doc.overall_sentiment.sentiment.value} (score: {doc.overall_sentiment.score:.2f})")

    if doc.entities:
        print(f"\nEntities found:")
        for e in doc.entities:
            print(f"  - {e.text} ({e.entity_type.value})")

    if doc.keywords:
        print(f"\nKeywords:")
        for kw, score in doc.keywords[:10]:
            print(f"  - {kw} ({score:.3f})")

    for sent in doc.sentences:
        if sent.intent:
            print(f"\nIntent: {sent.intent.intent_type.value}")
            if sent.intent.action:
                print(f"Action: {sent.intent.action}")


async def cmd_interactive(args):
    """Interactive mode."""
    print_banner()
    print("\n🎮 Interactive Mode")
    print("Type 'help' for commands, 'exit' to quit\n")

    from core.master_orchestrator import create_master, MasterMode
    master = await create_master(MasterMode.MAXIMUM)

    while True:
        try:
            user_input = input("BAEL> ").strip()

            if not user_input:
                continue

            if user_input.lower() == "exit":
                print("Farewell, Lord of All.")
                break

            if user_input.lower() == "help":
                print("""
Commands:
  think <query>     - Deep thinking about a topic
  analyze <text>    - Analyze content
  status            - Show system status
  exit              - Exit interactive mode

Or just type anything to get an AI response.
""")
                continue

            if user_input.lower() == "status":
                status = await master.get_status()
                print(json.dumps(status, indent=2))
                continue

            if user_input.lower().startswith("think "):
                query = user_input[6:]
                result = await master.think(query)
                if result.success:
                    print(json.dumps(result.result, indent=2))
                else:
                    print(f"Error: {result.error}")
                continue

            # Default: think about the input
            result = await master.think(user_input)
            if result.success:
                if result.result.get("cognitive_insight"):
                    print(f"\n{result.result['cognitive_insight']}")
                else:
                    print(json.dumps(result.result, indent=2))
            else:
                print(f"Error: {result.error}")

        except KeyboardInterrupt:
            print("\n\nFarewell, Lord of All.")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BAEL - The Lord of All AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bael status                       # Show system status
  bael think "How does X work?"     # Deep thinking
  bael analyze --file code.py       # Analyze code
  bael generate --name MyClass --type class
  bael scan --file code.py          # Security scan
  bael interactive                  # Interactive mode
"""
    )

    parser.add_argument("--version", action="version", version="BAEL v3.0 - Lord of All Edition")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")

    # Think command
    think_parser = subparsers.add_parser("think", help="Deep thinking operation")
    think_parser.add_argument("query", help="Query to think about")
    think_parser.add_argument("--depth", type=int, default=3, help="Thinking depth")
    think_parser.add_argument("--mode", default="maximum", choices=["standard", "maximum"])

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze content")
    analyze_parser.add_argument("--content", help="Content to analyze")
    analyze_parser.add_argument("--file", help="File to analyze")
    analyze_parser.add_argument("--modality", help="Content modality hint")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate code")
    gen_parser.add_argument("--name", required=True, help="Name of the component")
    gen_parser.add_argument("--type", default="function", help="Component type")
    gen_parser.add_argument("--language", default="python", help="Programming language")
    gen_parser.add_argument("--description", help="Description")
    gen_parser.add_argument("--params", nargs="*", help="Parameters (name:type)")
    gen_parser.add_argument("--output", help="Output file")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Security scan")
    scan_parser.add_argument("--content", help="Content to scan")
    scan_parser.add_argument("--file", help="File to scan")
    scan_parser.add_argument("--type", default="input", help="Content type")

    # Predict command
    predict_parser = subparsers.add_parser("predict", help="Make predictions")
    predict_parser.add_argument("--name", help="Series name")
    predict_parser.add_argument("--data", help="Data file (JSON)")
    predict_parser.add_argument("--horizon", type=int, default=5, help="Forecast horizon")

    # NLU command
    nlu_parser = subparsers.add_parser("nlu", help="Natural Language Understanding")
    nlu_parser.add_argument("text", help="Text to analyze")

    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Interactive mode")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Run command
    cmd_map = {
        "status": cmd_status,
        "think": cmd_think,
        "analyze": cmd_analyze,
        "generate": cmd_generate,
        "scan": cmd_scan,
        "predict": cmd_predict,
        "nlu": cmd_nlu,
        "interactive": cmd_interactive
    }

    cmd_func = cmd_map.get(args.command)
    if cmd_func:
        asyncio.run(cmd_func(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
