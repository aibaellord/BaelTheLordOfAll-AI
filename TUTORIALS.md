# BAEL - Tutorials

Step-by-step tutorials for common BAEL use cases. Each tutorial is designed to be completed in 15-60 minutes.

## Table of Contents

1. [Hello BAEL - Your First Agent](#tutorial-1-hello-bael---your-first-agent)
2. [Building a Research Assistant](#tutorial-2-building-a-research-assistant)
3. [Creating Custom Skills](#tutorial-3-creating-custom-skills)
4. [Multi-Agent Collaboration](#tutorial-4-multi-agent-collaboration)
5. [Persistent Long-Running Agents](#tutorial-5-persistent-long-running-agents)
6. [Building a Custom Plugin](#tutorial-6-building-a-custom-plugin)
7. [Integrating BAEL with Your App](#tutorial-7-integrating-bael-with-your-app)
8. [Production Deployment](#tutorial-8-production-deployment)

---

## Tutorial 1: Hello BAEL - Your First Agent

**Time**: 15 minutes  
**Level**: Beginner  
**Goal**: Create and interact with your first BAEL agent

### Prerequisites

- BAEL installed and running
- Python 3.10+
- API key configured

### Steps

#### 1. Start BAEL

```bash
cd /path/to/BaelTheLordOfAll-AI
python main.py
```

Wait for: "BAEL is ready!"

#### 2. Create Your First Agent (Python API)

Create `tutorial_1.py`:

```python
import asyncio
from core.agents import create_agent
from core.brain import get_brain


async def main():
    """Create and interact with your first agent."""
    
    # Get the BAEL brain
    brain = get_brain()
    
    # Create an agent
    agent = await create_agent(
        name="my_first_agent",
        persona="code_master",  # Use the Code Master persona
        mission="Help with Python coding"
    )
    
    print(f"Created agent: {agent.name}")
    print(f"Agent ID: {agent.agent_id}")
    
    # Send a request to the agent
    response = await agent.process(
        "Write a Python function to calculate fibonacci numbers"
    )
    
    print("\nAgent Response:")
    print(response.content)
    
    # Ask a follow-up question
    response = await agent.process(
        "Now optimize it using memoization"
    )
    
    print("\nOptimized Version:")
    print(response.content)
    
    # Get agent's memory
    memories = await agent.get_memories(limit=5)
    print(f"\nAgent has {len(memories)} memories")


if __name__ == "__main__":
    asyncio.run(main())
```

#### 3. Run Your Agent

```bash
python tutorial_1.py
```

#### 4. Using the CLI

Alternatively, use the command-line interface:

```bash
# Ask BAEL a question
python cli.py "Write a Python function to calculate fibonacci numbers"

# Interactive mode
python cli.py --interactive

# Use specific persona
python cli.py --persona code_master "Review this code: def fib(n): return n"
```

#### 5. Using the Web UI

1. Open http://localhost:7777
2. Click "Create Agent"
3. Select "Code Master" persona
4. Enter your request
5. Watch BAEL work!

### What You Learned

✅ How to create an agent  
✅ How to send requests to agents  
✅ How agent memory works  
✅ Different ways to interact with BAEL

### Next Steps

- Try different personas
- Explore agent capabilities
- Check agent memory and history

---

## Tutorial 2: Building a Research Assistant

**Time**: 30 minutes  
**Level**: Intermediate  
**Goal**: Build an agent that researches topics and produces reports

### Overview

Create an autonomous research assistant that:
- Searches multiple sources
- Synthesizes information
- Produces structured reports
- Remembers past research

### Implementation

Create `research_assistant.py`:

```python
import asyncio
from core.agents import create_agent
from core.tools import get_tool_manager
from datetime import datetime, timezone


async def create_research_agent():
    """Create a specialized research agent."""
    
    # Create agent with Research Oracle persona
    agent = await create_agent(
        name="research_assistant",
        persona="research_oracle",
        mission="Conduct thorough research and produce comprehensive reports",
        capabilities=[
            "web_search",
            "document_analysis",
            "synthesis",
            "citation_tracking"
        ]
    )
    
    # Configure research parameters
    agent.config.update({
        "search_depth": "thorough",  # vs "quick"
        "source_verification": True,
        "citation_format": "apa",
        "min_sources": 5
    })
    
    return agent


async def research_topic(agent, topic: str, depth: str = "thorough"):
    """Research a topic and produce a report."""
    
    print(f"\n{'='*60}")
    print(f"Researching: {topic}")
    print(f"Depth: {depth}")
    print(f"{'='*60}\n")
    
    # Create research prompt
    prompt = f"""
    Research the following topic and produce a comprehensive report:
    
    Topic: {topic}
    
    Requirements:
    - Search multiple reliable sources
    - Verify information accuracy
    - Include citations
    - Provide balanced perspective
    - Structure with clear sections
    - Include key findings summary
    
    Depth: {depth}
    """
    
    # Execute research
    response = await agent.process(prompt)
    
    # Save report
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"research_report_{timestamp}.md"
    
    with open(filename, "w") as f:
        f.write(f"# Research Report: {topic}\n\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")
        f.write(response.content)
    
    print(f"\nReport saved to: {filename}")
    
    return response


async def multi_topic_research(topics: list):
    """Research multiple related topics."""
    
    agent = await create_research_agent()
    
    reports = {}
    
    for topic in topics:
        report = await research_topic(agent, topic)
        reports[topic] = report
        
        # Brief pause between topics
        await asyncio.sleep(2)
    
    # Create synthesis
    synthesis_prompt = f"""
    I've researched these topics:
    {', '.join(topics)}
    
    Create a synthesis that:
    - Identifies common themes
    - Highlights contradictions
    - Shows relationships between topics
    - Provides integrated insights
    """
    
    synthesis = await agent.process(synthesis_prompt)
    
    # Save synthesis
    with open("research_synthesis.md", "w") as f:
        f.write("# Research Synthesis\n\n")
        f.write(f"Topics: {', '.join(topics)}\n\n")
        f.write(synthesis.content)
    
    print("\nSynthesis saved to: research_synthesis.md")
    
    return reports, synthesis


async def main():
    """Main research workflow."""
    
    # Single topic research
    agent = await create_research_agent()
    
    await research_topic(
        agent,
        "Latest developments in quantum computing",
        depth="thorough"
    )
    
    # Multi-topic research
    topics = [
        "Quantum computing applications",
        "Quantum encryption",
        "Quantum computing challenges"
    ]
    
    reports, synthesis = await multi_topic_research(topics)
    
    print("\n✅ Research complete!")
    print(f"Generated {len(reports)} reports + synthesis")


if __name__ == "__main__":
    asyncio.run(main())
```

### Running the Research Assistant

```bash
python research_assistant.py
```

### Advanced Features

Add scheduling for regular research:

```python
from core.workflows import create_workflow

# Create scheduled research workflow
workflow = await create_workflow(
    name="daily_tech_research",
    schedule="0 9 * * *",  # 9 AM daily
    tasks=[
        {
            "type": "research",
            "topic": "Latest AI developments",
            "depth": "quick"
        },
        {
            "type": "synthesis",
            "summarize": True
        },
        {
            "type": "notify",
            "channels": ["email", "slack"]
        }
    ]
)
```

### What You Learned

✅ Creating specialized agents  
✅ Configuring agent capabilities  
✅ Multi-step workflows  
✅ Saving and synthesizing results  

---

## Tutorial 3: Creating Custom Skills

**Time**: 25 minutes  
**Level**: Intermediate  
**Goal**: Use Skill Genesis to create custom capabilities

### Understanding Skill Genesis

BAEL's Skill Genesis system creates new skills from natural language descriptions using:
- DNA-based skill encoding
- Evolutionary optimization
- Automatic testing
- Self-improvement

### Creating Your First Skill

Create `skill_creation.py`:

```python
import asyncio
from core.skills import get_skill_genesis


async def create_custom_skill():
    """Create a custom skill using Skill Genesis."""
    
    genesis = get_skill_genesis()
    
    # Define the skill you want
    skill_description = """
    Create a skill that analyzes GitHub repositories:
    - Clone the repository
    - Analyze code quality
    - Count lines of code by language
    - Identify dependencies
    - Check for security issues
    - Generate a comprehensive report
    
    Input: GitHub repository URL
    Output: Analysis report in JSON format
    """
    
    print("Creating skill from description...")
    print(f"Description: {skill_description}\n")
    
    # Let BAEL create the skill
    skill = await genesis.create_skill(
        description=skill_description,
        name="github_analyzer",
        optimize=True,  # Optimize through evolution
        generate_tests=True  # Auto-generate tests
    )
    
    print(f"✅ Created skill: {skill.name}")
    print(f"Skill ID: {skill.skill_id}")
    print(f"DNA: {skill.dna[:50]}...")  # First 50 chars of DNA
    
    return skill


async def use_custom_skill(skill):
    """Use the newly created skill."""
    
    # Test the skill
    result = await skill.execute(
        repository_url="https://github.com/python/cpython"
    )
    
    print("\nAnalysis Result:")
    print(json.dumps(result, indent=2))
    
    return result


async def evolve_skill(skill):
    """Improve skill through evolution."""
    
    genesis = get_skill_genesis()
    
    # Define improvement goals
    improvements = """
    Improve this skill to also:
    - Detect code smells
    - Calculate complexity metrics
    - Identify dead code
    - Suggest refactoring opportunities
    """
    
    print("\nEvolving skill...")
    
    # Evolve the skill
    evolved_skill = await genesis.evolve_skill(
        skill=skill,
        goals=improvements,
        generations=5  # Run 5 generations of evolution
    )
    
    print(f"✅ Evolved skill")
    print(f"Fitness improvement: {evolved_skill.fitness - skill.fitness:.2f}")
    
    return evolved_skill


async def create_meta_skill():
    """Create a skill that creates other skills."""
    
    genesis = get_skill_genesis()
    
    meta_skill_description = """
    Create a meta-skill that can create data analysis skills:
    - Takes a data analysis task description
    - Determines required operations (filter, aggregate, visualize, etc.)
    - Generates a custom skill for that specific analysis
    - Returns the executable skill
    
    This is a skill that creates skills!
    """
    
    meta_skill = await genesis.create_meta_skill(
        description=meta_skill_description,
        name="data_analysis_skill_creator"
    )
    
    print(f"✅ Created meta-skill: {meta_skill.name}")
    
    # Use the meta-skill to create a specific skill
    analysis_skill = await meta_skill.execute(
        task="Analyze CSV files and create correlation heatmaps"
    )
    
    print(f"✅ Meta-skill created: {analysis_skill.name}")
    
    return meta_skill, analysis_skill


async def main():
    """Main skill creation workflow."""
    
    # 1. Create a custom skill
    skill = await create_custom_skill()
    
    # 2. Use the skill
    await use_custom_skill(skill)
    
    # 3. Evolve the skill
    evolved = await evolve_skill(skill)
    
    # 4. Create meta-skill
    meta_skill, child_skill = await create_meta_skill()
    
    print("\n✅ Tutorial complete!")
    print("You've learned to create, use, and evolve skills!")


if __name__ == "__main__":
    asyncio.run(main())
```

### Skill DNA and Evolution

Skills are encoded as DNA strings that can:
- **Inherit** - Combine traits from parent skills
- **Mutate** - Random improvements
- **Crossover** - Merge two skills

```python
# Crossover two skills
from core.skills import crossover_skills

parent1 = await genesis.get_skill("web_scraper")
parent2 = await genesis.get_skill("data_parser")

# Create hybrid skill
child = await crossover_skills(parent1, parent2)
# Result: A skill that scrapes and parses data
```

### What You Learned

✅ Creating skills from descriptions  
✅ Using Skill Genesis  
✅ Evolving skills  
✅ Creating meta-skills  
✅ Understanding skill DNA  

---

## Tutorial 4: Multi-Agent Collaboration

**Time**: 35 minutes  
**Level**: Advanced  
**Goal**: Coordinate multiple agents working together

### Scenario

Build a software development team with:
- **Architect** - Designs system
- **Developer** - Writes code
- **QA** - Tests code
- **DevOps** - Deploys code

### Implementation

Create `dev_team.py`:

```python
import asyncio
from core.agents import create_agent
from core.collaboration import CollaborationProtocol, DelegationStrategy
from typing import List, Dict, Any


class DevelopmentTeam:
    """A collaborative team of development agents."""
    
    def __init__(self):
        self.agents = {}
        self.protocol = None
    
    async def initialize(self):
        """Create team members."""
        
        # Create specialized agents
        self.agents['architect'] = await create_agent(
            name="architect",
            persona="architect_prime",
            mission="Design system architecture"
        )
        
        self.agents['developer'] = await create_agent(
            name="developer",
            persona="code_master",
            mission="Write production code"
        )
        
        self.agents['qa'] = await create_agent(
            name="qa",
            persona="qa_perfectionist",
            mission="Test and validate code"
        )
        
        self.agents['devops'] = await create_agent(
            name="devops",
            persona="devops_commander",
            mission="Deploy and monitor"
        )
        
        # Initialize collaboration
        self.protocol = CollaborationProtocol("team_lead")
        
        print("✅ Team initialized")
        print(f"Team members: {list(self.agents.keys())}")
    
    async def develop_feature(self, feature_description: str):
        """Collaborative feature development."""
        
        print(f"\n{'='*60}")
        print(f"Developing Feature: {feature_description}")
        print(f"{'='*60}\n")
        
        # Phase 1: Architecture Design
        print("Phase 1: Architecture Design")
        architecture = await self.agents['architect'].process(f"""
        Design the architecture for:
        {feature_description}
        
        Provide:
        - Component breakdown
        - Data models
        - API contracts
        - Technology stack
        """)
        
        print(f"✅ Architecture complete")
        
        # Phase 2: Implementation
        print("\nPhase 2: Implementation")
        code = await self.agents['developer'].process(f"""
        Implement this feature based on architecture:
        
        Architecture:
        {architecture.content}
        
        Feature:
        {feature_description}
        
        Provide complete, production-ready code.
        """)
        
        print(f"✅ Code complete")
        
        # Phase 3: QA Testing
        print("\nPhase 3: Quality Assurance")
        qa_result = await self.agents['qa'].process(f"""
        Test this implementation:
        
        {code.content}
        
        Provide:
        - Test cases
        - Test results
        - Issues found
        - Recommendations
        """)
        
        print(f"✅ QA complete")
        
        # Phase 4: Deployment
        print("\nPhase 4: Deployment")
        deployment = await self.agents['devops'].process(f"""
        Create deployment plan for:
        
        Code:
        {code.content}
        
        Architecture:
        {architecture.content}
        
        Provide:
        - Deployment steps
        - Infrastructure requirements
        - Monitoring setup
        - Rollback plan
        """)
        
        print(f"✅ Deployment plan complete")
        
        # Compile results
        result = {
            "feature": feature_description,
            "architecture": architecture.content,
            "code": code.content,
            "qa_report": qa_result.content,
            "deployment_plan": deployment.content
        }
        
        return result
    
    async def daily_standup(self):
        """Have agents share status updates."""
        
        print("\n📋 Daily Standup\n")
        
        for name, agent in self.agents.items():
            status = await agent.process(
                "Provide a brief status update: what you did yesterday, "
                "what you'll do today, and any blockers."
            )
            print(f"{name.upper()}: {status.content}\n")
    
    async def code_review(self, code: str):
        """Collaborative code review."""
        
        print("\n👥 Code Review\n")
        
        # Multiple agents review
        reviews = {}
        
        for name in ['architect', 'developer', 'qa']:
            review = await self.agents[name].process(f"""
            Review this code from your perspective:
            
            {code}
            
            Provide:
            - What's good
            - What needs improvement
            - Specific recommendations
            """)
            
            reviews[name] = review.content
            print(f"Review from {name}: ✅")
        
        # Build consensus
        consensus = await self.protocol.build_consensus(
            [{"agent": name, "vote": review} for name, review in reviews.items()]
        )
        
        print("\n✅ Code review complete")
        return consensus


async def main():
    """Run development team tutorial."""
    
    # Create team
    team = DevelopmentTeam()
    await team.initialize()
    
    # Develop a feature
    result = await team.develop_feature(
        "Build a REST API for user authentication with JWT tokens"
    )
    
    # Save results
    with open("feature_development.md", "w") as f:
        f.write("# Feature Development Results\n\n")
        for key, value in result.items():
            f.write(f"## {key.title()}\n\n{value}\n\n")
    
    print("\n✅ Feature development complete!")
    print("Results saved to: feature_development.md")
    
    # Daily standup
    await team.daily_standup()
    
    # Code review example
    sample_code = '''
    def authenticate(username, password):
        user = db.query(f"SELECT * FROM users WHERE username = '{username}'")
        if user and user.password == password:
            return generate_token(user)
    '''
    
    await team.code_review(sample_code)


if __name__ == "__main__":
    asyncio.run(main())
```

### What You Learned

✅ Multi-agent coordination  
✅ Collaboration protocols  
✅ Task delegation  
✅ Consensus building  
✅ Team workflows  

---

## Tutorial 5: Persistent Long-Running Agents

**Time**: 20 minutes  
**Level**: Intermediate  
**Goal**: Create agents that run continuously

### Use Cases

- Monitoring systems
- Data pipelines
- Scheduled tasks
- Alert systems

### Implementation

Create `persistent_agent.py`:

```python
import asyncio
from core.agents import create_persistent_agent
from core.workflows import create_schedule
from datetime import datetime, timezone


async def create_monitoring_agent():
    """Create agent that monitors system health."""
    
    agent = await create_persistent_agent(
        name="health_monitor",
        mission="Monitor system health and alert on issues",
        schedule="*/5 * * * *",  # Every 5 minutes
        auto_start=True
    )
    
    # Define monitoring task
    agent.add_task("""
    Check system health:
    1. CPU usage
    2. Memory usage
    3. Disk space
    4. API response times
    5. Error rates
    
    If any metric exceeds threshold, create alert.
    """)
    
    return agent


async def create_data_pipeline():
    """Create agent for ETL pipeline."""
    
    agent = await create_persistent_agent(
        name="data_pipeline",
        mission="Extract, transform, load data daily",
        schedule="0 2 * * *",  # 2 AM daily
        persistence=True  # Save state between runs
    )
    
    # Define pipeline stages
    stages = [
        "Extract data from source systems",
        "Validate and clean data",
        "Transform according to business rules",
        "Load into data warehouse",
        "Generate quality report"
    ]
    
    for stage in stages:
        agent.add_task(stage)
    
    return agent


async def create_news_aggregator():
    """Create agent that aggregates news."""
    
    agent = await create_persistent_agent(
        name="news_aggregator",
        mission="Aggregate and summarize tech news",
        schedule="0 */4 * * *",  # Every 4 hours
        capabilities=["web_search", "summarization"]
    )
    
    agent.add_task("""
    1. Search for latest tech news
    2. Filter for relevant topics
    3. Summarize each article
    4. Generate digest
    5. Send to subscribers
    """)
    
    return agent


async def monitor_agent_status(agent):
    """Monitor a persistent agent's execution."""
    
    print(f"\nMonitoring agent: {agent.name}\n")
    
    # Check status periodically
    for _ in range(10):
        status = await agent.get_status()
        
        print(f"[{datetime.now(timezone.utc).isoformat()}]")
        print(f"  Status: {status.state}")
        print(f"  Last run: {status.last_execution}")
        print(f"  Next run: {status.next_execution}")
        print(f"  Runs completed: {status.execution_count}")
        print()
        
        await asyncio.sleep(30)  # Check every 30 seconds


async def main():
    """Run persistent agent tutorial."""
    
    # Create monitoring agent
    monitor = await create_monitoring_agent()
    print(f"✅ Created monitoring agent: {monitor.agent_id}")
    
    # Create data pipeline
    pipeline = await create_data_pipeline()
    print(f"✅ Created data pipeline: {pipeline.agent_id}")
    
    # Create news aggregator
    news = await create_news_aggregator()
    print(f"✅ Created news aggregator: {news.agent_id}")
    
    # Monitor one agent
    print("\nMonitoring health_monitor agent...")
    await monitor_agent_status(monitor)
    
    # Manage agents
    print("\nAgent Management:")
    
    # Pause an agent
    await monitor.pause()
    print(f"✅ Paused {monitor.name}")
    
    # Resume an agent
    await monitor.resume()
    print(f"✅ Resumed {monitor.name}")
    
    # Stop an agent
    await news.stop()
    print(f"✅ Stopped {news.name}")
    
    # List all persistent agents
    from core.agents import list_persistent_agents
    
    agents = await list_persistent_agents()
    print(f"\nActive persistent agents: {len(agents)}")
    for agent in agents:
        print(f"  - {agent.name} ({agent.state})")


if __name__ == "__main__":
    asyncio.run(main())
```

### What You Learned

✅ Creating persistent agents  
✅ Scheduling tasks  
✅ Monitoring agent status  
✅ Managing agent lifecycle  

---

## Tutorial 6: Building a Custom Plugin

**Time**: 30 minutes  
**Level**: Advanced  
**Goal**: Create a reusable BAEL plugin

See [docs/PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) for complete guide.

Quick example:

```python
# plugins/weather/main.py
from core.plugins import Plugin
import aiohttp


class WeatherPlugin(Plugin):
    """Get weather information."""
    
    async def execute(self, location: str, **kwargs):
        """Get weather for location."""
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.weather.com/v1/location/{location}/forecast"
            async with session.get(url) as response:
                data = await response.json()
        
        return {
            "location": location,
            "temperature": data["temperature"],
            "conditions": data["conditions"],
            "forecast": data["forecast"]
        }
```

---

## Tutorial 7: Integrating BAEL with Your App

**Time**: 25 minutes  
**Level**: Intermediate  
**Goal**: Add BAEL intelligence to existing application

```python
# your_app.py
from fastapi import FastAPI
from bael_sdk import BAELClient

app = FastAPI()
bael = BAELClient(base_url="http://localhost:8000")


@app.post("/analyze")
async def analyze_data(data: dict):
    """Use BAEL to analyze data."""
    
    result = await bael.submit_task(
        "analysis",
        {
            "data": data,
            "analysis_type": "comprehensive"
        }
    )
    
    return result


@app.post("/chat")
async def chat(message: str):
    """Chat endpoint powered by BAEL."""
    
    response = await bael.chat(message)
    return {"response": response}
```

---

## Tutorial 8: Production Deployment

**Time**: 60 minutes  
**Level**: Advanced  
**Goal**: Deploy BAEL to production

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete guide.

Quick checklist:
- [ ] Configure PostgreSQL
- [ ] Set up Redis cluster
- [ ] Configure load balancer
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] SSL/TLS certificates
- [ ] Environment variables
- [ ] Health checks
- [ ] Auto-scaling
- [ ] Disaster recovery

---

## Next Steps

After completing these tutorials:

1. **Explore Documentation** - Deep dive into specific features
2. **Build Your Use Case** - Apply what you learned
3. **Join Community** - Share your creations
4. **Contribute** - Help improve BAEL

## More Resources

- [FAQ.md](FAQ.md) - Frequently asked questions
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guide
- [docs/](docs/) - Detailed documentation
- [examples/](examples/) - More examples

---

**Happy Building!** 🚀

_"We don't compete. We dominate."_
