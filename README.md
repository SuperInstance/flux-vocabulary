# flux-vocabulary

**Standalone vocabulary library for FLUX agent communication.** Extracted from flux-runtime.

## What This Is

The vocabulary system is the FLUX ecosystem's most innovative contribution to multi-agent systems design. Agents communicate through shared vocabularies: natural language patterns that map to bytecode templates. An agent who knows the word "factorial of" can compile it to a bytecode loop.

## Core Components

### Vocabulary Class
Natural language pattern → bytecode template mapping. Supports regex parameter extraction and template-based assembly generation.

### Vocabulary Immune System
Scans vocabulary entries for logical contradictions: duplicate patterns, register collisions, tag inconsistencies, dependency cycles, and semantic drift between versions.

### Ghost Vessels
Tombstoned vocabulary entries preserved as read-only "ghosts." New agents can consult/resurrect pruned vocabulary for historical context. SHA256 hashing for integrity verification.

### L0 Scrubber
Hostile audit agent that challenges vocabulary candidates against 7 constitutional L0 primitives (SELF, OTHER, POSSIBLE, TRUE, CAUSE, VALUE, AGREEMENT). Tests for semantic overlap, redundancy, and edge cases.

### Vocabulary Signaling System
Agents broadcast vocab manifests (business cards) showing what vocabularies they know. Includes compatibility scoring, dialect detection, and JSON persistence.

### Argumentation Framework
Dung-style argumentation for resolving vocabulary conflicts between agents. Claims, evidence, objections, acceptance/rejection with weighted scoring.

### Vocabulary Pruning System
RuntimeCompiler generates standalone Python files with only needed opcodes + vocabulary. The "hermit crab" model: copy everything, compile only what you need. Supports `prune_for_hardware(target="embedded")` with size constraints.

### Paper Bridge + Tiling System
Paper Bridge implements 6 concepts from research papers as callable functions. Tiling System composes vocabulary entries into higher-order vocabulary (Level 0 → N) using `@tile_name()` reference syntax.

## Design Principles

- **Zero VM dependency** — this library does not require a FLUX VM
- **Language-agnostic** — vocabulary format is JSON/text, usable by any runtime
- **Extensible** — new vocabulary categories and pruning strategies can be added
- **Safe** — immune system prevents contradictory or malicious vocabulary

## Status

- [ ] Extract from flux-runtime
- [ ] Remove auto-generated vocabulary bloat
- [ ] Add comprehensive test suite
- [ ] Publish to PyPI
- [ ] Create vocabulary interchange format spec

## Related

- [flux-runtime](https://github.com/SuperInstance/flux-runtime) — source of the vocabulary system
- [flux-spec](https://github.com/SuperInstance/flux-spec) — canonical FLUX specification

## License

MIT
