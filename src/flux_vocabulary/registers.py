"""
FLUX Register File Definitions.

Defines the register banks, special aliases, and ABI conventions for the
FLUX architecture. Extracted from flux-runtime/src/flux/vm/registers.py.

Layout:
    R0  - R15 : 16 general-purpose integer registers
    F0  - F15 : 16 floating-point registers
    V0  - V15 : 16 SIMD/vector registers (128-bit bytearrays)

Special ABI aliases:
    R11 (SP)    : Stack pointer
    R12         : Region ID (implicit ABI)
    R13         : Trust token (implicit ABI)
    R14 (FP)    : Frame pointer
    R15 (LR)    : Link register (return address)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RegisterDef:
    """Definition of a single register."""
    index: int
    name: str
    bank: str           # "gp", "fp", "vec"
    abi_name: str = ""  # e.g. "SP", "FP", "LR", "" for no alias
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "name": self.name,
            "bank": self.bank,
            "abi_name": self.abi_name,
            "description": self.description,
        }


@dataclass
class RegisterBank:
    """A bank of registers (e.g., GP, FP, VEC)."""
    name: str
    prefix: str          # "R", "F", "V"
    count: int
    description: str
    registers: List[RegisterDef] = field(default_factory=list)

    def __post_init__(self):
        if not self.registers:
            self.registers = [
                RegisterDef(i, f"{self.prefix}{i}", self.name.lower())
                for i in range(self.count)
            ]

    def get(self, index: int) -> Optional[RegisterDef]:
        if 0 <= index < self.count:
            return self.registers[index]
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "prefix": self.prefix,
            "count": self.count,
            "description": self.description,
            "registers": [r.to_dict() for r in self.registers],
        }


# ══════════════════════════════════════════════════════════════════════════════
# Pre-defined register banks
# ══════════════════════════════════════════════════════════════════════════════

GP_COUNT = 16
FP_COUNT = 16
VEC_COUNT = 16

# Special register ABI aliases
SP_INDEX = 11      # Stack pointer
FP_INDEX = 14      # Frame pointer
LR_INDEX = 15      # Link register
REGION_INDEX = 12  # Region ID
TRUST_INDEX = 13   # Trust token


def build_gp_bank() -> RegisterBank:
    """Build the general-purpose register bank R0-R15."""
    regs = []
    abi_map = {
        11: ("SP", "Stack pointer"),
        12: ("R12", "Region ID (implicit ABI)"),
        13: ("R13", "Trust token (implicit ABI)"),
        14: ("FP", "Frame pointer"),
        15: ("LR", "Link register (return address)"),
    }
    for i in range(GP_COUNT):
        abi_name = ""
        desc = f"General-purpose register {i}"
        if i in abi_map:
            abi_name, desc = abi_map[i]
        regs.append(RegisterDef(i, f"R{i}", "gp", abi_name, desc))

    return RegisterBank(
        name="General Purpose",
        prefix="R",
        count=GP_COUNT,
        description="16 general-purpose integer registers (R0-R15)",
        registers=regs,
    )


def build_fp_bank() -> RegisterBank:
    """Build the floating-point register bank F0-F15."""
    return RegisterBank(
        name="Floating Point",
        prefix="F",
        count=FP_COUNT,
        description="16 floating-point registers (F0-F15)",
    )


def build_vec_bank() -> RegisterBank:
    """Build the SIMD/vector register bank V0-V15."""
    return RegisterBank(
        name="Vector",
        prefix="V",
        count=VEC_COUNT,
        description="16 SIMD/vector registers (V0-V15, 128-bit bytearrays)",
    )


def get_all_banks() -> List[RegisterBank]:
    """Return all register banks."""
    return [build_gp_bank(), build_fp_bank(), build_vec_bank()]


def get_register_file_dict() -> dict:
    """Return the full register file as a dictionary."""
    return {
        "total_registers": GP_COUNT + FP_COUNT + VEC_COUNT,
        "gp_count": GP_COUNT,
        "fp_count": FP_COUNT,
        "vec_count": VEC_COUNT,
        "special_aliases": {
            "SP": SP_INDEX,
            "FP": FP_INDEX,
            "LR": LR_INDEX,
            "R12": REGION_INDEX,
            "R13": TRUST_INDEX,
        },
        "banks": [b.to_dict() for b in get_all_banks()],
    }
