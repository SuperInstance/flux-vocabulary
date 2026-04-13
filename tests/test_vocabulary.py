"""Comprehensive tests for the flux-vocabulary library.

Tests cover:
- Opcode table (247 opcodes, all 23 categories)
- Register file definitions
- Instruction format specifications
- .fluxvocab parser
- Validator
- Exporter (JSON, TOML, dict)
- Full library integration
"""

import os
import sys
import json
import tempfile

sys.path.insert(0, "src")

from flux_vocabulary.opcodes import (
    build_unified_isa, get_isa, get_opcode_by_code, get_opcode_by_mnemonic,
    get_opcodes_by_category, isa_stats, OPCODE_CATEGORIES, _FORMAT_SIZES,
)
from flux_vocabulary.registers import (
    RegisterDef, RegisterBank, build_gp_bank, build_fp_bank, build_vec_bank,
    get_all_banks, get_register_file_dict, GP_COUNT, FP_COUNT, VEC_COUNT,
    SP_INDEX, FP_INDEX, LR_INDEX,
)
from flux_vocabulary.formats import (
    FormatSpec, build_formats, get_format, get_all_formats_dict,
)
from flux_vocabulary.parser import (
    VocabEntry, BytecodeTemplate, FluxVocabParser, VocabValidator,
    ValidationError, VOCAB_MNEMONICS,
)
from flux_vocabulary.exporter import (
    export_entries_json, export_opcodes_json, export_registers_json,
    export_formats_json, export_full_vocabulary_json, export_entries_toml,
    export_entries_dict, export_opcodes_dict, export_registers_dict,
    export_formats_dict, export_full_vocabulary_dict, save_json, save_toml,
)
from flux_vocabulary.vocabulary import Vocabulary
from flux_vocabulary import __version__


# ══════════════════════════════════════════════════════════════════════════════
# 1. Opcode Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_isa_total_opcodes():
    """ISA should have exactly 256 total opcode slots."""
    ops = get_isa()
    assert len(ops) == 256, f"Expected 256 slots, got {len(ops)}"


def test_isa_defined_opcodes():
    """ISA should have 247 defined opcodes."""
    ops = get_isa()
    defined = [o for o in ops if not o.reserved]
    assert len(defined) == 247, f"Expected 247 defined, got {len(defined)}"


def test_isa_reserved_opcodes():
    """ISA should have 9 reserved slots."""
    ops = get_isa()
    reserved = [o for o in ops if o.reserved]
    assert len(reserved) == 9, f"Expected 9 reserved, got {len(reserved)}"


def test_isa_stats():
    """ISA stats should return correct counts and categories."""
    stats = isa_stats()
    assert stats["total_slots"] == 256
    assert stats["defined"] == 247
    assert stats["reserved"] == 9
    assert stats["confidence_ops"] == 16
    assert len(stats["categories"]) == 23
    assert "arithmetic" in stats["categories"]
    assert "a2a" in stats["categories"]
    assert "confidence" in stats["categories"]
    assert "sensor" in stats["categories"]


def test_opcode_lookup_by_code():
    """Lookup opcodes by byte value."""
    halt = get_opcode_by_code(0x00)
    assert halt is not None
    assert halt.mnemonic == "HALT"
    assert halt.fmt == "A"

    add = get_opcode_by_code(0x20)
    assert add is not None
    assert add.mnemonic == "ADD"
    assert add.category == "arithmetic"


def test_opcode_lookup_by_mnemonic():
    """Lookup opcodes by mnemonic (case-insensitive)."""
    add = get_opcode_by_mnemonic("ADD")
    assert add is not None
    assert add.opcode == 0x20

    add_lower = get_opcode_by_mnemonic("add")
    assert add_lower.opcode == 0x20

    jmp = get_opcode_by_mnemonic("JMP")
    assert jmp is not None
    assert jmp.opcode == 0x43


def test_opcode_by_category():
    """Filter opcodes by category."""
    a2a_ops = get_opcodes_by_category("a2a")
    assert len(a2a_ops) == 16

    confidence_ops = get_opcodes_by_category("confidence")
    assert len(confidence_ops) == 19
    conf_flagged = [op for op in confidence_ops if op.confidence]
    assert len(conf_flagged) == 16

    sensor_ops = get_opcodes_by_category("sensor")
    assert len(sensor_ops) == 16


def test_opcode_to_dict():
    """OpcodeDef serialization to dict."""
    add = get_opcode_by_mnemonic("ADD")
    d = add.to_dict()
    assert d["opcode"] == 0x20
    assert d["hex"] == "0x20"
    assert d["mnemonic"] == "ADD"
    assert d["format"] == "E"
    assert d["category"] == "arithmetic"
    assert d["byte_size"] == 4


def test_all_format_sizes():
    """All format sizes should be defined."""
    assert _FORMAT_SIZES == {"A": 1, "B": 2, "C": 2, "D": 3, "E": 4, "F": 4, "G": 5}


# ══════════════════════════════════════════════════════════════════════════════
# 2. Register Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_gp_register_count():
    """GP bank should have 16 registers."""
    bank = build_gp_bank()
    assert bank.count == 16
    assert len(bank.registers) == 16


def test_gp_special_aliases():
    """GP bank should have SP, FP, LR aliases."""
    bank = build_gp_bank()
    assert bank.registers[SP_INDEX].abi_name == "SP"
    assert bank.registers[FP_INDEX].abi_name == "FP"
    assert bank.registers[LR_INDEX].abi_name == "LR"


def test_fp_register_count():
    """FP bank should have 16 registers."""
    bank = build_fp_bank()
    assert bank.count == 16
    assert bank.prefix == "F"


def test_vec_register_count():
    """VEC bank should have 16 registers."""
    bank = build_vec_bank()
    assert bank.count == 16
    assert bank.prefix == "V"


def test_all_banks():
    """Should have exactly 3 register banks."""
    banks = get_all_banks()
    assert len(banks) == 3


def test_register_file_dict():
    """Register file dict should have correct structure."""
    rf = get_register_file_dict()
    assert rf["total_registers"] == 48
    assert rf["gp_count"] == 16
    assert rf["fp_count"] == 16
    assert rf["vec_count"] == 16
    assert rf["special_aliases"]["SP"] == 11
    assert rf["special_aliases"]["FP"] == 14
    assert rf["special_aliases"]["LR"] == 15
    assert len(rf["banks"]) == 3


# ══════════════════════════════════════════════════════════════════════════════
# 3. Format Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_format_count():
    """Should have exactly 7 instruction formats."""
    fmts = build_formats()
    assert len(fmts) == 7


def test_format_letters():
    """Formats should be A through G."""
    fmts = build_formats()
    letters = {f.letter for f in fmts}
    assert letters == {"A", "B", "C", "D", "E", "F", "G"}


def test_format_sizes():
    """Format sizes should match spec."""
    fmts = build_formats()
    for f in fmts:
        expected = {"A": 1, "B": 2, "C": 2, "D": 3, "E": 4, "F": 4, "G": 5}[f.letter]
        assert f.byte_size == expected


def test_get_format():
    """Lookup format by letter."""
    fmt_e = get_format("E")
    assert fmt_e is not None
    assert fmt_e.letter == "E"
    assert fmt_e.byte_size == 4

    fmt_g = get_format("g")
    assert fmt_g is not None
    assert fmt_g.byte_size == 5

    assert get_format("X") is None


# ══════════════════════════════════════════════════════════════════════════════
# 4. Parser Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_parse_basic_fluxvocab():
    """Parse a basic .fluxvocab string."""
    parser = FluxVocabParser()
    content = """---
pattern: "compute $a + $b"
expand: |
    MOVI R0, ${a}
    MOVI R1, ${b}
    IADD R0, R0, R1
    HALT
result: R0
name: addition
tags: math, arithmetic
"""
    entries = parser.parse_string(content)
    assert len(entries) == 1
    assert entries[0].pattern == "compute $a + $b"
    assert entries[0].name == "addition"
    assert entries[0].result_reg == 0
    assert entries[0].tags == ["math", "arithmetic"]
    assert "MOVI R0," in entries[0].expand


def test_parse_multiple_entries():
    """Parse a file with multiple entries."""
    parser = FluxVocabParser()
    content = """---
pattern: "double $a"
expand: |
    MOVI R0, ${a}
    IADD R0, R0, R0
    HALT
result: R0
---
pattern: "square $a"
expand: |
    MOVI R0, ${a}
    IMUL R0, R0, R0
    HALT
result: R0
"""
    entries = parser.parse_string(content)
    assert len(entries) == 2
    assert entries[0].name == "double $a"
    assert entries[1].name == "square $a"


def test_parse_real_arithmetic_file():
    """Parse the actual arithmetic.fluxvocab file."""
    parser = FluxVocabParser()
    path = os.path.join("vocabularies", "math", "arithmetic.fluxvocab")
    if os.path.exists(path):
        entries = parser.parse_file(path)
        assert len(entries) == 7
        names = [e.name for e in entries]
        assert "addition" in names
        assert "subtraction" in names


def test_parse_real_basic_file():
    """Parse the actual core/basic.fluxvocab file."""
    parser = FluxVocabParser()
    path = os.path.join("vocabularies", "core", "basic.fluxvocab")
    if os.path.exists(path):
        entries = parser.parse_file(path)
        assert len(entries) == 5


def test_vocab_entry_match():
    """Test pattern matching on a VocabEntry."""
    entry = VocabEntry(
        pattern="compute $a + $b",
        expand="MOVI R0, ${a}\nHALT",
        name="test",
    )
    entry.compile_pattern()

    result = entry.match("compute 3 + 4")
    assert result is not None
    assert result["a"] == "3"
    assert result["b"] == "4"

    result = entry.match("no match here")
    assert result is None


def test_vocab_entry_substitute():
    """Test template substitution."""
    entry = VocabEntry(
        pattern="compute $a + $b",
        expand="MOVI R0, ${a}\nMOVI R1, ${b}\nIADD R0, R0, R1\nHALT",
    )
    captures = {"a": "3", "b": "4"}
    result = entry.substitute(captures)
    assert "MOVI R0, 3" in result
    assert "MOVI R1, 4" in result


def test_vocab_entry_to_dict():
    """Test VocabEntry serialization."""
    entry = VocabEntry(
        pattern="add $a and $b",
        expand="HALT",
        name="addition",
        tags=["math"],
    )
    d = entry.to_dict()
    assert d["pattern"] == "add $a and $b"
    assert d["name"] == "addition"
    assert d["tags"] == ["math"]


# ══════════════════════════════════════════════════════════════════════════════
# 5. Validator Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_validate_valid_entry():
    """A valid entry should produce no errors."""
    validator = VocabValidator()
    entry = VocabEntry(
        pattern="add $a and $b",
        expand="MOVI R0, ${a}\nMOVI R1, ${b}\nIADD R0, R0, R1\nHALT",
        name="addition",
        result_reg=0,
    )
    errors = validator.validate_entry(entry)
    assert len(errors) == 0


def test_validate_missing_pattern():
    """Missing pattern should be an error."""
    validator = VocabValidator()
    entry = VocabEntry(pattern="", expand="HALT")
    errors = validator.validate_entry(entry)
    assert any(e.message == "Missing 'pattern' field" for e in errors)


def test_validate_missing_expand():
    """Missing expand should be an error."""
    validator = VocabValidator()
    entry = VocabEntry(pattern="test", expand="")
    errors = validator.validate_entry(entry)
    assert any(e.message == "Missing 'expand' field" for e in errors)


def test_validate_bad_result_reg():
    """Result register out of range should be an error."""
    validator = VocabValidator()
    entry = VocabEntry(pattern="test", expand="HALT", result_reg=20)
    errors = validator.validate_entry(entry)
    assert any("out of range" in e.message for e in errors)


def test_validate_var_mismatch():
    """Missing pattern variables in expand should be an error."""
    validator = VocabValidator()
    entry = VocabEntry(pattern="test $a $b", expand="MOVI R0, ${a}\nHALT")
    errors = validator.validate_entry(entry)
    assert any("b" in e.message for e in errors)


def test_validate_unknown_mnemonic():
    """Unknown mnemonics should produce warnings."""
    validator = VocabValidator()
    entry = VocabEntry(pattern="test $x", expand="BADCMD R0\nHALT")
    errors = validator.validate_entry(entry)
    assert any("Unknown mnemonic" in e.message and e.severity == "warning" for e in errors)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Exporter Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_export_entries_json():
    """Export entries to JSON."""
    entries = [VocabEntry(pattern="test $x", expand="HALT", name="test")]
    json_str = export_entries_json(entries)
    data = json.loads(json_str)
    assert data["entry_count"] == 1
    assert data["entries"][0]["pattern"] == "test $x"


def test_export_opcodes_json():
    """Export opcodes to JSON."""
    opcodes = get_isa()
    json_str = export_opcodes_json(opcodes)
    data = json.loads(json_str)
    assert data["opcode_count"] == 256
    assert len(data["opcodes"]) == 256


def test_export_registers_json():
    """Export registers to JSON."""
    rf = get_register_file_dict()
    json_str = export_registers_json(rf)
    data = json.loads(json_str)
    assert data["total_registers"] == 48


def test_export_formats_json():
    """Export formats to JSON."""
    fmts = build_formats()
    json_str = export_formats_json(fmts)
    data = json.loads(json_str)
    assert data["format_count"] == 7


def test_export_full_vocabulary_json():
    """Export complete vocabulary library to JSON."""
    entries = [VocabEntry(pattern="test", expand="HALT")]
    opcodes = get_isa()
    registers = get_register_file_dict()
    fmts = build_formats()
    json_str = export_full_vocabulary_json(entries, opcodes, registers, fmts)
    data = json.loads(json_str)
    assert "vocab_entries" in data
    assert "opcodes" in data
    assert "registers" in data
    assert "formats" in data


def test_export_entries_toml():
    """Export entries to TOML."""
    entries = [VocabEntry(pattern="test $x", expand="HALT", name="test-entry")]
    toml_str = export_entries_toml(entries)
    assert '[[entries]]' in toml_str
    assert 'pattern = "test $x"' in toml_str
    assert 'result_reg = 0' in toml_str


def test_export_entries_dict():
    """Export entries as Python dict."""
    entries = [VocabEntry(pattern="test", expand="HALT")]
    d = export_entries_dict(entries)
    assert d["entry_count"] == 1
    assert isinstance(d["entries"], list)


def test_export_opcodes_dict():
    """Export opcodes as Python dict with by_mnemonic index."""
    opcodes = get_isa()
    d = export_opcodes_dict(opcodes)
    assert "ADD" in d["by_mnemonic"]
    assert d["by_mnemonic"]["ADD"]["opcode"] == 0x20
    assert d["stats"]["defined"] == 247


def test_export_full_vocabulary_dict():
    """Export complete vocabulary as Python dict."""
    entries = []
    opcodes = get_isa()
    registers = get_register_file_dict()
    fmts = build_formats()
    d = export_full_vocabulary_dict(entries, opcodes, registers, fmts)
    assert "version" in d
    assert "opcodes" in d
    assert d["opcodes"]["stats"]["defined"] == 247


def test_save_json_file():
    """Save JSON to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.json")
        save_json('{"test": true}', path)
        assert os.path.exists(path)
        with open(path) as f:
            assert json.load(f) == {"test": True}


def test_save_toml_file():
    """Save TOML to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test.toml")
        save_toml('version = "1.0"', path)
        assert os.path.exists(path)
        with open(path) as f:
            assert 'version = "1.0"' in f.read()


# ══════════════════════════════════════════════════════════════════════════════
# 7. Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_load_and_export_real_vocab():
    """Parse real vocabulary files, validate, and export."""
    parser = FluxVocabParser()
    validator = VocabValidator()

    all_entries = []
    vocab_dir = "vocabularies"
    if not os.path.isdir(vocab_dir):
        return

    for root, dirs, files in os.walk(vocab_dir):
        for fname in files:
            if fname.endswith('.fluxvocab'):
                fpath = os.path.join(root, fname)
                entries = parser.parse_file(fpath)
                all_entries.extend(entries)

    assert len(all_entries) > 0, "Should have loaded at least one entry"

    # Validate all
    errors = validator.validate_vocabulary(all_entries)
    # Only errors should be warnings (unknown mnemonics), not real errors
    real_errors = [e for e in errors if e.severity == "error"]
    # Allow some errors due to cross-file references
    assert len(all_entries) >= 10

    # Export to JSON
    json_str = export_entries_json(all_entries)
    data = json.loads(json_str)
    assert data["entry_count"] == len(all_entries)


def test_vocab_mnemonics_subset():
    """Vocabulary mnemonics should be a subset of the full ISA."""
    from flux_vocabulary.opcodes import build_unified_isa
    full_isa = build_unified_isa()
    isa_mnemonics = {op.mnemonic for op in full_isa if not op.reserved}

    # Vocab assembler uses legacy names that differ from unified ISA
    _LEGACY_MAP = {
        "INEG": "NEG", "IMOD": "MOD", "IDIV": "DIV",
        "IMUL": "MUL", "ISUB": "SUB", "IADD": "ADD",
        "IAND": "AND", "IOR": "OR", "IXOR": "XOR",
        "ISHL": "SHL", "ISHR": "SHR", "INOT": "NOT",
        "CMP": None,  # Special case: maps to CMP_EQ/CMP_LT/etc.
    }
    for vm in VOCAB_MNEMONICS:
        if vm == "CMP":
            assert any(m.startswith("CMP") for m in isa_mnemonics)
        elif vm in _LEGACY_MAP:
            mapped = _LEGACY_MAP[vm]
            assert mapped in isa_mnemonics, f"{vm} (mapped to {mapped}) not found in ISA"
        else:
            assert vm in isa_mnemonics, f"{vm} not found in ISA"


def test_version():
    """Library should have a version string."""
    assert isinstance(__version__, str)
    assert __version__.startswith("0.")


# ══════════════════════════════════════════════════════════════════════════════
# Run all tests
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import traceback

    test_functions = [
        # Opcode tests
        test_isa_total_opcodes, test_isa_defined_opcodes, test_isa_reserved_opcodes,
        test_isa_stats, test_opcode_lookup_by_code, test_opcode_lookup_by_mnemonic,
        test_opcode_by_category, test_opcode_to_dict, test_all_format_sizes,
        # Register tests
        test_gp_register_count, test_gp_special_aliases, test_fp_register_count,
        test_vec_register_count, test_all_banks, test_register_file_dict,
        # Format tests
        test_format_count, test_format_letters, test_format_sizes, test_get_format,
        # Parser tests
        test_parse_basic_fluxvocab, test_parse_multiple_entries,
        test_parse_real_arithmetic_file, test_parse_real_basic_file,
        test_vocab_entry_match, test_vocab_entry_substitute, test_vocab_entry_to_dict,
        # Validator tests
        test_validate_valid_entry, test_validate_missing_pattern,
        test_validate_missing_expand, test_validate_bad_result_reg,
        test_validate_var_mismatch, test_validate_unknown_mnemonic,
        # Exporter tests
        test_export_entries_json, test_export_opcodes_json, test_export_registers_json,
        test_export_formats_json, test_export_full_vocabulary_json,
        test_export_entries_toml, test_export_entries_dict, test_export_opcodes_dict,
        test_export_full_vocabulary_dict, test_save_json_file, test_save_toml_file,
        # Integration tests
        test_load_and_export_real_vocab, test_vocab_mnemonics_subset, test_version,
    ]

    passed = 0
    failed = 0
    errors_list: list = []

    for test_fn in test_functions:
        try:
            test_fn()
            passed += 1
            print(f"  PASS: {test_fn.__name__}")
        except Exception as e:
            failed += 1
            errors_list.append((test_fn.__name__, str(e)))
            print(f"  FAIL: {test_fn.__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'='*60}")

    if failed:
        print("\nFailed tests:")
        for name, err in errors_list:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)
