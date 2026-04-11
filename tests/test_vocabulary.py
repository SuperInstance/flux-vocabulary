"""Tests for flux-vocabulary library."""

import sys
import os
import json
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flux_vocabulary.vocabulary import VocabEntry, Vocabulary
from flux_vocabulary.loader import load_fluxvocab, load_ese, load_folder, validate_fluxvocab
from flux_vocabulary.concepts import L0Scrubber, scrub_primitive, L0_PRIMITIVES, L0_DEFINITIONS
from flux_vocabulary.signal import (
    VocabManifest, VocabInfo, Tombstone,
    VocabCompatibility, RepoSignaler,
)
from flux_vocabulary.ghost import GhostLoader, GhostEntry, create_tombstone
from flux_vocabulary.argumentation import (
    Argument, ArgumentationFramework, VocabInterpretation, VocabArbitration,
)
from flux_vocabulary.pruning import UsageTracker, VocabularyPruner
from flux_vocabulary.tiling import Tile, TilingInterpreter, build_default_tiling


# ============================================================
# Vocabulary core tests
# ============================================================

def test_vocab_entry_compile_and_match():
    """Test VocabEntry regex compilation and matching."""
    entry = VocabEntry(
        pattern="compute $a + $b",
        bytecode_template="MOVI R0, ${a}\nMOVI R1, ${b}\nIADD R0, R0, R1\nHALT",
        result_reg=0,
        name="addition",
    )
    entry.compile()

    result = entry.match("compute 3 + 4")
    assert result is not None
    assert result["a"] == "3"
    assert result["b"] == "4"

    # Case insensitive
    result2 = entry.match("COMPUTE 10 + 20")
    assert result2 is not None

    # No match
    result3 = entry.match("subtract 3 from 4")
    assert result3 is None


def test_vocabulary_load_folder():
    """Test loading vocabulary from a folder."""
    vocab_dir = os.path.join(os.path.dirname(__file__), '..', 'vocabularies', 'core')
    if not os.path.isdir(vocab_dir):
        return

    vocab = Vocabulary()
    vocab.load_folder(vocab_dir)

    assert len(vocab.entries) > 0

    # Should have basic patterns
    match = vocab.find_match("what is 3 + 4")
    if match:
        entry, groups = match
        assert entry.name != ""


def test_vocabulary_load_multiple_folders():
    """Test loading vocabulary from multiple folders."""
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'vocabularies')
    if not os.path.isdir(base_dir):
        return

    vocab = Vocabulary()
    for sub in ['core', 'math', 'loops']:
        path = os.path.join(base_dir, sub)
        if os.path.isdir(path):
            vocab.load_folder(path)

    assert len(vocab.entries) > 5

    # Test math patterns
    match = vocab.find_match("compute 10 * 5")
    if match:
        entry, groups = match
        assert "10" in groups.get("a", "") or "10" in groups.values()


def test_vocabulary_stats():
    """Test vocabulary statistics."""
    vocab = Vocabulary()
    vocab.entries = [
        VocabEntry(pattern="test $a", bytecode_template="NOP\nHALT", tags=["math", "core"]),
        VocabEntry(pattern="test $b", bytecode_template="NOP\nHALT", tags=["core"]),
    ]

    stats = vocab.stats()
    assert stats["total_entries"] == 2
    assert "math" in stats["unique_tags"]
    assert "core" in stats["unique_tags"]


# ============================================================
# Loader tests
# ============================================================

def test_load_fluxvocab_file():
    """Test loading a .fluxvocab file directly."""
    path = os.path.join(os.path.dirname(__file__), '..', 'vocabularies', 'core', 'basic.fluxvocab')
    if not os.path.exists(path):
        return

    entries = load_fluxvocab(path)
    assert len(entries) > 0

    # All entries should have patterns
    for entry in entries:
        assert entry.pattern != ""
        assert entry.bytecode_template != ""


def test_load_ese_file():
    """Test loading a .ese file."""
    path = os.path.join(os.path.dirname(__file__), '..', 'vocabularies', 'core', 'l0_primitives.ese')
    if not os.path.exists(path):
        return

    data = load_ese(path)
    assert "definitions" in data
    assert len(data["definitions"]) > 0

    # Should have L0 primitive definitions
    assert "SELF" in data["definitions"]
    assert "OTHER" in data["definitions"]


def test_validate_fluxvocab():
    """Test vocabulary validation."""
    good_content = """---
pattern: "test $a"
expand: |
    MOVI R0, ${a}
    HALT
result: R0
name: test-entry
tags: test
"""
    issues = validate_fluxvocab(good_content)
    assert len(issues) == 0

    bad_content = """---
name: no-pattern
---
expand: no pattern here
"""
    issues = validate_fluxvocab(bad_content)
    assert len(issues) > 0


# ============================================================
# L0 concepts tests
# ============================================================

def test_l0_primitives_exist():
    """Test that L0 primitives are defined."""
    assert len(L0_PRIMITIVES) == 7
    assert 'self' in L0_PRIMITIVES
    assert 'other' in L0_PRIMITIVES
    assert 'possible' in L0_PRIMITIVES
    assert 'true' in L0_PRIMITIVES
    assert 'cause' in L0_PRIMITIVES
    assert 'value' in L0_PRIMITIVES
    assert 'agreement' in L0_PRIMITIVES


def test_l0_definitions():
    """Test that L0 definitions are complete."""
    assert len(L0_DEFINITIONS) == 7
    for prim in L0_PRIMITIVES:
        assert prim.upper() in L0_DEFINITIONS


def test_scrubber_reject_duplicate():
    """Test that scrubber rejects duplicates of existing L0 primitives."""
    report = scrub_primitive("SELF", "My own perspective")
    assert report.passed == False
    assert report.recommendation == 'reject'


def test_scrubber_accept_novel():
    """Test that scrubber can accept genuinely novel primitives."""
    report = scrub_primitive(
        "TEMPORAL",
        "The perception of events ordered in a before-after sequence"
    )
    # Should not be rejected outright
    assert report.recommendation in ('accept', 'needs-refinement')


def test_scrubber_batch():
    """Test batch scrubbing."""
    scrubber = L0Scrubber()
    candidates = [
        ("BEAUTY", "The aesthetic quality of something"),
        ("KNOWLEDGE", "True beliefs that are justified"),
        ("PREFERENCE", "What an agent values or wants"),
    ]
    reports = scrubber.batch_challenge(candidates)
    assert len(reports) == 3
    for report in reports:
        assert report.recommendation in ('accept', 'reject', 'needs-refinement')


# ============================================================
# Signaling tests
# ============================================================

def test_manifest_creation():
    """Test creating a VocabManifest."""
    manifest = VocabManifest(agent_name="test_agent")
    assert manifest.agent_name == "test_agent"
    assert len(manifest.vocabularies) == 0


def test_manifest_add_and_generate():
    """Test adding vocabularies and generating manifest."""
    manifest = VocabManifest(agent_name="test_agent")
    manifest.add_vocabulary("basic", 5, version="1.0.0", content="test content")
    manifest.add_tombstone("old_vocab", "deprecated")

    summary = manifest.generate()
    assert summary["vocab_count"] == 1
    assert summary["total_patterns"] == 5
    assert summary["tombstone_count"] == 1


def test_manifest_save_and_load():
    """Test saving and loading manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest = VocabManifest(agent_name="test_agent")
        manifest.add_vocabulary("basic", 5, content="test")
        manifest.add_tombstone("old", "deprecated")

        path = os.path.join(tmpdir, "manifest.json")
        manifest.save(path)

        loaded = VocabManifest.load(path)
        assert loaded.agent_name == "test_agent"
        assert len(loaded.vocabularies) == 1
        assert len(loaded.tombstones) == 1


def test_compatibility_identical():
    """Test compatibility of identical manifests."""
    a = VocabManifest(agent_name="a")
    a.add_vocabulary("basic", 5)
    a.add_vocabulary("math", 3)

    b = VocabManifest(agent_name="b")
    b.add_vocabulary("basic", 5)
    b.add_vocabulary("math", 3)

    result = VocabCompatibility.compare(a, b)
    assert result["compatibility_score"] == 1.0
    assert result["shared_count"] == 2


def test_compatibility_no_overlap():
    """Test compatibility of completely different manifests."""
    a = VocabManifest(agent_name="a")
    a.add_vocabulary("basic", 5)

    b = VocabManifest(agent_name="b")
    b.add_vocabulary("math", 3)

    result = VocabCompatibility.compare(a, b)
    assert result["compatibility_score"] == 0.0


def test_repo_signaler_scan():
    """Test RepoSignaler scanning real vocabulary files."""
    vocab_dir = os.path.join(os.path.dirname(__file__), '..', 'vocabularies')
    if not os.path.isdir(vocab_dir):
        return

    manifest = RepoSignaler.scan_repo(vocab_dir, "test_agent")
    assert len(manifest.vocabularies) > 0


def test_repo_signaler_business_card():
    """Test business card generation."""
    vocab_dir = os.path.join(os.path.dirname(__file__), '..', 'vocabularies')
    if not os.path.isdir(vocab_dir):
        return

    card = RepoSignaler.business_card(vocab_dir)
    assert "FLUX VOCABULARY BUSINESS CARD" in card


# ============================================================
# Ghost loader tests
# ============================================================

def test_ghost_create_and_resurrect():
    """Test creating and resurrecting ghost entries."""
    loader = GhostLoader()

    ghost = GhostEntry(
        name="factorial",
        pattern="factorial of $n",
        bytecode_template="MOVI R0, ${n}\nHALT",
        sha256="test_hash_123",
        pruned_reason="Unused - replaced by recursive implementation",
        pruned_at=1000000.0,
        description="Compute factorial",
        tags=["math"],
    )

    entry = loader.resurrect(ghost)
    assert entry is not None
    assert entry.name == "factorial"
    assert entry.pattern == "factorial of $n"


def test_ghost_consult():
    """Test consulting ghosts for matches."""
    loader = GhostLoader()
    loader._ghosts = [
        GhostEntry(
            name="factorial", pattern="factorial of $n",
            bytecode_template="MOVI R0, ${n}\nHALT",
            sha256="abc", pruned_reason="unused", pruned_at=1000000.0,
        ),
        GhostEntry(
            name="fibonacci", pattern="fibonacci of $n",
            bytecode_template="MOVI R0, ${n}\nHALT",
            sha256="def", pruned_reason="unused", pruned_at=1000000.0,
        ),
    ]
    loader._rebuild_index()

    results = loader.consult(loader._ghosts, "factorial")
    assert len(results) > 0
    assert results[0].name == "factorial"


def test_ghost_save_and_load():
    """Test saving and loading tombstones."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = GhostLoader()
        loader._ghosts = [
            GhostEntry(
                name="test", pattern="test $a",
                bytecode_template="NOP\nHALT",
                sha256="hash123", pruned_reason="test",
                pruned_at=1000000.0,
            ),
        ]

        path = os.path.join(tmpdir, "tombstones.json")
        loader.save_tombstones(path)

        loaded = loader.load_tombstones(path)
        assert len(loaded) == 1
        assert loaded[0].name == "test"


# ============================================================
# Argumentation tests
# ============================================================

def test_argumentation_basic():
    """Test basic argumentation evaluation."""
    fw = ArgumentationFramework()

    arg1 = Argument(claim="Pattern X should compile to bytecode A", confidence=0.9)
    arg1.add_evidence("Test result confirms bytecode A")

    fw.add_argument(arg1)

    results = fw.evaluate()
    assert "arg_0" in results
    # Has evidence and no objections -> accepted
    assert results["arg_0"] == "accepted"


def test_argumentation_with_objection():
    """Test argumentation with objections."""
    fw = ArgumentationFramework()

    arg1 = Argument(claim="X is true", confidence=0.5)
    arg1.add_evidence("Evidence 1")

    fw.add_argument(arg1)

    # Strong objection overcomes weak support
    objection = Argument(claim="X is not true", confidence=0.9)
    fw.object_to("arg_0", objection)

    results = fw.evaluate()
    # support_weight = 1 * 0.5 = 0.5, objection_weight = 0.9
    # ratio = 0.5/0.9 = 0.56, which is > 0.5 so undecided
    assert results["arg_0"] == "undecided"


def test_vocab_arbitration():
    """Test vocabulary arbitration between two agents."""
    arbiter = VocabArbitration()

    agent1 = [VocabInterpretation("compute $a + $b", "IADD R0, R0, R1", "Agent1")]
    agent2 = [VocabInterpretation("compute $a + $b", "IMUL R0, R0, R1", "Agent2")]

    result = arbiter.resolve(agent1, agent2)
    assert len(result["conflicts"]) == 1
    assert "resolutions" in result


# ============================================================
# Pruning tests
# ============================================================

def test_usage_tracker():
    """Test usage tracking."""
    tracker = UsageTracker()
    tracker.mark_used("factorial")
    tracker.mark_used("factorial")
    tracker.mark_used("add")

    assert tracker.get_call_count("factorial") == 2
    assert tracker.get_call_count("add") == 1
    assert tracker.get_call_count("unknown") == 0

    most_used = tracker.get_most_used(1)
    assert most_used[0][0] == "factorial"
    assert most_used[0][1] == 2

    unused = tracker.get_unused(["factorial", "add", "subtract"])
    assert unused == ["subtract"]


def test_usage_tracker_serialization():
    """Test usage tracker save/load."""
    tracker = UsageTracker()
    tracker.mark_used("test")

    data = tracker.to_dict()
    restored = UsageTracker.from_dict(data)

    assert restored.get_call_count("test") == 1


def test_pruner_dead_code_report():
    """Test dead code report generation."""
    vocab = Vocabulary()
    vocab.entries = [
        VocabEntry(name="used", pattern="test", bytecode_template="NOP\nHALT"),
        VocabEntry(name="unused1", pattern="test2", bytecode_template="NOP\nHALT"),
        VocabEntry(name="unused2", pattern="test3", bytecode_template="NOP\nHALT"),
    ]

    tracker = UsageTracker()
    tracker.mark_used("used")

    pruner = VocabularyPruner()
    report = pruner.dead_code_report(vocab, tracker)

    assert report.original_count == 3
    assert report.pruned_count == 1
    assert set(report.removed) == {"unused1", "unused2"}
    assert report.savings_percent == pytest.approx(66.7, abs=0.1) if 'pytest' in sys.modules else abs(report.savings_percent - 66.7) < 0.1


# ============================================================
# Tiling tests
# ============================================================

def test_tiling_build_default():
    """Test building default tiling interpreter."""
    interp = build_default_tiling()

    tiles = interp.list_tiles()
    assert len(tiles) > 0

    # Should have average tile
    tile_names = [t["name"] for t in tiles]
    assert "average" in tile_names


def test_tiling_match():
    """Test tile pattern matching."""
    interp = build_default_tiling()

    result = interp.run("average of 10 and 20")
    assert result.success is True
    assert result.tiles_used[0] == "average"


def test_tiling_dependency_graph():
    """Test tile dependency graph."""
    interp = build_default_tiling()

    graph = interp.tile_graph()
    assert "average" in graph
    assert "addition" in graph["average"]
    assert "division" in graph["average"]


# ============================================================
# Integration tests
# ============================================================

def test_full_workflow():
    """Test complete workflow: load, match, signal, scrub."""
    # 1. Load vocabularies
    vocab = Vocabulary()
    vocab_dir = os.path.join(os.path.dirname(__file__), '..', 'vocabularies')
    for sub in ['core', 'math']:
        path = os.path.join(vocab_dir, sub)
        if os.path.isdir(path):
            vocab.load_folder(path)

    # 2. Find a match
    match = vocab.find_match("what is 3 + 4")
    if match:
        entry, groups = match
        assert entry.pattern != ""
        assert groups is not None

    # 3. Generate manifest
    manifest = VocabManifest(agent_name="test")
    manifest.add_vocabulary("test", len(vocab.entries), content="test")

    # 4. Scrub a candidate
    report = scrub_primitive("TRUST", "Belief another agent will act in agreement")
    assert report.recommendation in ('accept', 'reject', 'needs-refinement')


if __name__ == "__main__":
    print("Running flux-vocabulary tests...")
    import traceback

    test_fns = [
        test_vocab_entry_compile_and_match,
        test_vocabulary_load_folder,
        test_vocabulary_load_multiple_folders,
        test_vocabulary_stats,
        test_load_fluxvocab_file,
        test_load_ese_file,
        test_validate_fluxvocab,
        test_l0_primitives_exist,
        test_l0_definitions,
        test_scrubber_reject_duplicate,
        test_scrubber_accept_novel,
        test_scrubber_batch,
        test_manifest_creation,
        test_manifest_add_and_generate,
        test_manifest_save_and_load,
        test_compatibility_identical,
        test_compatibility_no_overlap,
        test_repo_signaler_scan,
        test_repo_signaler_business_card,
        test_ghost_create_and_resurrect,
        test_ghost_consult,
        test_ghost_save_and_load,
        test_argumentation_basic,
        test_argumentation_with_objection,
        test_vocab_arbitration,
        test_usage_tracker,
        test_usage_tracker_serialization,
        test_tiling_build_default,
        test_tiling_match,
        test_tiling_dependency_graph,
        test_full_workflow,
    ]

    passed = 0
    failed = 0
    for test_fn in test_fns:
        try:
            test_fn()
            print(f"  PASS: {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {test_fn.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(0 if failed == 0 else 1)
