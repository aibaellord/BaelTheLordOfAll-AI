---
name: Council Orchestration Skill
description: Multi-agent council coordination and consensus building
---

# Council Orchestration Skill

## Purpose
Coordinate multiple specialized councils for complex decision-making and problem-solving.

## Council Types

### Grand Council
Supreme decision-making body overseeing all operations.

### Specialized Councils
1. **Optimization Council** - Performance and efficiency
2. **Exploitation Council** - Resource maximization  
3. **Innovation Council** - Novel approaches and creativity
4. **Validation Council** - Quality assurance and testing
5. **Micro-Detail Council** - Edge cases and fine-tuning

## Deliberation Protocol

```python
from core.council.council_engine import CouncilEngine, CouncilType

# Convene council for decision
council = CouncilEngine(CouncilType.GRAND)

# Present problem to all councils
perspectives = await council.gather_perspectives(problem_context)

# Deliberate and reach consensus
decision = await council.deliberate(
    perspectives=perspectives,
    consensus_threshold=0.7,
    max_rounds=5
)

# Execute decision
await council.execute_decision(decision)
```

## Consensus Mechanisms

### Voting Weights
- Standard: Equal weight
- Expertise-based: Higher weight for domain experts
- Confidence-scaled: Weight by confidence level

### Conflict Resolution
1. Identify conflicting perspectives
2. Seek common ground
3. If deadlock, escalate to Grand Council
4. Grand Council makes final decision

## Integration Points
- `core/council/council_engine.py`
- `core/council/grand_council.py`
- `core/orchestration/supreme_orchestrator.py`

## Best Practices
1. Always include Validation Council for quality checks
2. Use Micro-Detail Council for edge cases
3. Let Innovation Council challenge assumptions
4. Weight Exploitation Council higher for resource decisions
