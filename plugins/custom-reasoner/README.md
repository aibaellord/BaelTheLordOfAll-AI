# Custom Reasoner Plugin

Framework for implementing custom reasoning engines with deductive, inductive, and abductive reasoning.

## Features

- ✅ **Multiple Reasoning Modes:** Deductive, Inductive, Abductive, Hybrid
- ✅ **Knowledge Base:** Store premises with confidence scores
- ✅ **Hypothesis Testing:** Test hypotheses against evidence
- ✅ **Reasoning Paths:** Track reasoning steps
- ✅ **Caching:** Cache conclusions for performance
- ✅ **Confidence Scoring:** Configurable confidence thresholds

## Installation

```bash
# Activate plugin
bael plugin load custom-reasoner
```

## Configuration

```yaml
reasoning_mode: hybrid # deductive, inductive, abductive, hybrid
max_depth: 10 # Maximum reasoning depth
confidence_threshold: 0.7 # Minimum confidence (0-1)
```

## Usage

```python
# Get reasoner
reasoner = await bael.plugins.get("custom-reasoner")

# Add premises
await reasoner.add_premise(
    "All humans are mortal",
    confidence=1.0,
    source="aristotle"
)

await reasoner.add_premise(
    "Socrates is human",
    confidence=1.0,
    source="historical_record"
)

# Perform reasoning
conclusion = await reasoner.reason("Is Socrates mortal?")
if conclusion:
    print(f"Conclusion: {conclusion.statement}")
    print(f"Confidence: {conclusion.confidence}")
    print(f"Reasoning: {conclusion.reasoning_path}")

# Test hypothesis
supported, confidence, reasoning = await reasoner.test_hypothesis(
    "All Greeks are philosophers",
    ["Plato was Greek", "Plato was a philosopher"]
)

# Get statistics
stats = await reasoner.get_reasoning_stats()
```

## Reasoning Modes

### Deductive (General → Specific)

Classical syllogistic reasoning from general principles to specific conclusions.

```
All humans are mortal (general)
Socrates is human (specific instance)
Therefore, Socrates is mortal (conclusion)
```

### Inductive (Specific → General)

Reasoning from specific observations to general principles.

```
The sun rose today (observation)
The sun rose yesterday (observation)
Therefore, the sun always rises (generalization)
```

### Abductive (Inference to Best Explanation)

Reasoning backward from observations to the most likely explanation.

```
The ground is wet (observation)
Most likely explanation: It rained
(not: someone watered it, sprinkler broke, etc.)
```

### Hybrid

Combines all reasoning modes for more robust conclusions.

## API Reference

### Knowledge Base Management

```python
# Add premise
await reasoner.add_premise(
    "Premise statement",
    confidence=0.95,
    source="source_name"
)

# Get all premises
premises = await reasoner.get_premises()

# Clear knowledge base
await reasoner.clear_knowledge_base()
```

### Reasoning

```python
# Perform reasoning
conclusion = await reasoner.reason(
    "Query statement",
    depth=5  # Optional depth limit
)

# Test hypothesis
supported, confidence, reasoning = await reasoner.test_hypothesis(
    "Hypothesis statement",
    ["Evidence 1", "Evidence 2"]
)
```

### Statistics

```python
# Get reasoning stats
stats = await reasoner.get_reasoning_stats()
# Returns: {
#   'premises_count': 10,
#   'avg_confidence': 0.85,
#   'conclusions_cached': 3,
#   'reasoning_mode': 'hybrid',
#   'max_depth': 10
# }
```

## Examples

### Logical Reasoning

```python
reasoner = await bael.plugins.get("custom-reasoner")

# Build knowledge base
premises = [
    "All birds have wings",
    "Penguins are birds",
    "Things with wings can fly (usually)"
]

for premise in premises:
    await reasoner.add_premise(premise)

# Test conclusion
conclusion = await reasoner.reason("Can penguins fly?")
# Will conclude: "Can penguins fly?" with high confidence based on premises
```

### Diagnostic Reasoning

```python
# Build diagnostic knowledge base
await reasoner.add_premise("Fever indicates infection", confidence=0.85)
await reasoner.add_premise("Patient has fever", confidence=0.95)

# Perform abductive reasoning
conclusion = await reasoner.reason("Patient has infection?")

# Test hypothesis
supported, conf, msg = await reasoner.test_hypothesis(
    "Patient has flu",
    ["Fever", "Cough", "Body ache"]
)
```

### Scientific Reasoning

```python
# Inductive reasoning example
observations = [
    "Metal A expands when heated",
    "Metal B expands when heated",
    "Metal C expands when heated"
]

for obs in observations:
    await reasoner.add_premise(obs)

# Reason inductively
conclusion = await reasoner.reason("All metals expand when heated")
```

## Performance

- **Caching:** Conclusions cached for repeated queries
- **Depth Control:** Configurable maximum reasoning depth
- **Confidence Filtering:** Ignore low-confidence conclusions
- **Knowledge Base:** Efficient premise lookup and matching

## Advanced Features

### Custom Reasoning Logic

Extend the plugin to implement custom reasoning:

```python
class MyCustomReasoner(CustomReasoner):
    async def _custom_reasoning_mode(self, query: str, depth: int):
        # Implement your own reasoning logic
        pass
```

### Integration with Brain

```python
# Use reasoner in brain operations
reasoning_result = await brain.reason_with_plugin(
    "custom-reasoner",
    query="Is X true?"
)
```

## License

MIT
