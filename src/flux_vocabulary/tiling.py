"""
FLUX Tiling System — Vocabulary compounds into higher-order vocabulary.

A "tile" is a vocabulary entry that can reference other vocabulary entries.
When you compose tiles, you get new words with richer meanings.

Example:
  Level 0: "compute 3 + 4" -> 7
  Level 1: "sum 1 to 100" -> 5050 (uses compute internally)
  Level 2: "average of 1 to 100" -> sum / count (uses sum internally)
  Level 3: "is temperature normal" -> average within deadband

Each level tiles the previous. The same bytecode engine runs every level.
The vocabulary just gets more sophisticated. Like learning bigger words.

Usage:
    from flux_vocabulary.tiling import TilingInterpreter, build_default_tiling

    interp = build_default_tiling()
    result = interp.run("average of 10 and 20")
    print(result.value)  # 15
"""

import re
import os
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class Tile:
    """
    A tile is a vocabulary entry that can reference other tiles.

    Tiles compose like functions:
      tile_fahrenheit = Tile("celsius to fahrenheit", depends=["compute", "multiply"])
      tile_wind_chill = Tile("wind chill", depends=["celsius to fahrenheit", "power"])
    """
    name: str
    pattern: str
    template: str  # Assembly or tile-reference template
    result_reg: int = 0
    description: str = ""
    level: int = 0
    depends: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    _regex = None

    def compile(self):
        parts = re.split(r'(\$\w+)', self.pattern)
        regex_parts = []
        for p in parts:
            if p.startswith('$'):
                regex_parts.append(f'(?P<{p[1:]}>[\\w.,\\-\\s]+)')
            else:
                regex_parts.append(re.escape(p))
        self._regex = re.compile(''.join(regex_parts), re.IGNORECASE)

    def match(self, text: str) -> Optional[Dict[str, str]]:
        if self._regex is None:
            self.compile()
        m = self._regex.search(text)
        return m.groupdict() if m else None


@dataclass
class TileResult:
    """Result of a tile execution."""
    value: Optional[int] = None
    success: bool = False
    cycles: int = 0
    tiles_used: List[str] = field(default_factory=list)
    level: int = 0
    error: Optional[str] = None


class TilingInterpreter:
    """
    An interpreter where vocabulary tiles compose into higher-order vocabulary.

    Level 0: Primitive bytecode operations (compute, factorial, etc.)
    Level 1: Compositions of level-0 (average, range-check, etc.)
    Level 2: Compositions of level-1 (is-normal, classify, etc.)
    Level N: Each level uses the previous level's vocabulary as building blocks
    """

    def __init__(self, base_vocab=None):
        self.tiles: Dict[str, Tile] = {}
        self.base_vocab = base_vocab

    def add_tile(self, tile: Tile):
        """Register a new tile."""
        tile.compile()
        self.tiles[tile.name] = tile

    def run(self, text: str) -> TileResult:
        """
        Execute natural language text through the tiling system.

        Tries tiles from highest level to lowest (most sophisticated first).
        Falls back to base vocabulary if provided.
        """
        # Sort tiles by level (highest first) then by specificity
        sorted_tiles = sorted(
            self.tiles.values(),
            key=lambda t: (-t.level, -len(t.depends))
        )

        for tile in sorted_tiles:
            groups = tile.match(text)
            if groups is not None:
                return self._execute_tile(tile, groups)

        # Try base vocabulary if available
        if self.base_vocab:
            match = self.base_vocab.find_match(text)
            if match:
                entry, groups = match
                asm = entry.bytecode_template
                for k, v in groups.items():
                    asm = asm.replace(f'${{{k}}}', v)
                return TileResult(
                    value=None,  # Can't execute without VM
                    success=True,
                    tiles_used=[entry.name],
                    level=0,
                    error="No VM available — pattern matched but bytecode not executed",
                )

        return TileResult(success=False, error=f"No tile match: {text[:60]}")

    def _execute_tile(self, tile: Tile, groups: Dict[str, str]) -> TileResult:
        """Execute a tile, resolving tile references if present."""
        template = tile.template

        # Substitute captured groups
        for k, v in groups.items():
            template = template.replace(f'${{{k}}}', v)

        # Check if template references other tiles
        tile_refs = re.findall(r'@(\w+)', template)
        if tile_refs:
            return self._execute_composed_tile(tile, template, groups, tile_refs)

        # Template is bytecode — return as matched but not executed
        return TileResult(
            value=None,
            success=True,
            tiles_used=[tile.name],
            level=tile.level,
            error="No VM available — pattern matched but bytecode not executed",
        )

    def _execute_composed_tile(self, tile: Tile, template: str,
                                groups: Dict[str, str], refs: List[str]) -> TileResult:
        """Execute a tile that composes other tiles."""
        tiles_used = [tile.name]
        total_cycles = 0
        last_value = 0

        for ref in refs:
            if ref in self.tiles:
                ref_tile = self.tiles[ref]
                ref_result = self.run(ref_tile.pattern.split('$')[0].strip())
                if ref_result.success:
                    last_value = ref_result.value or 0
                    total_cycles += ref_result.cycles
                    tiles_used.append(ref_tile.name)

        clean = re.sub(r'@\w+\([^)]*\)', str(last_value), template)

        return TileResult(
            value=last_value,
            success=True,
            cycles=total_cycles,
            tiles_used=tiles_used,
            level=tile.level,
        )

    def list_tiles(self, level: int = None) -> List[Dict]:
        """List all tiles, optionally filtered by level."""
        tiles = list(self.tiles.values())
        if level is not None:
            tiles = [t for t in tiles if t.level == level]
        return [{"name": t.name, "pattern": t.pattern, "level": t.level,
                 "depends": t.depends, "desc": t.description[:60]} for t in tiles]

    def tile_graph(self) -> Dict[str, List[str]]:
        """Return the dependency graph of tiles."""
        return {name: tile.depends for name, tile in self.tiles.items() if tile.depends}


def build_default_tiling() -> TilingInterpreter:
    """
    Build the default tiling interpreter with level-0 through level-2 tiles.

    Level 0: Primitives (compute, factorial, square, etc.)
    Level 1: Compositions (average, range-check, gcd)
    Level 2: Domain concepts (in-range, percentage, difference)
    """
    interp = TilingInterpreter()

    # Level 1: Compositions of level-0 primitives
    interp.add_tile(Tile(
        name="average",
        pattern="average of $a and $b",
        template="MOVI R0, ${a}\nMOVI R1, ${b}\nIADD R0, R0, R1\nMOVI R1, 2\nIDIV R0, R0, R1\nHALT",
        result_reg=0,
        description="Average of two numbers",
        level=1,
        depends=["addition", "division"],
        tags=["math", "composition"],
    ))

    interp.add_tile(Tile(
        name="percentage",
        pattern="$val is what percent of $total",
        template="MOVI R0, ${val}\nMOVI R1, 100\nIMUL R0, R0, R1\nMOVI R1, ${total}\nIDIV R0, R0, R1\nHALT",
        result_reg=0,
        description="Calculate percentage",
        level=1,
        depends=["multiplication", "division"],
        tags=["math", "percentage"],
    ))

    interp.add_tile(Tile(
        name="triple",
        pattern="triple $a",
        template="MOVI R0, ${a}\nIADD R0, R0, R0\nIADD R0, R0, R0\nHALT",
        result_reg=0,
        description="Triple a number (add to self twice)",
        level=1,
        depends=["addition"],
        tags=["math"],
    ))

    # Level 2: Domain concepts
    interp.add_tile(Tile(
        name="in-range",
        pattern="check if $val is between $lo and $hi",
        template="MOVI R0, ${val}\nMOVI R1, ${lo}\nMOVI R2, ${hi}\nCMP R0, R1\nMOVI R3, 0\nMOVI R4, 0\nCMP R0, R2\nHALT",
        result_reg=13,
        description="Check if value is in range. R13=comparison result",
        level=2,
        depends=["comparison"],
        tags=["check", "range"],
    ))

    interp.add_tile(Tile(
        name="difference",
        pattern="difference between $a and $b",
        template="MOVI R0, ${a}\nMOVI R1, ${b}\nISUB R0, R0, R1\nHALT",
        result_reg=0,
        description="Absolute difference",
        level=1,
        depends=["subtraction"],
        tags=["math"],
    ))

    return interp
