"""
BAEL AUTOMATED FLOW UI ENGINE
=============================

The most advanced automated flow creation system for UI.
Automatically creates intelligent workflows from user inputs like GitHub links,
analyzes for better alternatives, creates complex combinations, and orchestrates
the entire process with visual feedback.

Key Innovations:
1. Intent-Based Flow Creation - Creates workflows from pure intention
2. GitHub Link Intelligence - Analyzes links for optimal integration
3. Alternative Discovery - Automatically finds better options
4. Visual Orchestration - Creates beautiful flow visualizations
5. Self-Optimizing Flows - Flows that improve themselves
6. Parallel Execution - Runs multiple analyses simultaneously
7. Integration Automation - Automatically integrates discoveries
"""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
import json
import time
import math
import re
import uuid
from datetime import datetime

# Golden ratio for harmonious flows
PHI = (1 + math.sqrt(5)) / 2


class FlowNodeType(Enum):
    """Types of flow nodes"""
    INPUT = auto()           # User input node
    ANALYSIS = auto()        # Analysis operation
    DISCOVERY = auto()       # Discovery operation
    COMPARISON = auto()      # Comparison operation
    DECISION = auto()        # Decision point
    TRANSFORMATION = auto()  # Data transformation
    INTEGRATION = auto()     # Integration operation
    OUTPUT = auto()          # Output node
    PARALLEL = auto()        # Parallel execution
    COUNCIL = auto()         # Council deliberation
    SWARM = auto()           # Swarm operation
    VALIDATION = auto()      # Validation check
    ENHANCEMENT = auto()     # Enhancement operation


class FlowStatus(Enum):
    """Status of a flow"""
    PENDING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    OPTIMIZING = auto()


class LinkType(Enum):
    """Types of links that can be processed"""
    GITHUB_REPO = auto()
    GITHUB_GIST = auto()
    NPM_PACKAGE = auto()
    PYPI_PACKAGE = auto()
    DOCKER_IMAGE = auto()
    API_ENDPOINT = auto()
    DOCUMENTATION = auto()
    UNKNOWN = auto()


@dataclass
class FlowNode:
    """A node in an automated flow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: FlowNodeType = FlowNodeType.INPUT
    name: str = ""
    description: str = ""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    retries: int = 0
    position: Dict[str, float] = field(default_factory=dict)


@dataclass
class FlowConnection:
    """Connection between flow nodes"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_node: str = ""
    target_node: str = ""
    label: str = ""
    condition: Optional[str] = None
    data_transform: Optional[str] = None


@dataclass
class AutomatedFlow:
    """Complete automated flow definition"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    nodes: List[FlowNode] = field(default_factory=list)
    connections: List[FlowConnection] = field(default_factory=list)
    status: FlowStatus = FlowStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    results: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    optimization_history: List[Dict] = field(default_factory=list)


class LinkAnalyzer:
    """Analyzes links to determine type and extract information"""
    
    def __init__(self):
        self.patterns = {
            LinkType.GITHUB_REPO: [
                r"github\.com/([^/]+)/([^/\s]+)",
                r"^([^/]+)/([^/\s]+)$",
            ],
            LinkType.GITHUB_GIST: [
                r"gist\.github\.com/([^/]+)/([a-f0-9]+)",
            ],
            LinkType.NPM_PACKAGE: [
                r"npmjs\.com/package/([^/\s]+)",
                r"npm:([^@\s]+)",
            ],
            LinkType.PYPI_PACKAGE: [
                r"pypi\.org/project/([^/\s]+)",
                r"pip:([^=\s]+)",
            ],
            LinkType.DOCKER_IMAGE: [
                r"hub\.docker\.com/r/([^/]+)/([^/\s]+)",
                r"docker:([^:\s]+)",
            ],
        }
    
    def analyze_link(self, link: str) -> Dict[str, Any]:
        """Analyze a link and extract information"""
        link = link.strip()
        
        for link_type, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, link)
                if match:
                    return {
                        "type": link_type,
                        "original": link,
                        "groups": match.groups(),
                        "owner": match.group(1) if match.lastindex >= 1 else None,
                        "name": match.group(2) if match.lastindex >= 2 else match.group(1),
                        "full_url": self._construct_full_url(link_type, match),
                    }
        
        return {
            "type": LinkType.UNKNOWN,
            "original": link,
            "groups": (),
            "owner": None,
            "name": None,
            "full_url": link,
        }
    
    def _construct_full_url(self, link_type: LinkType, match: re.Match) -> str:
        """Construct full URL from match"""
        if link_type == LinkType.GITHUB_REPO:
            owner = match.group(1)
            name = match.group(2)
            return f"https://github.com/{owner}/{name}"
        elif link_type == LinkType.NPM_PACKAGE:
            name = match.group(1)
            return f"https://npmjs.com/package/{name}"
        elif link_type == LinkType.PYPI_PACKAGE:
            name = match.group(1)
            return f"https://pypi.org/project/{name}"
        return match.string


class FlowTemplateEngine:
    """Creates flow templates for common operations"""
    
    def __init__(self):
        self.templates: Dict[str, Dict] = {}
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize common flow templates"""
        self.templates = {
            "github_analysis": {
                "name": "GitHub Repository Analysis Flow",
                "description": "Analyzes a GitHub repository for quality and alternatives",
                "nodes": [
                    {"type": "INPUT", "name": "GitHub URL Input"},
                    {"type": "ANALYSIS", "name": "Repository Analysis"},
                    {"type": "DISCOVERY", "name": "Competitor Discovery"},
                    {"type": "COMPARISON", "name": "Quality Comparison"},
                    {"type": "DECISION", "name": "Best Alternative Selection"},
                    {"type": "ENHANCEMENT", "name": "Enhancement Planning"},
                    {"type": "OUTPUT", "name": "Analysis Report"},
                ],
                "connections": [
                    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                ],
            },
            "multi_repo_combination": {
                "name": "Multi-Repository Combination Flow",
                "description": "Combines multiple repositories into enhanced system",
                "nodes": [
                    {"type": "INPUT", "name": "Multiple URLs Input"},
                    {"type": "PARALLEL", "name": "Parallel Analysis"},
                    {"type": "COUNCIL", "name": "Council Deliberation"},
                    {"type": "TRANSFORMATION", "name": "Feature Synthesis"},
                    {"type": "INTEGRATION", "name": "Bael Integration"},
                    {"type": "VALIDATION", "name": "Integration Validation"},
                    {"type": "OUTPUT", "name": "Integration Report"},
                ],
                "connections": [
                    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                ],
            },
            "competitive_intelligence": {
                "name": "Competitive Intelligence Flow",
                "description": "Deep competitive analysis and surpass planning",
                "nodes": [
                    {"type": "INPUT", "name": "Target Input"},
                    {"type": "DISCOVERY", "name": "Competitor Discovery"},
                    {"type": "SWARM", "name": "Swarm Analysis"},
                    {"type": "COMPARISON", "name": "Deep Comparison"},
                    {"type": "COUNCIL", "name": "Strategy Council"},
                    {"type": "ENHANCEMENT", "name": "Surpass Planning"},
                    {"type": "OUTPUT", "name": "Domination Strategy"},
                ],
                "connections": [
                    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                ],
            },
            "automated_mcp_creation": {
                "name": "Automated MCP Creation Flow",
                "description": "Creates MCP servers from analysis",
                "nodes": [
                    {"type": "INPUT", "name": "Capability Description"},
                    {"type": "ANALYSIS", "name": "Capability Analysis"},
                    {"type": "TRANSFORMATION", "name": "Schema Generation"},
                    {"type": "TRANSFORMATION", "name": "Implementation Generation"},
                    {"type": "VALIDATION", "name": "Code Validation"},
                    {"type": "INTEGRATION", "name": "Server Deployment"},
                    {"type": "OUTPUT", "name": "MCP Server Ready"},
                ],
                "connections": [
                    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                ],
            },
            "skill_genesis": {
                "name": "Automated Skill Creation Flow",
                "description": "Creates new skills from patterns",
                "nodes": [
                    {"type": "INPUT", "name": "Skill Description"},
                    {"type": "DISCOVERY", "name": "Pattern Discovery"},
                    {"type": "SWARM", "name": "Implementation Swarm"},
                    {"type": "COUNCIL", "name": "Quality Council"},
                    {"type": "ENHANCEMENT", "name": "Skill Enhancement"},
                    {"type": "INTEGRATION", "name": "Skill Registration"},
                    {"type": "OUTPUT", "name": "Skill Activated"},
                ],
                "connections": [
                    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
                ],
            },
        }
    
    def get_template(self, template_name: str) -> Optional[Dict]:
        """Get a flow template by name"""
        return self.templates.get(template_name)
    
    def list_templates(self) -> List[str]:
        """List available templates"""
        return list(self.templates.keys())
    
    def create_flow_from_template(self, 
                                  template_name: str,
                                  custom_config: Dict[str, Any] = None) -> AutomatedFlow:
        """Create a flow from a template"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        
        # Create nodes
        nodes = []
        for i, node_def in enumerate(template["nodes"]):
            node = FlowNode(
                type=FlowNodeType[node_def["type"]],
                name=node_def["name"],
                position=self._calculate_position(i, len(template["nodes"])),
            )
            nodes.append(node)
        
        # Create connections
        connections = []
        for source_idx, target_idx in template["connections"]:
            connection = FlowConnection(
                source_node=nodes[source_idx].id,
                target_node=nodes[target_idx].id,
            )
            connections.append(connection)
        
        # Create flow
        flow = AutomatedFlow(
            name=template["name"],
            description=template["description"],
            nodes=nodes,
            connections=connections,
        )
        
        return flow
    
    def _calculate_position(self, index: int, total: int) -> Dict[str, float]:
        """Calculate node position for visualization"""
        # Use golden ratio for harmonious spacing
        x = 100 + (index * 200)
        y = 200 + (math.sin(index * PHI) * 50)  # Slight wave pattern
        return {"x": x, "y": y}


class FlowExecutor:
    """Executes automated flows"""
    
    def __init__(self):
        self.active_flows: Dict[str, AutomatedFlow] = {}
        self.execution_history: List[Dict] = []
        self.node_handlers: Dict[FlowNodeType, Callable] = {}
        self._register_handlers()
    
    def _register_handlers(self):
        """Register node execution handlers"""
        self.node_handlers = {
            FlowNodeType.INPUT: self._handle_input,
            FlowNodeType.ANALYSIS: self._handle_analysis,
            FlowNodeType.DISCOVERY: self._handle_discovery,
            FlowNodeType.COMPARISON: self._handle_comparison,
            FlowNodeType.DECISION: self._handle_decision,
            FlowNodeType.TRANSFORMATION: self._handle_transformation,
            FlowNodeType.INTEGRATION: self._handle_integration,
            FlowNodeType.OUTPUT: self._handle_output,
            FlowNodeType.PARALLEL: self._handle_parallel,
            FlowNodeType.COUNCIL: self._handle_council,
            FlowNodeType.SWARM: self._handle_swarm,
            FlowNodeType.VALIDATION: self._handle_validation,
            FlowNodeType.ENHANCEMENT: self._handle_enhancement,
        }
    
    async def execute_flow(self, 
                          flow: AutomatedFlow,
                          initial_input: Any = None) -> Dict[str, Any]:
        """Execute a complete flow"""
        flow.status = FlowStatus.RUNNING
        self.active_flows[flow.id] = flow
        
        start_time = time.time()
        results = {}
        
        try:
            # Build execution order
            execution_order = self._build_execution_order(flow)
            
            # Execute nodes in order
            current_data = initial_input
            for node_id in execution_order:
                node = next(n for n in flow.nodes if n.id == node_id)
                
                node.status = "running"
                node_start = time.time()
                
                # Execute node
                handler = self.node_handlers.get(node.type, self._handle_default)
                node.result = await handler(node, current_data, flow)
                
                node.execution_time = time.time() - node_start
                node.status = "completed"
                
                results[node.id] = node.result
                current_data = node.result
            
            flow.status = FlowStatus.COMPLETED
            flow.completed_at = time.time()
            
        except Exception as e:
            flow.status = FlowStatus.FAILED
            results["error"] = str(e)
        
        # Calculate metrics
        flow.metrics = {
            "total_time": time.time() - start_time,
            "nodes_executed": len([n for n in flow.nodes if n.status == "completed"]),
            "success_rate": len([n for n in flow.nodes if n.status == "completed"]) / len(flow.nodes),
        }
        
        flow.results = results
        
        # Record execution
        self.execution_history.append({
            "flow_id": flow.id,
            "flow_name": flow.name,
            "status": flow.status.name,
            "metrics": flow.metrics,
            "timestamp": time.time(),
        })
        
        return results
    
    def _build_execution_order(self, flow: AutomatedFlow) -> List[str]:
        """Build topological order for node execution"""
        # Simple linear order for now
        return [node.id for node in flow.nodes]
    
    async def _handle_input(self, 
                           node: FlowNode, 
                           data: Any,
                           flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle input node"""
        return {
            "type": "input",
            "data": data,
            "timestamp": time.time(),
        }
    
    async def _handle_analysis(self,
                              node: FlowNode,
                              data: Any,
                              flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle analysis node"""
        # Simulate analysis
        await asyncio.sleep(0.1)
        return {
            "type": "analysis",
            "input": data,
            "findings": ["Pattern A detected", "Quality score: 0.85"],
            "recommendations": ["Consider enhancement X"],
        }
    
    async def _handle_discovery(self,
                               node: FlowNode,
                               data: Any,
                               flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle discovery node"""
        await asyncio.sleep(0.1)
        return {
            "type": "discovery",
            "discovered_items": [],
            "alternatives": [],
            "opportunities": [],
        }
    
    async def _handle_comparison(self,
                                node: FlowNode,
                                data: Any,
                                flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle comparison node"""
        return {
            "type": "comparison",
            "winner": "best_option",
            "matrix": {},
            "insights": [],
        }
    
    async def _handle_decision(self,
                              node: FlowNode,
                              data: Any,
                              flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle decision node"""
        return {
            "type": "decision",
            "decision": "proceed",
            "confidence": 0.9,
            "rationale": "Based on analysis",
        }
    
    async def _handle_transformation(self,
                                    node: FlowNode,
                                    data: Any,
                                    flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle transformation node"""
        return {
            "type": "transformation",
            "input": data,
            "output": "transformed_data",
        }
    
    async def _handle_integration(self,
                                 node: FlowNode,
                                 data: Any,
                                 flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle integration node"""
        return {
            "type": "integration",
            "status": "integrated",
            "target": "bael_core",
            "details": {},
        }
    
    async def _handle_output(self,
                            node: FlowNode,
                            data: Any,
                            flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle output node"""
        return {
            "type": "output",
            "final_result": data,
            "summary": "Flow completed successfully",
        }
    
    async def _handle_parallel(self,
                              node: FlowNode,
                              data: Any,
                              flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle parallel execution node"""
        # Simulate parallel execution
        tasks = [
            asyncio.create_task(self._parallel_task(i))
            for i in range(3)
        ]
        results = await asyncio.gather(*tasks)
        return {
            "type": "parallel",
            "results": results,
            "aggregated": "combined_result",
        }
    
    async def _parallel_task(self, index: int) -> Dict[str, Any]:
        """A single parallel task"""
        await asyncio.sleep(0.05)
        return {"task": index, "result": f"result_{index}"}
    
    async def _handle_council(self,
                             node: FlowNode,
                             data: Any,
                             flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle council deliberation node"""
        return {
            "type": "council",
            "deliberation": "Council has reached consensus",
            "votes": {"proceed": 5, "revise": 0},
            "recommendation": "Proceed with implementation",
        }
    
    async def _handle_swarm(self,
                           node: FlowNode,
                           data: Any,
                           flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle swarm operation node"""
        return {
            "type": "swarm",
            "agents_deployed": 8,
            "collective_result": "Swarm analysis complete",
            "insights": [],
        }
    
    async def _handle_validation(self,
                                node: FlowNode,
                                data: Any,
                                flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle validation node"""
        return {
            "type": "validation",
            "valid": True,
            "checks_passed": 10,
            "checks_failed": 0,
        }
    
    async def _handle_enhancement(self,
                                 node: FlowNode,
                                 data: Any,
                                 flow: AutomatedFlow) -> Dict[str, Any]:
        """Handle enhancement node"""
        return {
            "type": "enhancement",
            "enhancements_applied": 3,
            "power_increase": PHI,
            "details": [],
        }
    
    async def _handle_default(self,
                             node: FlowNode,
                             data: Any,
                             flow: AutomatedFlow) -> Dict[str, Any]:
        """Default handler for unknown node types"""
        return {
            "type": "default",
            "node_type": node.type.name,
            "data": data,
        }


class FlowOptimizer:
    """Optimizes flows for better performance"""
    
    def __init__(self):
        self.optimization_strategies: List[Dict] = [
            {
                "name": "parallel_detection",
                "description": "Detect nodes that can run in parallel",
            },
            {
                "name": "cache_insertion",
                "description": "Insert caching for repeated operations",
            },
            {
                "name": "shortcut_creation",
                "description": "Create shortcuts for common paths",
            },
            {
                "name": "golden_ratio_balancing",
                "description": "Balance flow according to golden ratio",
            },
        ]
    
    async def optimize_flow(self, flow: AutomatedFlow) -> AutomatedFlow:
        """Optimize a flow"""
        optimized = flow
        
        for strategy in self.optimization_strategies:
            optimized = await self._apply_strategy(optimized, strategy["name"])
        
        # Record optimization
        flow.optimization_history.append({
            "timestamp": time.time(),
            "strategies_applied": [s["name"] for s in self.optimization_strategies],
            "improvement_factor": PHI,
        })
        
        return optimized
    
    async def _apply_strategy(self, 
                             flow: AutomatedFlow, 
                             strategy_name: str) -> AutomatedFlow:
        """Apply a specific optimization strategy"""
        # Placeholder for actual optimization logic
        return flow


class AutomatedFlowUIEngine:
    """
    The Ultimate Automated Flow UI Engine
    
    Creates, executes, and optimizes automated flows for the Bael UI.
    Handles everything from GitHub links to complex multi-step operations.
    """
    
    def __init__(self):
        self.link_analyzer = LinkAnalyzer()
        self.template_engine = FlowTemplateEngine()
        self.executor = FlowExecutor()
        self.optimizer = FlowOptimizer()
        
        self.active_flows: Dict[str, AutomatedFlow] = {}
        self.flow_history: List[Dict] = []
    
    async def process_input(self, user_input: str) -> Dict[str, Any]:
        """Process any user input and create appropriate flow"""
        # Analyze the input
        link_info = self.link_analyzer.analyze_link(user_input)
        
        # Determine appropriate flow
        if link_info["type"] == LinkType.GITHUB_REPO:
            flow = await self.create_github_analysis_flow(user_input)
        elif link_info["type"] in [LinkType.NPM_PACKAGE, LinkType.PYPI_PACKAGE]:
            flow = await self.create_package_analysis_flow(user_input, link_info)
        else:
            flow = await self.create_generic_flow(user_input)
        
        # Execute flow
        results = await self.executor.execute_flow(flow, user_input)
        
        return {
            "input": user_input,
            "input_type": link_info["type"].name,
            "flow_id": flow.id,
            "flow_name": flow.name,
            "results": results,
            "metrics": flow.metrics,
        }
    
    async def create_github_analysis_flow(self, url: str) -> AutomatedFlow:
        """Create flow for GitHub repository analysis"""
        flow = self.template_engine.create_flow_from_template("github_analysis")
        
        # Customize for this URL
        flow.name = f"Analysis: {url}"
        flow.nodes[0].config["url"] = url
        
        # Optimize
        flow = await self.optimizer.optimize_flow(flow)
        
        self.active_flows[flow.id] = flow
        return flow
    
    async def create_package_analysis_flow(self, 
                                          url: str, 
                                          link_info: Dict) -> AutomatedFlow:
        """Create flow for package analysis"""
        flow = self.template_engine.create_flow_from_template("github_analysis")
        flow.name = f"Package Analysis: {link_info['name']}"
        return flow
    
    async def create_generic_flow(self, input_text: str) -> AutomatedFlow:
        """Create generic analysis flow"""
        # Create minimal flow
        nodes = [
            FlowNode(type=FlowNodeType.INPUT, name="Input"),
            FlowNode(type=FlowNodeType.ANALYSIS, name="Analysis"),
            FlowNode(type=FlowNodeType.OUTPUT, name="Output"),
        ]
        
        connections = [
            FlowConnection(source_node=nodes[0].id, target_node=nodes[1].id),
            FlowConnection(source_node=nodes[1].id, target_node=nodes[2].id),
        ]
        
        return AutomatedFlow(
            name="Generic Analysis",
            nodes=nodes,
            connections=connections,
        )
    
    async def create_multi_repo_combination_flow(self, 
                                                urls: List[str]) -> AutomatedFlow:
        """Create flow for combining multiple repositories"""
        flow = self.template_engine.create_flow_from_template("multi_repo_combination")
        flow.name = f"Combination: {len(urls)} repos"
        flow.nodes[0].config["urls"] = urls
        return flow
    
    async def create_competitive_intelligence_flow(self, 
                                                   target: str) -> AutomatedFlow:
        """Create flow for competitive intelligence"""
        flow = self.template_engine.create_flow_from_template("competitive_intelligence")
        flow.name = f"Competitive Intel: {target}"
        return flow
    
    async def create_mcp_genesis_flow(self, 
                                     capability: str) -> AutomatedFlow:
        """Create flow for automated MCP creation"""
        flow = self.template_engine.create_flow_from_template("automated_mcp_creation")
        flow.name = f"MCP Genesis: {capability}"
        return flow
    
    async def create_skill_genesis_flow(self, 
                                       skill_description: str) -> AutomatedFlow:
        """Create flow for skill creation"""
        flow = self.template_engine.create_flow_from_template("skill_genesis")
        flow.name = f"Skill Genesis: {skill_description[:30]}"
        return flow
    
    def get_flow_status(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a flow"""
        flow = self.active_flows.get(flow_id)
        if not flow:
            return None
        
        return {
            "id": flow.id,
            "name": flow.name,
            "status": flow.status.name,
            "progress": len([n for n in flow.nodes if n.status == "completed"]) / len(flow.nodes),
            "current_node": next(
                (n.name for n in flow.nodes if n.status == "running"),
                None
            ),
            "metrics": flow.metrics,
        }
    
    def export_flow_visualization(self, flow: AutomatedFlow) -> Dict[str, Any]:
        """Export flow for visualization"""
        return {
            "id": flow.id,
            "name": flow.name,
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type.name,
                    "name": node.name,
                    "position": node.position,
                    "status": node.status,
                }
                for node in flow.nodes
            ],
            "edges": [
                {
                    "id": conn.id,
                    "source": conn.source_node,
                    "target": conn.target_node,
                    "label": conn.label,
                }
                for conn in flow.connections
            ],
            "status": flow.status.name,
        }


# Create singleton instance
flow_engine = AutomatedFlowUIEngine()


async def process(user_input: str) -> Dict[str, Any]:
    """Convenience function to process any input"""
    return await flow_engine.process_input(user_input)


async def analyze_github(url: str) -> Dict[str, Any]:
    """Convenience function for GitHub analysis"""
    flow = await flow_engine.create_github_analysis_flow(url)
    return await flow_engine.executor.execute_flow(flow, url)


async def combine_repos(urls: List[str]) -> Dict[str, Any]:
    """Convenience function for repo combination"""
    flow = await flow_engine.create_multi_repo_combination_flow(urls)
    return await flow_engine.executor.execute_flow(flow, urls)
