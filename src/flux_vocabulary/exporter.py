"""
FLUX Vocabulary Exporter.

Exports vocabulary definitions (entries, opcodes, registers, formats)
to multiple formats: JSON, TOML, and Python dict.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .parser import VocabEntry, BytecodeTemplate


# ══════════════════════════════════════════════════════════════════════════════
# JSON Export
# ══════════════════════════════════════════════════════════════════════════════

def export_entries_json(
    entries: List[VocabEntry],
    indent: int = 2,
    include_patterns: bool = True,
) -> str:
    """Export vocabulary entries to JSON string."""
    data = {
        "version": "1.0",
        "entry_count": len(entries),
        "entries": [e.to_dict() for e in entries],
    }
    if include_patterns:
        data["patterns"] = [e.pattern for e in entries]
        data["tags_summary"] = _summarize_tags(entries)
    return json.dumps(data, indent=indent, default=str)


def export_opcodes_json(opcodes: List[Any], indent: int = 2) -> str:
    """Export opcode definitions to JSON string."""
    data = {
        "version": "1.0",
        "opcode_count": len(opcodes),
        "opcodes": [op.to_dict() for op in opcodes],
    }
    return json.dumps(data, indent=indent, default=str)


def export_registers_json(registers: Dict[str, Any], indent: int = 2) -> str:
    """Export register file definition to JSON string."""
    return json.dumps(registers, indent=indent, default=str)


def export_formats_json(formats: List[Any], indent: int = 2) -> str:
    """Export instruction format specs to JSON string."""
    data = {
        "version": "1.0",
        "format_count": len(formats),
        "formats": [f.to_dict() for f in formats],
    }
    return json.dumps(data, indent=indent, default=str)


def export_full_vocabulary_json(
    entries: List[VocabEntry],
    opcodes: List[Any],
    registers: Dict[str, Any],
    formats: List[Any],
    indent: int = 2,
) -> str:
    """Export the complete vocabulary library to JSON."""
    data = {
        "version": "1.0",
        "vocab_entries": {
            "count": len(entries),
            "entries": [e.to_dict() for e in entries],
            "tags_summary": _summarize_tags(entries),
        },
        "opcodes": {
            "count": len(opcodes),
            "opcodes": [op.to_dict() for op in opcodes],
            "stats": _opcode_stats(opcodes),
        },
        "registers": registers,
        "formats": [f.to_dict() for f in formats],
    }
    return json.dumps(data, indent=indent, default=str)


# ══════════════════════════════════════════════════════════════════════════════
# TOML Export
# ══════════════════════════════════════════════════════════════════════════════

def _toml_escape(s: str) -> str:
    """Escape a string for TOML double-quoted value."""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def export_entries_toml(entries: List[VocabEntry]) -> str:
    """Export vocabulary entries to TOML string."""
    lines = [
        '# FLUX Vocabulary Export',
        'version = "1.0"',
        f'entry_count = {len(entries)}',
        '',
    ]

    for i, entry in enumerate(entries):
        name = entry.name or f"entry_{i}"
        safe_name = reformat_toml_key(name)
        lines.append(f'[[entries]]')
        lines.append(f'name = "{_toml_escape(entry.name)}"')
        lines.append(f'pattern = "{_toml_escape(entry.pattern)}"')
        lines.append(f'expand = """')
        lines.append(entry.expand)
        lines.append('"""')
        lines.append(f'result_reg = {entry.result_reg}')
        if entry.tags:
            tags_toml = ", ".join(f'"{t}"' for t in entry.tags)
            lines.append(f'tags = [{tags_toml}]')
        if entry.description:
            lines.append(f'description = "{_toml_escape(entry.description)}"')
        lines.append('')

    return '\n'.join(lines)


def reformat_toml_key(name: str) -> str:
    """Format a name for use as a TOML table key."""
    return name.lower().replace(' ', '-').replace('_', '-')


# ══════════════════════════════════════════════════════════════════════════════
# Python Dict Export
# ══════════════════════════════════════════════════════════════════════════════

def export_entries_dict(entries: List[VocabEntry]) -> Dict[str, Any]:
    """Export vocabulary entries as Python dictionary."""
    return {
        "version": "1.0",
        "entry_count": len(entries),
        "entries": [e.to_dict() for e in entries],
        "patterns": [e.pattern for e in entries],
        "tags_summary": _summarize_tags(entries),
    }


def export_opcodes_dict(opcodes: List[Any]) -> Dict[str, Any]:
    """Export opcode definitions as Python dictionary."""
    return {
        "version": "1.0",
        "opcode_count": len(opcodes),
        "opcodes": [op.to_dict() for op in opcodes],
        "by_mnemonic": {op.mnemonic: op.to_dict() for op in opcodes if not op.reserved},
        "stats": _opcode_stats(opcodes),
    }


def export_registers_dict(registers: Dict[str, Any]) -> Dict[str, Any]:
    """Export register definitions as Python dictionary."""
    return dict(registers)


def export_formats_dict(formats: List[Any]) -> Dict[str, Any]:
    """Export format specs as Python dictionary."""
    return {
        "version": "1.0",
        "formats": {f.letter: f.to_dict() for f in formats},
    }


def export_full_vocabulary_dict(
    entries: List[VocabEntry],
    opcodes: List[Any],
    registers: Dict[str, Any],
    formats: List[Any],
) -> Dict[str, Any]:
    """Export the complete vocabulary library as Python dictionary."""
    return {
        "version": "1.0",
        "vocab_entries": export_entries_dict(entries),
        "opcodes": export_opcodes_dict(opcodes),
        "registers": export_registers_dict(registers),
        "formats": export_formats_dict(formats),
    }


# ══════════════════════════════════════════════════════════════════════════════
# File-based export
# ══════════════════════════════════════════════════════════════════════════════

def save_json(data: str, path: str):
    """Write JSON string to file."""
    with open(path, 'w') as f:
        f.write(data)


def save_toml(data: str, path: str):
    """Write TOML string to file."""
    with open(path, 'w') as f:
        f.write(data)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _summarize_tags(entries: List[VocabEntry]) -> Dict[str, int]:
    """Count occurrences of each tag across all entries."""
    counts: Dict[str, int] = {}
    for e in entries:
        for t in e.tags:
            counts[t] = counts.get(t, 0) + 1
    return dict(sorted(counts.items()))


def _opcode_stats(opcodes: List[Any]) -> Dict[str, Any]:
    """Generate opcode statistics."""
    defined = [op for op in opcodes if not op.reserved]
    by_category: Dict[str, int] = {}
    by_source: Dict[str, int] = {}
    for op in defined:
        by_category[op.category] = by_category.get(op.category, 0) + 1
        by_source[op.source] = by_source.get(op.source, 0) + 1

    return {
        "defined": len(defined),
        "reserved": len(opcodes) - len(defined),
        "confidence_ops": len([op for op in defined if op.confidence]),
        "by_category": by_category,
        "by_source": by_source,
    }
