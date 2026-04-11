# Vocabulary Index

This directory contains all FLUX vocabulary files organized by domain.

## Format Reference

### `.fluxvocab` files
Machine-parsable vocabulary entries in YAML-front-matter style:
- **pattern**: Natural language regex with `$var` captures
- **expand**: FLUX assembly bytecode with `${var}` substitutions
- **result**: Which register holds the result (e.g., `R0`)
- **name**: Unique identifier for the entry
- **description**: Human-readable description
- **tags**: Comma-separated category tags

### `.ese` files (FLUX-ese)
Natural-but-precise specification language, like legalese for code:
- `**WORD** := definition` — Concept definitions
- `## pattern: ...` — Pattern declarations
- `## assembly: ...` — Bytecode templates
- `>> commentary` — Annotations for agents

## Directory Structure

### `core/` — Foundational Primitives
| File | Entries | Description |
|------|---------|-------------|
| `basic.fluxvocab` | 5 | Core operations: load, add, multiply, noop, hello |
| `l0_primitives.ese` | 7 | Constitutional L0 primitives: SELF, OTHER, POSSIBLE, TRUE, CAUSE, VALUE, AGREEMENT |

### `math/` — Mathematical Operations
| File | Entries | Description |
|------|---------|-------------|
| `arithmetic.fluxvocab` | 7 | Basic arithmetic: add, subtract, multiply, divide, double, square |
| `sequences.fluxvocab` | 4 | Mathematical sequences: factorial, fibonacci, sum-range, power |

### `loops/` — Loop Constructs
| File | Entries | Description |
|------|---------|-------------|
| `basic.fluxvocab` | 3 | Loop patterns: count, repeat, repeated-squaring |

### `examples/` — Domain-Specific Vocabularies
| File | Entries | Description |
|------|---------|-------------|
| `maritime.fluxvocab` | 3 | Maritime navigation: heading, depth-check, ETA |
| `maritime.ese` | 4 | Extended maritime vocabulary with safety checks (FLUX-ese format) |
| `papers_decomposed.fluxvocab` | 30+ | Research paper concepts decomposed into vocabulary |
| `math_decomposed.fluxvocab` | 53 | Python math module functions as vocabulary entries |

### `custom/` — User Vocabularies
Drop your own `.fluxvocab` files here. See `custom/README.md` for instructions.

## Total Stats
- **10 vocabulary files**
- **110+ vocabulary entries**
- **5 domains**: core, math, loops, maritime, papers
- **2 file formats**: `.fluxvocab`, `.ese`
