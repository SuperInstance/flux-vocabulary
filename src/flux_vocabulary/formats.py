"""
FLUX Instruction Format Specifications.

Defines the 7 encoding formats (A through G) used in the FLUX architecture.
Each format specifies the byte layout of instructions.

Format A: 1 byte  — [op]                    HALT, NOP
Format B: 2 bytes — [op][rd]                INC, DEC, PUSH, POP
Format C: 2 bytes — [op][imm8]              SYS, TRAP, DBG
Format D: 3 bytes — [op][rd][imm8]          MOVI rd, 8-bit literal
Format E: 4 bytes — [op][rd][rs1][rs2]      3-register arithmetic
Format F: 4 bytes — [op][rd][imm16hi][imm16lo]  MOVI rd, 16-bit literal
Format G: 5 bytes — [op][rd][rs1][imm16hi][imm16lo]  Load/store with offset
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class FormatSpec:
    """Specification of a single instruction encoding format."""
    letter: str
    byte_size: int
    description: str
    layout: str
    opcode_range: str
    example_mnemonic: str

    def to_dict(self) -> dict:
        return {
            "letter": self.letter,
            "byte_size": self.byte_size,
            "description": self.description,
            "layout": self.layout,
            "opcode_range": self.opcode_range,
            "example_mnemonic": self.example_mnemonic,
        }


def build_formats() -> List[FormatSpec]:
    """Build the list of all instruction encoding formats."""
    return [
        FormatSpec(
            letter="A",
            byte_size=1,
            description="No-operand instructions (system control, debug)",
            layout="[op]",
            opcode_range="0x00-0x07, 0xF0-0xFF",
            example_mnemonic="HALT",
        ),
        FormatSpec(
            letter="B",
            byte_size=2,
            description="Single register instructions",
            layout="[op][rd]",
            opcode_range="0x08-0x0F",
            example_mnemonic="INC",
        ),
        FormatSpec(
            letter="C",
            byte_size=2,
            description="Immediate-only instructions",
            layout="[op][imm8]",
            opcode_range="0x10-0x17",
            example_mnemonic="SYS",
        ),
        FormatSpec(
            letter="D",
            byte_size=3,
            description="Register + 8-bit immediate",
            layout="[op][rd][imm8]",
            opcode_range="0x18-0x1F",
            example_mnemonic="MOVI",
        ),
        FormatSpec(
            letter="E",
            byte_size=4,
            description="3-register arithmetic / ternary operations",
            layout="[op][rd][rs1][rs2]",
            opcode_range="0x20-0x3F, 0x50-0x5F, 0x60-0x6F, 0x70-0x7F, 0x80-0x8F, 0x90-0x9F, 0xB0-0xBF, 0xC0-0xCF",
            example_mnemonic="ADD",
        ),
        FormatSpec(
            letter="F",
            byte_size=4,
            description="Register + 16-bit immediate (little-endian)",
            layout="[op][rd][imm16hi][imm16lo]",
            opcode_range="0x40-0x47, 0xE0-0xEF",
            example_mnemonic="MOVI16",
        ),
        FormatSpec(
            letter="G",
            byte_size=5,
            description="Register + register + 16-bit offset (little-endian)",
            layout="[op][rd][rs1][imm16hi][imm16lo]",
            opcode_range="0x48-0x4F, 0xD0-0xDF",
            example_mnemonic="LOADOFF",
        ),
    ]


def get_format(letter: str) -> Optional[FormatSpec]:
    """Look up a format spec by letter."""
    for f in build_formats():
        if f.letter == letter.upper():
            return f
    return None


def get_all_formats_dict() -> dict:
    """Return all format specs as a dictionary keyed by letter."""
    return {f.letter: f.to_dict() for f in build_formats()}
