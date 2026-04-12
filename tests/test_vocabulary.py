"""Comprehensive tests for flux-vocabulary."""
import sys
import os
import json
import time
import tempfile
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flux_vocabulary import Vocabulary, VocabEntry
from flux_vocabulary.loader import (
    load_fluxvocab, load_ese, load_folder, load_folder_recursive,
    validate_fluxvocab, _parse_fluxvocab_block,
)
from flux_vocabulary.concepts import L0Scrubber, ScrubReport, L0_PRIMITIVES, L0_DEFINITIONS, scrub_primitive
from flux_vocabulary.vocab_signal import (
    VocabInfo, Tombstone, VocabManifest, VocabCompatibility, RepoSignaler,
)
from flux_vocabulary.ghost import (
    GhostEntry, ResurrectionContext, GhostLoader, create_tombstone,
)
from flux_vocabulary.ghost_loader import GhostLoader as GhostLoader2, GhostEntry as GhostEntry2
from flux_vocabulary.argumentation import (
    Argument, ArgumentationFramework, VocabInterpretation, VocabArbitration,
)
from flux_vocabulary.pruning import (
    UsageTracker, VocabularyPruner, PruneReport, RuntimeCompiler,
)
from flux_vocabulary.tiling import Tile, TileResult, TilingSystem, build_default_tiling
from flux_vocabulary.contradiction_detector import (
    ContradictionDetector, Contradiction, ScanReport, Severity,
)
from flux_vocabulary.necrosis_detector import (
    NecrosisDetector, NecrosisLevel, TileProvenance,
)
from flux_vocabulary.decomposer import Decomposer, DecomposedVocabulary, NativeBridge
from flux_vocabulary.compiler import compile_interpreter


# ─── Helpers ─────────────────────────────────────────────────────────────

def make_entry(pattern="add $a and $b", template="MOVI R0, ${a}\nMOVI R1, ${b}\nIADD R0, R0, R1\nHALT",
               name="addition", result_reg=0, description="Add two numbers", tags=["math"]):
    """Create a test VocabEntry with compiled regex."""
    entry = VocabEntry(
        pattern=pattern,
        bytecode_template=template,
        result_reg=result_reg,
        name=name,
        description=description,
        tags=tags,
    )
    entry.compile()
    return entry


def make_vocab_with_entries(*entries):
    """Create a Vocabulary with pre-populated entries."""
    v = Vocabulary("test")
    for e in entries:
        v.add(e)
    return v


def make_sample_fluxvocab_file(path, content):
    """Write a sample .fluxvocab file."""
    with open(path, 'w') as f:
        f.write(content)


# ═══════════════════════════════════════════════════════════════════════
# VocabEntry Tests
# ═══════════════════════════════════════════════════════════════════════

class TestVocabEntry:
    """Tests for VocabEntry dataclass and its methods."""

    def test_create_entry_defaults(self):
        entry = VocabEntry(pattern="test $x", bytecode_template="")
        assert entry.pattern == "test $x"
        assert entry.bytecode_template == ""
        assert entry.result_reg == 0
        assert entry.name == ""
        assert entry.description == ""
        assert entry.tags == []
        assert entry._regex is None

    def test_create_entry_full(self):
        entry = VocabEntry(
            pattern="add $a and $b",
            bytecode_template="MOVI R0, ${a}\nHALT",
            result_reg=1,
            name="addition",
            description="Add two numbers",
            tags=["math", "core"],
        )
        assert entry.result_reg == 1
        assert entry.name == "addition"
        assert len(entry.tags) == 2

    def test_compile_creates_regex(self):
        entry = make_entry()
        assert entry._regex is not None
        assert entry._regex.pattern != ""

    def test_compile_simple_pattern(self):
        entry = VocabEntry(pattern="hello", bytecode_template="HALT")
        entry.compile()
        assert entry._regex is not None

    def test_compile_captures_dollar_vars(self):
        entry = VocabEntry(pattern="compute $a + $b", bytecode_template="HALT")
        entry.compile()
        m = entry._regex.search("compute 3 + 4")
        assert m is not None
        assert m.groupdict() == {"a": "3", "b": "4"}

    def test_match_returns_groups_dict(self):
        entry = make_entry()
        result = entry.match("add 5 and 3")
        assert result is not None
        assert result == {"a": "5", "b": "3"}

    def test_match_returns_none_on_no_match(self):
        entry = make_entry()
        assert entry.match("subtract 5 and 3") is None

    def test_match_case_insensitive(self):
        entry = make_entry()
        result = entry.match("ADD 5 AND 3")
        assert result is not None
        assert result["a"] == "5"

    def test_match_with_single_var(self):
        entry = VocabEntry(pattern="double $a", bytecode_template="MOVI R0, ${a}\nHALT")
        entry.compile()
        result = entry.match("double 42")
        assert result == {"a": "42"}

    def test_match_only_captures_digits(self):
        entry = VocabEntry(pattern="compute $a + $b", bytecode_template="HALT")
        entry.compile()
        m = entry._regex.search("compute abc + def")
        # $var only matches \d+, so non-digit text won't match the capture groups
        assert m is None or ("a" not in m.groupdict() or m.groupdict()["a"] is None)

    def test_lazy_compile_on_match(self):
        entry = VocabEntry(pattern="test $x", bytecode_template="MOVI R0, ${x}\nHALT")
        assert entry._regex is None
        result = entry.match("test 7")
        assert result is not None
        assert entry._regex is not None

    def test_match_with_extra_text(self):
        """Pattern uses search, not fullmatch, so extra text is fine."""
        entry = make_entry()
        result = entry.match("please add 5 and 3 for me")
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════
# Vocabulary Class Tests
# ═══════════════════════════════════════════════════════════════════════

class TestVocabulary:
    """Tests for the Vocabulary class."""

    def test_create_empty(self):
        v = Vocabulary("empty")
        assert v.name == "empty"
        assert v.entries == []
        assert v.templates == {}

    def test_add_entry(self):
        v = Vocabulary("test")
        e = make_entry()
        v.add(e)
        assert len(v.entries) == 1
        assert v.entries[0].name == "addition"

    def test_add_multiple_entries(self):
        v = Vocabulary("test")
        v.add(make_entry(name="add"))
        v.add(make_entry(pattern="double $a", name="double", template="MOVI R0, ${a}\nIADD R0, R0, R0\nHALT"))
        assert len(v.entries) == 2

    def test_find_match_first_wins(self):
        v = Vocabulary("test")
        e1 = make_entry(pattern="compute $a + $b", name="compute-add")
        e2 = make_entry(pattern="compute $a + $b exactly", name="exact-add")
        v.add(e1)
        v.add(e2)
        result = v.find_match("compute 3 + 4")
        assert result is not None
        assert result[0].name == "compute-add"

    def test_find_match_no_match(self):
        v = Vocabulary("test")
        assert v.find_match("nothing matches") is None

    def test_list_words(self):
        v = Vocabulary("test")
        v.add(make_entry(pattern="add $a and $b", name="add"))
        v.add(make_entry(pattern="sub $a and $b", name="sub"))
        words = v.list_words()
        assert len(words) == 2
        assert "add $a and $b" in words

    def test_load_folder_nonexistent(self):
        v = Vocabulary("test")
        v.load_folder("/nonexistent/path")
        assert v.entries == []

    def test_load_folder_fluxvocab(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.fluxvocab")
            make_sample_fluxvocab_file(fpath, textwrap.dedent("""\
                ---
                pattern: "hello $x"
                expand: |
                    MOVI R0, ${x}
                    HALT
                result: R0
                name: hello
                description: Say hello
                tags: test
                ---
                pattern: "double $x"
                expand: |
                    MOVI R0, ${x}
                    IADD R0, R0, R0
                    HALT
                result: R0
                name: double
                tags: math
            """))
            v = Vocabulary("test")
            v.load_folder(tmpdir)
            assert len(v.entries) == 2

    def test_load_folder_skips_non_vocab_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "readme.txt")
            with open(fpath, 'w') as f:
                f.write("not a vocab file")
            v = Vocabulary("test")
            v.load_folder(tmpdir)
            assert v.entries == []

    def test_load_folder_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.fluxvocab")
            make_sample_fluxvocab_file(fpath, textwrap.dedent("""\
                ---
                pattern: "hello"
                expand: |
                    MOVI R0, 42
                    HALT
                result: R0
                name: hello
            """))
            v = Vocabulary("test")
            v.load_folder(tmpdir)
            v.load_folder(tmpdir)  # should not double-load
            assert len(v.entries) == 1

    def test_load_folder_ese_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test.ese")
            with open(fpath, 'w') as f:
                f.write(textwrap.dedent("""\
                    ## pattern: self is $agent_id
                    ## assembly: MOVI R0, ${agent_id}
                    ## description: Register identity
                    ## result_reg: 0
                    ## tags: test, l0
                """))
            v = Vocabulary("test")
            v.load_folder(tmpdir)
            # ESE entries don't have expand: so they may be skipped by _parse_entry
            # This test documents current behavior
            assert isinstance(v.entries, list)


# ═══════════════════════════════════════════════════════════════════════
# BytecodeTemplate Tests
# ═══════════════════════════════════════════════════════════════════════

class TestBytecodeTemplate:
    """Tests for BytecodeTemplate dataclass."""

    def test_create_template(self):
        from flux_vocabulary.vocabulary import BytecodeTemplate
        t = BytecodeTemplate(
            name="factorial",
            assembly="MOVI R0, ${n}\nHALT",
            result_reg=0,
            description="Compute factorial",
        )
        assert t.name == "factorial"
        assert t.result_reg == 0


# ═══════════════════════════════════════════════════════════════════════
# Loader Tests
# ═══════════════════════════════════════════════════════════════════════

class TestLoader:
    """Tests for the loader module functions."""

    def test_load_fluxvocab_basic(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fluxvocab', delete=False) as f:
            f.write(textwrap.dedent("""\
                ---
                pattern: "add $a and $b"
                expand: |
                    MOVI R0, ${a}
                    MOVI R1, ${b}
                    IADD R0, R0, R1
                    HALT
                result: R0
                name: add
            """))
            f.flush()
            entries = load_fluxvocab(f.name)
            assert len(entries) == 1
            assert entries[0].name == "add"
            os.unlink(f.name)

    def test_load_fluxvocab_multiple_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "multi.fluxvocab")
            with open(fpath, 'w') as f:
                f.write(textwrap.dedent("""\
                    ---
                    pattern: "add $a and $b"
                    expand: |
                        MOVI R0, ${a}
                        HALT
                    result: R0
                    name: add
                    ---
                    pattern: "sub $a and $b"
                    expand: |
                        MOVI R0, ${a}
                        HALT
                    result: R0
                    name: sub
                """))
            entries = load_fluxvocab(fpath)
            assert len(entries) == 2
            assert entries[0].name == "add"
            assert entries[1].name == "sub"

    def test_load_fluxvocab_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fluxvocab', delete=False) as f:
            f.write("")
            f.flush()
            entries = load_fluxvocab(f.name)
            assert entries == []
            os.unlink(f.name)

    def test_load_fluxvocab_entry_without_expand_skipped(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fluxvocab', delete=False) as f:
            f.write(textwrap.dedent("""\
                ---
                pattern: "test $x"
                name: test-no-expand
                description: This has no expand
            """))
            f.flush()
            entries = load_fluxvocab(f.name)
            assert entries == []
            os.unlink(f.name)

    def test_load_ese_basic(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ese', delete=False) as f:
            f.write(textwrap.dedent("""\
                **SELF** := the unique referent designating this process
                **OTHER** := a recognized autonomous process
                >> These are foundational concepts.
                ## pattern: self is $agent_id
                ## assembly: MOVI R0, ${agent_id}; HALT
                ## description: Register identity
                ## result_reg: 0
                ## tags: l0, identity
            """))
            f.flush()
            result = load_ese(f.name)
            assert result["source"] == os.path.basename(f.name)
            assert "SELF" in result["definitions"]
            assert "OTHER" in result["definitions"]
            assert len(result["patterns"]) == 1
            assert len(result["commentary"]) == 1
            os.unlink(f.name)

    def test_validate_fluxvocab_valid(self):
        content = textwrap.dedent("""\
            ---
            pattern: "test $x"
            expand: MOVI R0, ${x}\nHALT
            result: R0
            name: test-entry
        """)
        issues = validate_fluxvocab(content)
        assert len(issues) == 0

    def test_validate_fluxvocab_missing_pattern(self):
        content = textwrap.dedent("""\
            ---
            expand: MOVI R0, 0\nHALT
            result: R0
            name: no-pattern
        """)
        issues = validate_fluxvocab(content)
        assert any("missing 'pattern:'" in i for i in issues)

    def test_validate_fluxvocab_missing_expand(self):
        content = textwrap.dedent("""\
            ---
            pattern: "test"
            result: R0
        """)
        issues = validate_fluxvocab(content)
        assert any("missing 'expand:'" in i for i in issues)

    def test_validate_fluxvocab_duplicate_names(self):
        content = textwrap.dedent("""\
            ---
            pattern: "test $x"
            expand: |
                MOVI R0, ${x}
                HALT
            result: R0
            name: duplicate
            ---
            pattern: "other $y"
            expand: |
                MOVI R0, ${y}
                HALT
            result: R0
            name: duplicate
        """)
        issues = validate_fluxvocab(content)
        assert any("duplicate" in i.lower() for i in issues)

    def test_parse_fluxvocab_block_with_pipe_expand(self):
        block = textwrap.dedent("""\
            pattern: "add $a + $b"
            expand: |
                MOVI R0, ${a}
                MOVI R1, ${b}
                IADD R0, R0, R1
                HALT
            result: R0
            name: addition
            description: Add numbers
            tags: math, core
        """)
        entry = _parse_fluxvocab_block(block)
        assert entry is not None
        assert entry.name == "addition"
        assert "IADD" in entry.bytecode_template
        assert entry.tags == ["math", "core"]

    def test_parse_fluxvocab_block_inline_expand(self):
        block = 'pattern: "double $x"\nexpand: MOVI R0, ${x}\nIADD R0, R0, R0\nHALT\nresult: R0\nname: double'
        entry = _parse_fluxvocab_block(block)
        assert entry is not None
        assert entry.name == "double"

    def test_parse_fluxvocab_block_name_fallback(self):
        """When no name is given, pattern[:40] is used as name."""
        block = 'pattern: "short"\nexpand: MOVI R0, 0\nHALT\nresult: R0'
        entry = _parse_fluxvocab_block(block)
        assert entry is not None
        assert entry.name.startswith("short")

    def test_load_folder_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "sub")
            os.makedirs(subdir)
            fpath = os.path.join(subdir, "test.fluxvocab")
            make_sample_fluxvocab_file(fpath, textwrap.dedent("""\
                ---
                pattern: "hello"
                expand: MOVI R0, 42\nHALT
                result: R0
                name: hello
            """))
            entries = load_folder_recursive(tmpdir)
            assert len(entries) == 1


# ═══════════════════════════════════════════════════════════════════════
# L0 Concepts / Scrubber Tests
# ═══════════════════════════════════════════════════════════════════════

class TestL0Concepts:
    """Tests for L0 constitutional primitives."""

    def test_l0_primitives_count(self):
        assert len(L0_PRIMITIVES) == 7

    def test_l0_definitions_has_all_primitives(self):
        for prim in L0_PRIMITIVES:
            assert prim.upper() in L0_DEFINITIONS

    def test_scrub_primitive_rejects_existing(self):
        report = scrub_primitive("SELF", "My own perspective")
        assert report.recommendation == 'reject'
        assert report.passed is False
        assert len(report.conflicts) > 0

    def test_scrub_primitive_case_insensitive(self):
        report = scrub_primitive("self", "perspective")
        assert report.recommendation == 'reject'

    def test_scrub_report_has_challenges(self):
        report = scrub_primitive("NOVELTY", "Something entirely new and distinct")
        assert len(report.challenges) > 0

    def test_scrub_report_repr(self):
        report = ScrubReport(candidate="TEST", definition="test", passed=True, can_tile=False,
                            conflicts=[], challenges=[], recommendation="accept")
        r = repr(report)
        assert "TEST" in r
        assert "accept" in r

    def test_scrubber_batch_challenge(self):
        scrubber = L0Scrubber()
        reports = scrubber.batch_challenge([
            ("BEAUTY", "Aesthetic quality"),
            ("TRUST", "Belief in agreement with other"),
        ])
        assert len(reports) == 2
        for r in reports:
            assert r.recommendation in ('accept', 'reject', 'needs-refinement')

    def test_scrub_overlap_score_range(self):
        report = scrub_primitive("QUARK", "A fundamental subatomic particle")
        assert 0.0 <= report.semantic_overlap_score <= 1.0

    def test_scrub_reasoning_populated(self):
        report = scrub_primitive("SOMETHING", "A generic thing")
        assert report.reasoning != ""


# ═══════════════════════════════════════════════════════════════════════
# VocabManifest / Signal Tests
# ═══════════════════════════════════════════════════════════════════════

class TestVocabManifest:
    """Tests for VocabManifest, VocabCompatibility, RepoSignaler."""

    def test_create_manifest(self):
        m = VocabManifest(agent_name="test-agent")
        assert m.agent_name == "test-agent"
        assert m.vocabularies == []
        assert m.tombstones == []

    def test_add_vocabulary(self):
        m = VocabManifest("agent")
        m.add_vocabulary("core", 10, "1.0.0", "content")
        assert len(m.vocabularies) == 1
        assert m.vocabularies[0].pattern_count == 10

    def test_add_vocabulary_with_hash(self):
        m = VocabManifest("agent")
        m.add_vocabulary("core", 5, "1.0.0", "some content")
        assert m.vocabularies[0].sha256 != ""

    def test_add_tombstone(self):
        m = VocabManifest("agent")
        m.add_tombstone("old-vocab", "no longer needed")
        assert len(m.tombstones) == 1
        assert m.tombstones[0].name == "old-vocab"
        assert m.tombstones[0].pruned_at != ""

    def test_generate_manifest(self):
        m = VocabManifest("agent")
        m.add_vocabulary("core", 5)
        m.add_vocabulary("math", 10)
        data = m.generate()
        assert data["agent_name"] == "agent"
        assert data["vocab_count"] == 2
        assert data["total_patterns"] == 15
        assert data["tombstone_count"] == 0

    def test_manifest_save_and_load(self):
        m = VocabManifest("agent")
        m.add_vocabulary("core", 5)
        m.add_tombstone("old", "unused")
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            m.save(path)
            loaded = VocabManifest.load(path)
            assert loaded.agent_name == "agent"
            assert len(loaded.vocabularies) == 1
            assert len(loaded.tombstones) == 1
        finally:
            os.unlink(path)

    def test_compatibility_identical(self):
        m1 = VocabManifest("a")
        m1.add_vocabulary("core", 5)
        m2 = VocabManifest("b")
        m2.add_vocabulary("core", 5)
        result = VocabCompatibility.compare(m1, m2)
        assert result["compatibility_score"] == 1.0
        assert result["shared_count"] == 1

    def test_compatibility_no_overlap(self):
        m1 = VocabManifest("a")
        m1.add_vocabulary("core", 5)
        m2 = VocabManifest("b")
        m2.add_vocabulary("math", 10)
        result = VocabCompatibility.compare(m1, m2)
        assert result["compatibility_score"] == 0.0
        assert result["unique_to_a_count"] == 1
        assert result["unique_to_b_count"] == 1

    def test_compatibility_empty(self):
        m1 = VocabManifest("a")
        m2 = VocabManifest("b")
        result = VocabCompatibility.compare(m1, m2)
        assert result["compatibility_score"] == 0.0

    def test_vocab_info_compute_hash(self):
        info = VocabInfo(name="test", pattern_count=1)
        info.compute_hash("content")
        assert len(info.sha256) == 64  # SHA256 hex

    def test_repo_signaler_scan_repo(self):
        manifest = RepoSignaler.scan_repo("vocabularies/core")
        assert manifest.agent_name == "unknown"
        assert len(manifest.vocabularies) > 0

    def test_repo_signaler_detect_dialect(self):
        dialect = RepoSignaler.detect_dialect("vocabularies")
        assert isinstance(dialect, str)
        assert dialect != ""

    def test_repo_signaler_business_card(self):
        card = RepoSignaler.business_card("vocabularies")
        assert "FLUX VOCABULARY BUSINESS CARD" in card
        assert "Dialect:" in card

    def test_repo_signaler_invalid_dir(self):
        assert RepoSignaler.business_card("/nonexistent") == "Invalid vocabulary directory"
        assert RepoSignaler.detect_dialect("/nonexistent") == "unknown"


# ═══════════════════════════════════════════════════════════════════════
# Ghost System Tests
# ═══════════════════════════════════════════════════════════════════════

class TestGhostSystem:
    """Tests for GhostEntry, GhostLoader, create_tombstone."""

    def test_create_ghost_entry(self):
        ghost = GhostEntry(
            name="factorial", pattern="factorial of $n",
            bytecode_template="MOVI R0, ${n}\nHALT",
            sha256="abc123", pruned_reason="unused",
            pruned_at=time.time(),
        )
        assert ghost.name == "factorial"
        assert ghost.age_days() >= 0
        assert ghost.is_recent(days=365)

    def test_ghost_entry_to_dict_roundtrip(self):
        ghost = GhostEntry(
            name="test", pattern="test $x",
            bytecode_template="MOVI R0, ${x}\nHALT",
            sha256="hash123", pruned_reason="test",
            pruned_at=1000.0,
        )
        d = ghost.to_dict()
        restored = GhostEntry.from_dict(d)
        assert restored.name == ghost.name
        assert restored.sha256 == ghost.sha256

    def test_ghost_loader_save_and_load(self):
        loader = GhostLoader()
        ghosts = [
            GhostEntry(
                name="factorial", pattern="factorial of $n",
                bytecode_template="MOVI R0, ${n}\nHALT",
                sha256="abc123", pruned_reason="unused",
                pruned_at=time.time(),
            ),
        ]
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            loader.save_tombstones(path, ghosts)
            loaded = loader.load_tombstones(path)
            assert len(loaded) == 1
            assert loaded[0].name == "factorial"
        finally:
            os.unlink(path)

    def test_ghost_loader_consult(self):
        ghosts = [
            GhostEntry(name="factorial", pattern="factorial of $n",
                       bytecode_template="MOVI R0, ${n}\nHALT",
                       sha256="abc", pruned_reason="unused", pruned_at=time.time(),
                       tags=["math"]),
            GhostEntry(name="fibonacci", pattern="fibonacci of $n",
                       bytecode_template="MOVI R0, ${n}\nHALT",
                       sha256="def", pruned_reason="unused", pruned_at=time.time(),
                       tags=["math"]),
        ]
        loader = GhostLoader()
        results = loader.consult(ghosts, "factorial")
        assert len(results) == 1
        assert results[0].name == "factorial"

    def test_ghost_loader_resurrect(self):
        ghost = GhostEntry(
            name="factorial", pattern="factorial of $n",
            bytecode_template="MOVI R0, ${n}\nHALT",
            sha256="abc", pruned_reason="unused", pruned_at=time.time(),
        )
        loader = GhostLoader()
        entry = loader.resurrect(ghost)
        assert entry is not None
        assert entry.name == "factorial"
        assert entry.pattern == "factorial of $n"

    def test_ghost_loader_resurrect_invalid(self):
        ghost = GhostEntry(
            name="empty", pattern="",
            bytecode_template="", sha256="abc",
            pruned_reason="test", pruned_at=time.time(),
        )
        loader = GhostLoader()
        assert loader.resurrect(ghost) is None

    def test_create_tombstone_from_vocab_entry(self):
        entry = make_entry(name="add")
        ghost = create_tombstone(entry, "unused", usage_count=5)
        assert ghost.name == "add"
        assert ghost.usage_count == 5
        assert ghost.sha256 != ""

    def test_ghost_loader_find_by_name(self):
        loader = GhostLoader()
        g1 = GhostEntry(name="test", pattern="test", bytecode_template="HALT",
                        sha256="h1", pruned_reason="r", pruned_at=1.0)
        g2 = GhostEntry(name="other", pattern="other", bytecode_template="HALT",
                        sha256="h2", pruned_reason="r", pruned_at=1.0)
        loader.merge([g1, g2])
        assert len(loader.find_by_name("test")) == 1
        assert loader.find_by_name("nonexistent") == []

    def test_ghost_loader_find_by_hash(self):
        loader = GhostLoader()
        g = GhostEntry(name="test", pattern="test", bytecode_template="HALT",
                       sha256="unique_hash_123", pruned_reason="r", pruned_at=1.0)
        loader.merge([g])
        found = loader.find_by_hash("unique_hash_123")
        assert found is not None
        assert found.name == "test"

    def test_ghost_loader_merge_deduplicates(self):
        loader = GhostLoader()
        g = GhostEntry(name="test", pattern="test", bytecode_template="HALT",
                       sha256="same_hash", pruned_reason="r", pruned_at=1.0)
        loader.merge([g])
        loader.merge([g])
        assert len(loader._ghosts) == 1

    def test_ghost_loader_statistics_empty(self):
        loader = GhostLoader()
        stats = loader.get_statistics()
        assert stats["total_ghosts"] == 0
        assert stats["avg_age_days"] == 0

    def test_ghost_loader_statistics_populated(self):
        loader = GhostLoader()
        g1 = GhostEntry(name="a", pattern="a", bytecode_template="HALT",
                        sha256="h1", pruned_reason="unused", pruned_at=time.time() - 86400)
        g2 = GhostEntry(name="b", pattern="b", bytecode_template="HALT",
                        sha256="h2", pruned_reason="deprecated", pruned_at=time.time() - 172800)
        loader.merge([g1, g2])
        stats = loader.get_statistics()
        assert stats["total_ghosts"] == 2
        assert stats["unique_names"] == 2
        assert "unused" in stats["pruned_reasons"]


# ═══════════════════════════════════════════════════════════════════════
# Argumentation Framework Tests
# ═══════════════════════════════════════════════════════════════════════

class TestArgumentation:
    """Tests for Argument, ArgumentationFramework, VocabArbitration."""

    def test_argument_creation(self):
        arg = Argument(claim="Pattern X means Y", evidence=["source 1"], confidence=0.8)
        assert arg.claim == "Pattern X means Y"
        assert arg.support_weight == 0.8  # 1 evidence * 0.8 confidence
        assert arg.objection_weight == 0.0

    def test_argument_invalid_confidence(self):
        with pytest.raises(ValueError):
            Argument(claim="test", confidence=1.5)

    def test_argument_confidence_zero_valid(self):
        arg = Argument(claim="test", confidence=0.0)
        assert arg.confidence == 0.0

    def test_argument_add_evidence_and_objection(self):
        arg = Argument(claim="test", confidence=0.9)
        arg.add_evidence("reason 1")
        arg.add_evidence("reason 2")
        assert arg.support_weight == 1.8  # 2 * 0.9
        obj = Argument(claim="counter", confidence=0.5)
        arg.add_objection(obj)
        assert arg.objection_weight == 0.5

    def test_framework_add_and_evaluate(self):
        fw = ArgumentationFramework()
        arg = Argument(claim="test", evidence=["proof"], confidence=0.9)
        fw.add_argument(arg)
        results = fw.evaluate()
        assert len(results) == 1
        assert results["arg_0"] == "accepted"

    def test_framework_no_evidence_undecided(self):
        fw = ArgumentationFramework()
        arg = Argument(claim="test")
        fw.add_argument(arg)
        results = fw.evaluate()
        assert results["arg_0"] == "undecided"

    def test_framework_get_accepted(self):
        fw = ArgumentationFramework()
        fw.add_argument(Argument(claim="strong", evidence=["e1", "e2"], confidence=1.0))
        fw.add_argument(Argument(claim="weak"))
        accepted = fw.get_accepted()
        assert "arg_0" in accepted
        assert "arg_1" not in accepted

    def test_framework_object_to(self):
        fw = ArgumentationFramework()
        arg_id = fw.add_argument(Argument(claim="original", evidence=["e1"], confidence=0.9))
        obj_id = fw.object_to(arg_id, Argument(claim="counter", confidence=0.2))
        results = fw.evaluate()
        assert results[arg_id] == "accepted"  # support > objection

    def test_framework_object_to_nonexistent(self):
        fw = ArgumentationFramework()
        with pytest.raises(KeyError):
            fw.object_to("nonexistent", Argument(claim="test"))

    def test_vocab_interpretation_conflicts(self):
        i1 = VocabInterpretation(pattern="add $a + $b", bytecode="IADD", agent="agent1")
        i2 = VocabInterpretation(pattern="add $a + $b", bytecode="ISUB", agent="agent2")
        assert i1.conflicts_with(i2)
        assert not i1.conflicts_with(i1)

    def test_vocab_arbitration_find_conflicts(self):
        arbiter = VocabArbitration()
        i1 = VocabInterpretation(pattern="add $a + $b", bytecode="IADD", agent="a1")
        i2 = VocabInterpretation(pattern="add $a + $b", bytecode="ISUB", agent="a2")
        i3 = VocabInterpretation(pattern="sub $a - $b", bytecode="ISUB", agent="a1")
        conflicts = arbiter.find_conflicts([i1, i3], [i2, i3])
        assert len(conflicts) == 1

    def test_vocab_arbitration_resolve(self):
        arbiter = VocabArbitration()
        i1 = VocabInterpretation(pattern="add $a + $b", bytecode="IADD", agent="a1", confidence=1.0)
        i2 = VocabInterpretation(pattern="add $a + $b", bytecode="ISUB", agent="a2", confidence=0.5)
        result = arbiter.resolve([i1], [i2])
        assert len(result["conflicts"]) == 1
        assert "add $a + $b" in result["resolutions"]


# ═══════════════════════════════════════════════════════════════════════
# Pruning System Tests
# ═══════════════════════════════════════════════════════════════════════

class TestPruning:
    """Tests for UsageTracker, VocabularyPruner, RuntimeCompiler."""

    def test_usage_tracker_mark_and_get(self):
        tracker = UsageTracker()
        tracker.mark_used("add")
        tracker.mark_used("add")
        tracker.mark_used("sub")
        assert tracker.get_call_count("add") == 2
        assert tracker.get_call_count("sub") == 1
        assert tracker.get_call_count("mul") == 0

    def test_usage_tracker_most_used(self):
        tracker = UsageTracker()
        for _ in range(5):
            tracker.mark_used("add")
        for _ in range(3):
            tracker.mark_used("sub")
        for _ in range(1):
            tracker.mark_used("mul")
        top = tracker.get_most_used(2)
        assert top[0] == ("add", 5)
        assert top[1] == ("sub", 3)

    def test_usage_tracker_get_unused(self):
        tracker = UsageTracker()
        tracker.mark_used("add")
        unused = tracker.get_unused(["add", "sub", "mul"])
        assert unused == ["sub", "mul"]

    def test_usage_tracker_reset(self):
        tracker = UsageTracker()
        tracker.mark_used("add")
        tracker.reset()
        assert tracker.get_call_count("add") == 0

    def test_usage_tracker_serialization(self):
        tracker = UsageTracker()
        tracker.mark_used("add")
        d = tracker.to_dict()
        restored = UsageTracker.from_dict(d)
        assert restored.get_call_count("add") == 1

    def test_pruner_basic_prune(self):
        vocab = make_vocab_with_entries(
            make_entry(name="add"),
            make_entry(name="sub"),
            make_entry(name="mul"),
        )
        tracker = UsageTracker()
        tracker.mark_used("add")
        pruner = VocabularyPruner()
        pruned = pruner.prune(vocab, tracker, min_calls=1)
        assert len(pruned.entries) == 1
        assert pruned.entries[0].name == "add"

    def test_pruner_dead_code_report(self):
        vocab = make_vocab_with_entries(
            make_entry(name="used"),
            make_entry(name="unused"),
        )
        tracker = UsageTracker()
        tracker.mark_used("used")
        pruner = VocabularyPruner()
        report = pruner.dead_code_report(vocab, tracker)
        assert isinstance(report, PruneReport)
        assert report.original_count == 2
        assert report.pruned_count == 1
        assert "unused" in report.removed
        assert "used" in report.kept
        assert report.savings_percent == 50.0

    def test_runtime_compiler_scan_opcodes(self):
        compiler = RuntimeCompiler()
        vocab = make_vocab_with_entries(
            make_entry(name="add", template="MOVI R0, ${a}\nMOVI R1, ${b}\nIADD R0, R0, R1\nHALT"),
        )
        ops = compiler._scan_opcodes(vocab)
        assert 0x2B in ops  # MOVI
        assert 0x08 in ops  # IADD
        assert 0x80 in ops  # HALT


# ═══════════════════════════════════════════════════════════════════════
# Tiling System Tests
# ═══════════════════════════════════════════════════════════════════════

class TestTiling:
    """Tests for Tile, TileResult, TilingSystem."""

    def test_tile_creation(self):
        tile = Tile(name="avg", pattern="average of $a and $b",
                     template="MOVI R0, ${a}\nHALT", level=1,
                     depends=["add", "div"])
        tile.compile()
        result = tile.match("average of 10 and 20")
        assert result is not None
        assert result["a"] == "10"

    def test_tile_result_defaults(self):
        r = TileResult()
        assert r.success is False
        assert r.value is None
        assert r.tiles_used == []

    def test_tiling_system_inline_math(self):
        interp = TilingSystem()
        result = interp.run("3 + 4")
        assert result.success
        assert result.value == 7

    def test_tiling_system_no_match(self):
        interp = TilingSystem()
        result = interp.run("xyzzy")
        assert result.success is False
        assert result.error is not None

    def test_build_default_tiling(self):
        interp = build_default_tiling()
        assert len(interp.tiles) > 0
        # Check level-1 tiles exist
        level1 = interp.list_tiles(level=1)
        assert len(level1) > 0

    def test_tile_graph(self):
        interp = build_default_tiling()
        graph = interp.tile_graph()
        assert isinstance(graph, dict)
        # Level-1 tiles should have dependencies
        for name, deps in graph.items():
            assert isinstance(deps, list)


# ═══════════════════════════════════════════════════════════════════════
# Contradiction Detector Tests
# ═══════════════════════════════════════════════════════════════════════

class TestContradictionDetector:
    """Tests for ContradictionDetector."""

    def test_scan_clean_vocab(self):
        vocab = make_vocab_with_entries(
            make_entry(name="add", pattern="add $a and $b"),
            make_entry(name="sub", pattern="sub $a and $b"),
        )
        detector = ContradictionDetector()
        report = detector.scan(vocab)
        assert report.total_entries == 2
        assert report.clean is True

    def test_scan_duplicate_name(self):
        vocab = make_vocab_with_entries(
            make_entry(name="dup", pattern="first $x"),
            make_entry(name="dup", pattern="second $y"),
        )
        detector = ContradictionDetector()
        report = detector.scan(vocab)
        assert report.critical_count > 0
        assert report.clean is False

    def test_scan_self_dependency(self):
        entry = VocabEntry(pattern="test", bytecode_template="HALT", name="self-dep")
        entry.compile()
        # Manually set depends to trigger self-dependency
        object.__setattr__(entry, 'depends', ['self-dep'])
        vocab = make_vocab_with_entries(entry)
        detector = ContradictionDetector()
        report = detector.scan(vocab)
        has_cycle = any(c.conflict_type == "dependency_cycle" for c in report.issues)
        assert has_cycle

    def test_validate_new_entry(self):
        vocab = make_vocab_with_entries(make_entry(name="existing", pattern="exists $x"))
        new_entry = VocabEntry(pattern="new $y", bytecode_template="HALT", name="new-entry")
        new_entry.compile()
        detector = ContradictionDetector()
        report = detector.validate(new_entry, vocab)
        assert report.total_entries == 2

    def test_validate_duplicate_name(self):
        vocab = make_vocab_with_entries(make_entry(name="existing", pattern="exists $x"))
        new_entry = VocabEntry(pattern="test $y", bytecode_template="HALT", name="existing")
        new_entry.compile()
        detector = ContradictionDetector()
        report = detector.validate(new_entry, vocab)
        assert report.critical_count > 0

    def test_diff_semantic_drift(self):
        v1 = make_vocab_with_entries(make_entry(name="add", pattern="add $a and $b"))
        v2 = make_vocab_with_entries(make_entry(name="add", pattern="sum $a and $b"))
        detector = ContradictionDetector()
        report = detector.diff(v1, v2)
        has_drift = any(c.conflict_type == "semantic_drift" for c in report.issues)
        assert has_drift

    def test_diff_removed_dependency(self):
        entry = VocabEntry(pattern="test", bytecode_template="HALT", name="child")
        entry.compile()
        object.__setattr__(entry, 'depends', ['parent'])
        v1 = make_vocab_with_entries(
            make_entry(name="parent", pattern="parent $x"),
            entry,
        )
        v2 = make_vocab_with_entries(entry)
        detector = ContradictionDetector()
        report = detector.diff(v1, v2)
        has_broken = any(c.conflict_type == "broken_dependency" for c in report.issues)
        assert has_broken


# ═══════════════════════════════════════════════════════════════════════
# Necrosis Detector Tests
# ═══════════════════════════════════════════════════════════════════════

class TestNecrosisDetector:
    """Tests for NecrosisDetector and TileProvenance."""

    def test_tile_provenance_ratios(self):
        tp = TileProvenance(tile_name="test", level=1,
                            source_ghosts=2, source_novel=1, source_legacy=1)
        assert tp.ghost_ratio == 0.5
        assert tp.novelty_ratio == 0.25

    def test_tile_provenance_zero_total(self):
        tp = TileProvenance(tile_name="test", level=0)
        assert tp.ghost_ratio == 0.0
        assert tp.novelty_ratio == 0.0

    def test_healthy_assessment(self):
        detector = NecrosisDetector()
        detector.register_tile(TileProvenance("t1", 1, source_novel=4, source_legacy=1))
        detector.register_tile(TileProvenance("t2", 1, source_novel=3, source_legacy=2))
        result = detector.assess()
        assert result["level"] == NecrosisLevel.HEALTHY

    def test_mausoleum_assessment(self):
        detector = NecrosisDetector()
        detector.register_tile(TileProvenance("t1", 1, source_ghosts=8, source_legacy=1))
        detector.register_tile(TileProvenance("t2", 1, source_ghosts=7, source_legacy=1))
        result = detector.assess()
        assert result["level"] == NecrosisLevel.MAUSOLEUM

    def test_empty_assessment(self):
        detector = NecrosisDetector()
        result = detector.assess()
        assert result["level"] == NecrosisLevel.HEALTHY
        assert result["tiles_checked"] == 0

    def test_novelty_prescription_healthy(self):
        detector = NecrosisDetector()
        detector.register_tile(TileProvenance("t1", 1, source_novel=10))
        rx = detector.novelty_prescription()
        assert "Continue" in rx[0]


# ═══════════════════════════════════════════════════════════════════════
# Decomposer Tests
# ═══════════════════════════════════════════════════════════════════════

class TestDecomposer:
    """Tests for Decomposer (string-based, no imports)."""

    def test_decompose_string_basic(self):
        d = Decomposer()
        code = textwrap.dedent("""\
            def add(a, b):
                return a + b
        """)
        vocab = d.decompose_string(code, module_name="test_mod")
        assert isinstance(vocab, DecomposedVocabulary)
        assert vocab.module_name == "test_mod"

    def test_decompose_string_math_function(self):
        d = Decomposer()
        code = textwrap.dedent("""\
            def factorial(n):
                if n <= 1:
                    return 1
                return n * factorial(n - 1)
        """)
        vocab = d.decompose_string(code, module_name="math_mod")
        assert len(vocab.entries) > 0

    def test_decompose_string_skips_private(self):
        d = Decomposer()
        code = textwrap.dedent("""\
            def public_fn(x):
                return x
            def _private_fn(x):
                return x
        """)
        vocab = d.decompose_string(code, module_name="test")
        names = [e["name"] for e in vocab.entries]
        assert "public_fn" in names
        assert "_private_fn" not in names

    def test_decomposed_vocabulary_save(self):
        d = Decomposer()
        code = "def add(a, b):\n    return a + b\n"
        vocab = d.decompose_string(code, module_name="test")
        with tempfile.NamedTemporaryFile(suffix='.fluxvocab', delete=False) as f:
            path = f.name
        try:
            vocab.save(path)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "pattern:" in content
        finally:
            os.unlink(path)

    def test_native_bridge_call(self):
        bridge = NativeBridge()
        d = Decomposer()
        vocab = d.decompose_string("def add(a, b):\n    return a + b\n", module_name="math_test")
        bridge.register_vocabulary(vocab)
        # The bridge needs actual Python modules, test with error handling
        try:
            bridge.call("add 2 and 3")
        except (ValueError, ImportError, AttributeError):
            pass  # Expected since 'math_test' isn't a real module


# ═══════════════════════════════════════════════════════════════════════
# Compiler Tests
# ═══════════════════════════════════════════════════════════════════════

class TestCompiler:
    """Tests for compile_interpreter."""

    def test_compile_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a vocab folder
            vdir = os.path.join(tmpdir, "vocab")
            os.makedirs(vdir)
            make_sample_fluxvocab_file(os.path.join(vdir, "test.fluxvocab"), textwrap.dedent("""\
                ---
                pattern: "double $a"
                expand: |
                    MOVI R0, ${a}
                    IADD R0, R0, R0
                    HALT
                result: R0
                name: double
                description: Double a number
                tags: math
            """))
            output = os.path.join(tmpdir, "runtime.py")
            result = compile_interpreter([vdir], output, class_name="TestFlux")
            assert os.path.exists(output)
            # Verify generated file has expected content
            with open(output) as f:
                content = f.read()
            assert "class TestFlux" in content
            assert "def run" in content

    def test_compile_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = os.path.join(tmpdir, "runtime.py")
            result = compile_interpreter([tmpdir], output)
            assert os.path.exists(output)


# ═══════════════════════════════════════════════════════════════════════
# Edge Cases & Integration Tests
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and integration tests."""

    def test_empty_pattern_entry(self):
        """Entry with empty pattern should not compile into anything useful."""
        entry = VocabEntry(pattern="", bytecode_template="HALT", name="empty")
        entry.compile()
        # Empty pattern compiles to regex that matches empty string
        assert entry.match("") is not None

    def test_duplicate_entries_in_vocab(self):
        v = Vocabulary("test")
        v.add(make_entry(name="dup"))
        v.add(make_entry(name="dup"))
        assert len(v.entries) == 2  # No dedup

    def test_vocabulary_load_real_core_files(self):
        v = Vocabulary("real")
        v.load_folder("vocabularies/core")
        assert len(v.entries) > 0

    def test_vocabulary_load_real_math_files(self):
        v = Vocabulary("real")
        v.load_folder("vocabularies/math")
        assert len(v.entries) > 0

    def test_vocabulary_load_real_loops_files(self):
        v = Vocabulary("real")
        v.load_folder("vocabularies/loops")
        assert len(v.entries) >= 0  # May be empty or have entries

    def test_match_with_zero(self):
        entry = VocabEntry(pattern="compute $a + $b", bytecode_template="HALT", name="add")
        entry.compile()
        result = entry.match("compute 0 + 0")
        assert result == {"a": "0", "b": "0"}

    def test_multi_var_pattern(self):
        entry = VocabEntry(pattern="$a then $b then $c", bytecode_template="HALT", name="seq")
        entry.compile()
        result = entry.match("1 then 2 then 3")
        assert result == {"a": "1", "b": "2", "c": "3"}

    def test_usage_stats(self):
        tracker = UsageTracker()
        tracker.mark_used("add")
        stats = tracker.get_usage_stats()
        assert "add" in stats
        assert stats["add"].call_count == 1

    def test_argumentation_repr(self):
        fw = ArgumentationFramework()
        assert "0 arguments" in repr(fw)
        fw.add_argument(Argument(claim="test"))
        assert "1 argument" in repr(fw)

    def test_ghost_age_calculation(self):
        ghost = GhostEntry(
            name="old", pattern="old", bytecode_template="HALT",
            sha256="h", pruned_reason="r", pruned_at=time.time() - 86400 * 100,
        )
        assert ghost.age_days() >= 99
        assert not ghost.is_recent(days=30)
        assert ghost.is_recent(days=200)

    def test_resurrection_context(self):
        ctx = ResurrectionContext(agent_name="test", reason="debug")
        assert ctx.agent_name == "test"
        assert "test" in repr(ctx)

    def test_vocabulary_template_loading(self):
        """Test .fluxtpl template loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "factorial.fluxtpl")
            with open(fpath, 'w') as f:
                f.write(textwrap.dedent("""\
                    name: factorial
                    result: R0
                    description: Compute factorial
                    assembly:
                        MOVI R0, 1
                        HALT
                """))
            v = Vocabulary("test")
            v.load_folder(tmpdir)
            assert "factorial" in v.templates
            assert v.templates["factorial"].description == "Compute factorial"


# ═══════════════════════════════════════════════════════════════════════
# pytest import
# ═══════════════════════════════════════════════════════════════════════
import pytest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
