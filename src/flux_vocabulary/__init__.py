"""FLUX Vocabulary Library — Standalone vocabulary system for multi-agent communication."""

from .vocabulary import Vocabulary, VocabEntry
from .vocab_signal import VocabManifest
from .ghost_loader import GhostLoader
from .pruning import UsageTracker, VocabularyPruner
from .contradiction_detector import ContradictionDetector
from .l0_scrubber import L0Scrubber
from .argumentation import ArgumentationFramework
from .necrosis_detector import NecrosisDetector
from .decomposer import Decomposer
from .tiling import TilingSystem
from .compiler import compile_interpreter

# Alias: VocabSignaler is now RepoSignaler
from .vocab_signal import RepoSignaler as VocabSignaler

# Alias: RuntimeCompiler is in pruning module
from .pruning import RuntimeCompiler

__all__ = [
    "Vocabulary", "VocabEntry",
    "VocabManifest", "VocabSignaler",
    "GhostLoader",
    "UsageTracker", "VocabularyPruner",
    "ContradictionDetector",
    "L0Scrubber",
    "ArgumentationFramework",
    "NecrosisDetector",
    "Decomposer",
    "TilingSystem",
    "RuntimeCompiler",
    "compile_interpreter",
]
