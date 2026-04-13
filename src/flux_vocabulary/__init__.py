"""FLUX Vocabulary Library — Standalone vocabulary system for FLUX multi-agent communication.

This library provides:
- Complete FLUX opcode table (247 defined opcodes across 23 categories)
- Register file definitions (R0-R15, F0-F15, V0-V15)
- Instruction format specifications (Formats A through G)
- .fluxvocab file parser with validation
- Export to JSON, TOML, and Python dict

Usage:
    from flux_vocabulary import get_isa, get_register_file_dict, FluxVocabParser

    # Get all 247 opcodes
    opcodes = get_isa()
    stats = isa_stats()

    # Parse .fluxvocab files
    parser = FluxVocabParser()
    entries = parser.parse_file("vocabularies/core/basic.fluxvocab")

    # Validate entries
    from flux_vocabulary import VocabValidator
    validator = VocabValidator()
    errors = validator.validate_vocabulary(entries)

    # Export to JSON
    from flux_vocabulary import export_entries_json
    json_str = export_entries_json(entries)
"""

from .parser import (
    VocabEntry,
    BytecodeTemplate,
    FluxVocabParser,
    VocabValidator,
    ValidationError,
    VOCAB_MNEMONICS,
)
from .opcodes import (
    OpcodeDef,
    build_unified_isa,
    get_isa,
    get_opcode_by_code,
    get_opcode_by_mnemonic,
    get_opcodes_by_category,
    isa_stats,
    OPCODE_CATEGORIES,
    FORMAT_DESCRIPTIONS,
    SOURCE_LABELS,
    _FORMAT_SIZES,
)
from .registers import (
    RegisterDef,
    RegisterBank,
    build_gp_bank,
    build_fp_bank,
    build_vec_bank,
    get_all_banks,
    get_register_file_dict,
    GP_COUNT,
    FP_COUNT,
    VEC_COUNT,
    SP_INDEX,
    FP_INDEX,
    LR_INDEX,
)
from .formats import (
    FormatSpec,
    build_formats,
    get_format,
    get_all_formats_dict,
)
from .exporter import (
    export_entries_json,
    export_opcodes_json,
    export_registers_json,
    export_formats_json,
    export_full_vocabulary_json,
    export_entries_toml,
    export_entries_dict,
    export_opcodes_dict,
    export_registers_dict,
    export_formats_dict,
    export_full_vocabulary_dict,
    save_json,
    save_toml,
)
from .vocabulary import Vocabulary
from .vocab_signal import VocabManifest

__version__ = "0.2.0"

__all__ = [
    # Parser
    "VocabEntry", "BytecodeTemplate", "FluxVocabParser",
    "VocabValidator", "ValidationError", "VOCAB_MNEMONICS",
    # Opcodes
    "OpcodeDef", "build_unified_isa", "get_isa",
    "get_opcode_by_code", "get_opcode_by_mnemonic",
    "get_opcodes_by_category", "isa_stats",
    "OPCODE_CATEGORIES", "FORMAT_DESCRIPTIONS", "SOURCE_LABELS", "_FORMAT_SIZES",
    # Registers
    "RegisterDef", "RegisterBank",
    "build_gp_bank", "build_fp_bank", "build_vec_bank",
    "get_all_banks", "get_register_file_dict",
    "GP_COUNT", "FP_COUNT", "VEC_COUNT",
    "SP_INDEX", "FP_INDEX", "LR_INDEX",
    # Formats
    "FormatSpec", "build_formats", "get_format", "get_all_formats_dict",
    # Exporter
    "export_entries_json", "export_opcodes_json",
    "export_registers_json", "export_formats_json",
    "export_full_vocabulary_json",
    "export_entries_toml",
    "export_entries_dict", "export_opcodes_dict",
    "export_registers_dict", "export_formats_dict",
    "export_full_vocabulary_dict",
    "save_json", "save_toml",
    # Vocabulary & Signal
    "Vocabulary", "VocabManifest",
]
