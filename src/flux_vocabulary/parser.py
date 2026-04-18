"""
Enhanced .fluxvocab Parser and Validator.

Parses .fluxvocab files into structured VocabEntry objects, validates
them against the FLUX ISA, and provides error reporting.

See flux-spec/FLUXVOCAB.md for the format specification.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class VocabEntry:
    """A single vocabulary entry: pattern -> bytecode expansion."""
    pattern: str           # Raw pattern with $var placeholders
    expand: str            # Assembly template with ${var} substitution
    result_reg: int = 0    # Result register (0-15)
    name: str = ""         # Human-readable name
    description: str = ""  # What this word does
    tags: List[str] = field(default_factory=list)
    source_file: str = ""  # File this entry was loaded from

    # Compiled regex (built from pattern)
    _regex: Optional[re.Pattern] = field(default=None, repr=False)

    def compile_pattern(self):
        """Convert $var patterns to regex capture groups."""
        parts = re.split(r'(\$\w+)', self.pattern)
        regex_parts = []
        for part in parts:
            if part.startswith('$'):
                name = part[1:]
                regex_parts.append(f'(?P<{name}>\\d+)')
            else:
                regex_parts.append(re.escape(part))
        regex_str = ''.join(regex_parts).strip()
        self._regex = re.compile(regex_str, re.IGNORECASE)

    def match(self, text: str) -> Optional[Dict[str, str]]:
        """Try to match text against this pattern. Returns captured groups."""
        if self._regex is None:
            self.compile_pattern()
        m = self._regex.search(text)
        if m:
            return {k: v for k, v in m.groupdict().items() if v is not None}
        return None

    def substitute(self, captures: Dict[str, str]) -> str:
        """Substitute captured values into the assembly template."""
        result = self.expand
        for key, value in captures.items():
            result = result.replace(f"${{{key}}}", value)
        return result

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "pattern": self.pattern,
            "expand": self.expand,
            "result_reg": self.result_reg,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "source_file": self.source_file,
        }


@dataclass
class BytecodeTemplate:
    """A reusable bytecode template with parameters."""
    name: str
    assembly: str
    result_reg: int = 0
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "assembly": self.assembly,
            "result_reg": self.result_reg,
            "description": self.description,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Validation
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationError:
    """A single validation error."""
    message: str
    entry_name: str = ""
    line: int = 0
    severity: str = "error"  # "error" or "warning"

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "entry_name": self.entry_name,
            "line": self.line,
            "severity": self.severity,
        }


# Mnemonics supported by the vocabulary assembler (26-opcode subset)
VOCAB_MNEMONICS = frozenset({
    "NOP", "HALT", "RET", "YIELD",
    "INC", "DEC", "PUSH", "POP", "NOT", "INEG",
    "MOV",
    "MOVI", "JZ", "JNZ",
    "IADD", "ISUB", "IMUL", "IDIV", "IMOD",
    "AND", "OR", "XOR", "SHL", "SHR", "CMP",
})


class VocabValidator:
    """Validates VocabEntry objects against the FLUX vocabulary spec."""

    def validate_entry(self, entry: VocabEntry) -> List[ValidationError]:
        """Validate a single vocabulary entry."""
        errors: List[ValidationError] = []
        name = entry.name or entry.pattern[:30]

        # Check required fields
        if not entry.pattern:
            errors.append(ValidationError("Missing 'pattern' field", name, severity="error"))
        if not entry.expand:
            errors.append(ValidationError("Missing 'expand' field", name, severity="error"))

        # Check result register range
        if not (0 <= entry.result_reg <= 15):
            errors.append(ValidationError(
                f"Result register R{entry.result_reg} out of range (0-15)",
                name, severity="error"
            ))

        # Check pattern variable consistency
        if entry.pattern and entry.expand:
            pattern_vars = set(re.findall(r'\$(\w+)', entry.pattern))
            expand_vars = set(re.findall(r'\$\{(\w+)\}', entry.expand))
            missing = pattern_vars - expand_vars
            extra = expand_vars - pattern_vars
            if missing:
                errors.append(ValidationError(
                    f"Pattern variables {missing} not found in expand template",
                    name, severity="error"
                ))
            if extra:
                errors.append(ValidationError(
                    f"Expand variables {extra} not found in pattern",
                    name, severity="warning"
                ))

        # Check assembly mnemonics
        if entry.expand:
            for line in entry.expand.split('\n'):
                line = line.strip().split(';')[0].split('//')[0].split('#')[0].strip()
                if not line:
                    continue
                mnemonic = line.split()[0].upper()
                if mnemonic not in VOCAB_MNEMONICS:
                    errors.append(ValidationError(
                        f"Unknown mnemonic '{mnemonic}' in expand template",
                        name, severity="warning"
                    ))

        return errors

    def validate_vocabulary(self, entries: List[VocabEntry]) -> List[ValidationError]:
        """Validate all entries in a vocabulary."""
        all_errors: List[ValidationError] = []
        for entry in entries:
            all_errors.extend(self.validate_entry(entry))
        return all_errors


# ══════════════════════════════════════════════════════════════════════════════
# Parser
# ══════════════════════════════════════════════════════════════════════════════

class FluxVocabParser:
    """Parses .fluxvocab and .ese files into VocabEntry objects."""

    def parse_file(self, path: str) -> List[VocabEntry]:
        """Parse a .fluxvocab or .ese file into entries."""
        with open(path) as f:
            content = f.read()

        blocks = re.split(r'^---\s*$', content, flags=re.MULTILINE)
        entries = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            entry = self._parse_block(block, path)
            if entry:
                entries.append(entry)
        return entries

    def parse_string(self, content: str, source: str = "<string>") -> List[VocabEntry]:
        """Parse a .fluxvocab content string into entries."""
        blocks = re.split(r'^---\s*$', content, flags=re.MULTILINE)
        entries = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            entry = self._parse_block(block, source)
            if entry:
                entries.append(entry)
        return entries

    def _parse_block(self, block: str, source: str) -> Optional[VocabEntry]:
        """Parse a single entry block."""
        lines = block.split('\n')
        pattern = ""
        expand_lines: List[str] = []
        result_reg = 0
        name = ""
        description = ""
        tags: List[str] = []
        in_expand = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('pattern:'):
                pattern = stripped.split(':', 1)[1].strip().strip('"').strip("'")
                in_expand = False
            elif stripped.startswith('expand:'):
                in_expand = True
                rest = stripped.split(':', 1)[1].strip()
                if rest and rest != '|':
                    expand_lines.append(rest)
            elif stripped.startswith('result:'):
                r = stripped.split(':', 1)[1].strip()
                result_reg = int(r.replace('R', '').strip())
                in_expand = False
            elif stripped.startswith('name:'):
                name = stripped.split(':', 1)[1].strip()
                in_expand = False
            elif stripped.startswith('description:'):
                description = stripped.split(':', 1)[1].strip()
                in_expand = False
            elif stripped.startswith('tags:'):
                tags_str = stripped.split(':', 1)[1].strip()
                tags = [t.strip() for t in tags_str.split(',') if t.strip()]
                in_expand = False
            elif in_expand:
                if stripped.startswith('|'):
                    stripped = stripped[1:].strip()
                if stripped:
                    expand_lines.append(stripped)

        if not pattern or not expand_lines:
            return None

        entry = VocabEntry(
            pattern=pattern,
            expand='\n'.join(expand_lines),
            result_reg=result_reg,
            name=name or pattern[:40],
            description=description,
            tags=tags,
            source_file=source,
        )
        entry.compile_pattern()
        return entry
