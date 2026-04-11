"""
flux-vocabulary — Standalone FLUX vocabulary library.

Extracted from flux-runtime. Provides vocabulary loading, parsing,
signaling, ghost vessels, L0 constitutional scrubbing, argumentation,
pruning, and tiling — all without requiring a FLUX VM.

Core classes:
    VocabEntry      — A single pattern → bytecode mapping
    Vocabulary       — Collection of vocabulary entries, loadable from files
    VocabManifest    — JSON manifest of available vocabularies
    VocabSignal      — Agent capability negotiation via vocab manifests
    GhostLoader      — Resurrect tombstoned vocabulary entries
    L0Scrubber       — Constitutional audit for proposed L0 primitives
    ArgumentationFW  — Dung-style argumentation for vocab conflicts
    VocabularyPruner — Hermit-crab pruning: copy everything, compile what you need
    TilingInterpreter — Level-N vocabulary composition

Usage:
    from flux_vocabulary import Vocabulary

    vocab = Vocabulary()
    vocab.load_folder("vocabularies/core")
    vocab.load_folder("vocabularies/math")

    entry, groups = vocab.find_match("what is 3 + 4")
    print(entry.name, groups)  # what-is-add {'a': '3', 'b': '4'}
"""

from .vocabulary import VocabEntry, BytecodeTemplate, Vocabulary
from .loader import load_fluxvocab, load_ese, load_folder
from .concepts import (
    L0Scrubber, ScrubReport, scrub_primitive,
    L0_PRIMITIVES, L0_DEFINITIONS,
)
from .signal import (
    VocabInfo, VocabManifest, Tombstone,
    VocabCompatibility, RepoSignaler,
)
from .ghost import GhostEntry, GhostLoader, create_tombstone
from .argumentation import (
    Argument, ArgumentationFramework,
    VocabInterpretation, VocabArbitration,
)
from .pruning import UsageTracker, VocabularyPruner, PruneReport, RuntimeCompiler
from .tiling import Tile, TileResult, TilingInterpreter, build_default_tiling

__version__ = "1.0.0"
__all__ = [
    # Core vocabulary
    "VocabEntry", "BytecodeTemplate", "Vocabulary",
    # Loading
    "load_fluxvocab", "load_ese", "load_folder",
    # L0 primitives / concepts
    "L0Scrubber", "ScrubReport", "scrub_primitive",
    "L0_PRIMITIVES", "L0_DEFINITIONS",
    # Signaling
    "VocabInfo", "VocabManifest", "Tombstone",
    "VocabCompatibility", "RepoSignaler",
    # Ghost vessels
    "GhostEntry", "GhostLoader", "create_tombstone",
    # Argumentation
    "Argument", "ArgumentationFramework",
    "VocabInterpretation", "VocabArbitration",
    # Pruning
    "UsageTracker", "VocabularyPruner", "PruneReport", "RuntimeCompiler",
    # Tiling
    "Tile", "TileResult", "TilingInterpreter", "build_default_tiling",
]
