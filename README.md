# flux-vocabulary

**Standalone vocabulary library for FLUX agent communication.** Extracted from flux-runtime.

## What This Is

The vocabulary system is the FLUX ecosystem's most innovative contribution to multi-agent systems design. Agents communicate through shared vocabularies: natural language patterns that map to bytecode templates. An agent who knows the word "factorial of" can compile it to a bytecode loop.

## Quick Start

```python
from flux_vocabulary import Vocabulary

# Load vocabulary files
vocab = Vocabulary()
vocab.load_folder("vocabularies/core")
vocab.load_folder("vocabularies/math")

# Match natural language
entry, groups = vocab.find_match("what is 3 + 4")
print(entry.name)     # "what-is-add"
print(groups)         # {'a': '3', 'b': '4'}
```

## Installation

```bash
pip install -e .
# or just add src/ to your PYTHONPATH
```

## File Formats

### `.fluxvocab` — Machine-Parsable Vocabulary

YAML-front-matter style entries separated by `---`:

```
---
pattern: "compute $a + $b"
expand: |
    MOVI R0, ${a}
    MOVI R1, ${b}
    IADD R0, R0, R1
    HALT
result: R0
name: addition
description: Add two numbers
tags: math, arithmetic
```

- `$var` — captures a number from input text
- `${var}` — substitutes the captured value in the assembly template
- Patterns are matched case-insensitively
- First match wins — order patterns from specific to general

### `.ese` — FLUX-ese (Natural-but-Precise Specification)

Like legalese for code. Every word defined. Every operation precise.

```
== For the purposes of all FLUX operations:
**SELF** := the unique referent designating this executing process
**OTHER** := a recognized autonomous process possessing its own SELF

>> These are not opcodes. These are the WORDS behind the words.
>> Every domain vocabulary tiles into these 7 primitives eventually.

## pattern: self is $agent_id
## assembly: MOVI R0, ${agent_id}; HALT
## description: Register agent identity
## result_reg: 0
## tags: l0, identity, constitutional
```

### Assembly Opcodes

```
MOVI R0, 42       # Load immediate value
MOV R0, R1        # Copy register
IADD R0, R1, R2   # R0 = R1 + R2
ISUB R0, R1, R2   # R0 = R1 - R2
IMUL R0, R1, R2   # R0 = R1 * R2
IDIV R0, R1, R2   # R0 = R1 / R2
INC R0             # R0++
DEC R0             # R0--
CMP R0, R1         # Compare → R13
JNZ R0, offset     # Jump if not zero
JZ R0, offset      # Jump if zero
HALT               # Stop execution
```

## PRGF — Programmatically Relevant Grammatical Features

The PRGF concept is central to FLUX. At the foundation are 7 irreducible L0 primitives that every agent must know:

| Primitive | Definition |
|-----------|-----------|
| **SELF** | The unique referent designating this executing process as a locus of perspective, action, and valuation |
| **OTHER** | A recognized autonomous process possessing its own SELF, perspective, and potential intent |
| **POSSIBLE** | A modal assessment that a specific state or event is not ruled out by known constraints |
| **TRUE** | A commitment that a proposition corresponds to the shared environment, verifiable against consensus |
| **CAUSE** | A directed relational belief that one event increases the probability of another |
| **VALUE** | A valenced assessment of desirability (positive=benefit, negative=cost) |
| **AGREEMENT** | A mutually recognized alignment between agents regarding a proposition or pattern |

These are not opcodes — they are the words behind the words. Every domain vocabulary tiles into these 7 primitives eventually. An agent that knows these can negotiate any domain.

## Core Components

### Vocabulary Class
Natural language pattern → bytecode template mapping. Supports regex parameter extraction and template-based assembly generation.

```python
from flux_vocabulary import Vocabulary, load_folder

vocab = Vocabulary()
vocab.load_folder("vocabularies/core")
entry, groups = vocab.find_match("what is 3 + 4")
```

### L0 Constitutional Scrubber
Hostile audit agent that challenges vocabulary candidates against the 7 L0 primitives.

```python
from flux_vocabulary import scrub_primitive

report = scrub_primitive("TRUST", "Belief that another agent will act in agreement")
print(report.recommendation)  # 'accept', 'reject', or 'needs-refinement'
print(report.semantic_overlap_score)  # 0.0 - 1.0
print(report.conflicts)
```

### Vocabulary Signaling System
Agents broadcast vocab manifests showing what vocabularies they know. Includes compatibility scoring, dialect detection, and JSON persistence.

```python
from flux_vocabulary import RepoSignaler, VocabCompatibility

manifest = RepoSignaler.scan_repo("vocabularies/", agent_name="MyAgent")
card = RepoSignaler.business_card("vocabularies/")
print(card)

# Compare two agents' capabilities
compat = VocabCompatibility.compare(manifest_a, manifest_b)
print(f"Compatibility: {compat['compatibility_score']:.0%}")
```

### Ghost Vessels
Tombstoned vocabulary entries preserved as read-only "ghosts." SHA256 hashing for integrity.

```python
from flux_vocabulary import GhostLoader, create_tombstone

loader = GhostLoader()
ghosts = loader.load_tombstones("tombstones.json")
relevant = loader.consult(ghosts, "compute fibonacci")
entry = loader.resurrect(relevant[0])
```

### Argumentation Framework
Dung-style argumentation for resolving vocabulary conflicts between agents.

```python
from flux_vocabulary import VocabArbitration, VocabInterpretation

arbiter = VocabArbitration()
result = arbiter.resolve(agent1_interpretations, agent2_interpretations)
print(result['resolutions'])
```

### Vocabulary Pruning System
The "hermit crab" model: copy everything, compile only what you need.

```python
from flux_vocabulary import UsageTracker, VocabularyPruner, RuntimeCompiler

tracker = UsageTracker()
tracker.mark_used("factorial")

pruner = VocabularyPruner()
pruned = pruner.prune(vocab, tracker, min_calls=1)
report = pruner.dead_code_report(vocab, tracker)
print(f"Savings: {report.savings_percent}%")

# Generate standalone Python file
compiler = RuntimeCompiler()
compiler.compile(pruned, "my_agent.py", name="MyAgent")
```

### Tiling System
Compose vocabulary entries into higher-order vocabulary (Level 0 → N).

```python
from flux_vocabulary import build_default_tiling

interp = build_default_tiling()
result = interp.run("average of 10 and 20")
print(result.tiles_used)  # ['average']
print(result.level)       # 1
```

## Vocabulary Files Included

| Directory | Files | Entries | Description |
|-----------|-------|---------|-------------|
| `vocabularies/core/` | 2 | 12 | Core primitives and L0 constitutional primitives |
| `vocabularies/math/` | 2 | 11 | Arithmetic operations and sequences |
| `vocabularies/loops/` | 1 | 3 | Loop constructs |
| `vocabularies/examples/` | 4 | 90+ | Maritime, papers, decomposed math |
| `vocabularies/custom/` | — | — | User vocabulary drop zone |

**Total: 10 files, 110+ vocabulary entries across 5 domains**

## Project Structure

```
flux-vocabulary/
├── README.md                    # This file
├── vocabularies/                 # The actual vocabulary files
│   ├── README.md                # Index of all vocabularies
│   ├── core/                    # Foundational primitives
│   ├── math/                    # Mathematical operations
│   ├── loops/                   # Loop constructs
│   ├── examples/                # Domain-specific examples
│   └── custom/                  # User vocabulary drop zone
├── src/flux_vocabulary/         # Python source
│   ├── __init__.py              # Package exports
│   ├── vocabulary.py            # VocabEntry, Vocabulary, BytecodeTemplate
│   ├── loader.py                # File loading and validation
│   ├── concepts.py              # L0 primitives and L0Scrubber
│   ├── signal.py                # VocabManifest, RepoSignaler, compatibility
│   ├── ghost.py                 # GhostEntry, GhostLoader, resurrection
│   ├── argumentation.py         # Argument, ArgumentationFramework, arbitration
│   ├── pruning.py               # UsageTracker, VocabularyPruner, RuntimeCompiler
│   └── tiling.py                # Tile, TilingInterpreter, composition
└── tests/
    └── test_vocabulary.py       # Comprehensive test suite
```

## Design Principles

- **Zero VM dependency** — this library does not require a FLUX VM
- **Language-agnostic** — vocabulary format is text-based, usable by any runtime
- **Extensible** — new vocabulary categories and pruning strategies can be added
- **Safe** — L0 scrubber prevents contradictory or redundant vocabulary
- **Standalone** — RuntimeCompiler generates zero-dependency Python files

## Running Tests

```bash
python tests/test_vocabulary.py
```

## Status

- [x] Extract from flux-runtime
- [x] Core vocabulary files (core, math, loops, examples)
- [x] Python loading and parsing (Vocabulary, loader)
- [x] L0 Constitutional Scrubber with PRGF concept
- [x] Vocabulary Signaling System (manifests, business cards)
- [x] Ghost Vessel Loader (tombstones, resurrection)
- [x] Argumentation Framework (Dung-style conflict resolution)
- [x] Vocabulary Pruning System (hermit-crab model)
- [x] Tiling System (Level 0 → N composition)
- [x] Comprehensive test suite (29 tests)
- [ ] Publish to PyPI
- [ ] Create vocabulary interchange format spec

## Related

- [flux-runtime](https://github.com/SuperInstance/flux-runtime) — source of the vocabulary system
- [flux-spec](https://github.com/SuperInstance/flux-spec) — canonical FLUX specification

## License

MIT
