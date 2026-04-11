"""
Vocabulary file loaders for .fluxvocab and .ese formats.

Convenience functions for loading vocabulary files without instantiating
a full Vocabulary object. These are useful for inspection, validation,
and tooling.
"""

import os
import re
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from .vocabulary import VocabEntry


def load_fluxvocab(path: str) -> List[VocabEntry]:
    """
    Load a single .fluxvocab file and return parsed VocabEntry objects.

    Args:
        path: Path to a .fluxvocab file.

    Returns:
        List of VocabEntry objects parsed from the file.
    """
    with open(path) as f:
        content = f.read()

    blocks = re.split(r'^---\s*$', content, flags=re.MULTILINE)
    entries = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        entry = _parse_fluxvocab_block(block)
        if entry:
            entries.append(entry)

    return entries


def load_ese(path: str) -> List[Dict[str, Any]]:
    """
    Load a single .ese (FLUX-ese) file and return parsed concept definitions.

    FLUX-ese files use a different format than .fluxvocab:
    - Definitions prefixed with **
    - Patterns prefixed with ## pattern:
    - Assembly prefixed with ## assembly:
    - Commentary prefixed with >>

    Args:
        path: Path to a .ese file.

    Returns:
        List of dicts with keys: definitions, patterns, commentary.
    """
    with open(path) as f:
        content = f.read()

    definitions = {}
    patterns = []
    commentary = []

    for line in content.split('\n'):
        line = line.strip()

        # Definition: ** WORD ** := definition
        def_match = re.match(r'\*\*(\w+)\*\*\s*:=\s*(.+)', line)
        if def_match:
            name = def_match.group(1)
            value = def_match.group(2)
            definitions[name] = value
            continue

        # Pattern: ## pattern: ...
        pat_match = re.match(r'##\s+pattern:\s*(.+)', line)
        if pat_match:
            patterns.append(pat_match.group(1))
            continue

        # Pattern metadata
        meta_match = re.match(r'##\s+(assembly|description|result_reg|tags):\s*(.*)', line)
        if meta_match and patterns:
            # Attach metadata to the last pattern
            key = meta_match.group(1)
            value = meta_match.group(2).strip()
            if not isinstance(patterns[-1], dict):
                # Convert last pattern string to dict
                patterns[-1] = {"pattern": patterns[-1]}
            patterns[-1][key] = value
            continue

        # Commentary: >> ...
        if line.startswith('>>'):
            commentary.append(line[2:].strip())
            continue

    return {
        "source": os.path.basename(path),
        "definitions": definitions,
        "patterns": patterns,
        "commentary": commentary,
    }


def load_folder(path: str) -> List[VocabEntry]:
    """
    Load all .fluxvocab files from a directory tree.

    Args:
        path: Path to a directory containing .fluxvocab and .ese files.

    Returns:
        Combined list of VocabEntry objects from all files found.
    """
    entries = []

    if not os.path.isdir(path):
        return entries

    for root, dirs, files in os.walk(path):
        for fname in sorted(files):
            if fname.endswith('.fluxvocab'):
                fpath = os.path.join(root, fname)
                entries.extend(load_fluxvocab(fpath))

    return entries


def load_folder_recursive(path: str) -> List[VocabEntry]:
    """
    Load all vocabulary files from a directory tree recursively.

    Includes both .fluxvocab and .ese files.

    Args:
        path: Path to a directory.

    Returns:
        Combined list of VocabEntry objects.
    """
    all_entries = []

    if not os.path.isdir(path):
        return all_entries

    for root, dirs, files in os.walk(path):
        for fname in sorted(files):
            fpath = os.path.join(root, fname)
            if fname.endswith('.fluxvocab'):
                all_entries.extend(load_fluxvocab(fpath))
            elif fname.endswith('.ese'):
                # Parse ESE files and create VocabEntry objects from patterns
                ese_data = load_ese(fpath)
                for pat in ese_data["patterns"]:
                    if isinstance(pat, dict):
                        entry = VocabEntry(
                            pattern=pat.get("pattern", ""),
                            bytecode_template=pat.get("assembly", ""),
                            result_reg=int(pat.get("result_reg", "0")),
                            description=pat.get("description", ""),
                            tags=[t.strip() for t in pat.get("tags", "").split(",")],
                        )
                        if entry.pattern:
                            entry.compile()
                            all_entries.append(entry)

    return all_entries


def validate_fluxvocab(content: str) -> List[str]:
    """
    Validate a .fluxvocab file and return a list of issues.

    Args:
        content: The file content as a string.

    Returns:
        List of validation error/warning messages.
    """
    issues = []
    blocks = re.split(r'^---\s*$', content, flags=re.MULTILINE)

    pattern_names = set()

    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue

        # Check for pattern
        has_pattern = False
        has_expand = False
        has_result = False
        name = ""

        for line in block.split('\n'):
            line = line.strip()
            if line.startswith('pattern:'):
                has_pattern = True
            elif line.startswith('expand:'):
                has_expand = True
            elif line.startswith('result:'):
                has_result = True
            elif line.startswith('name:'):
                name = line.split(':', 1)[1].strip()

        if not has_pattern:
            issues.append(f"Block {i}: missing 'pattern:' field")
        if not has_expand:
            issues.append(f"Block {i}: missing 'expand:' field")
        if not has_result:
            issues.append(f"Block {i}: missing 'result:' field (warning)")

        # Check for duplicate names
        if name:
            if name in pattern_names:
                issues.append(f"Block {i}: duplicate name '{name}'")
            pattern_names.add(name)

    return issues


def _parse_fluxvocab_block(block: str) -> Optional[VocabEntry]:
    """Parse a single fluxvocab block into a VocabEntry."""
    lines = block.split('\n')
    pattern = ""
    expand_lines = []
    result_reg = 0
    name = ""
    description = ""
    tags = []
    in_expand = False

    for line in lines:
        line = line.strip()
        if line.startswith('pattern:'):
            pattern = line.split(':', 1)[1].strip().strip('"').strip("'")
            in_expand = False
        elif line.startswith('expand:'):
            in_expand = True
            rest = line.split(':', 1)[1].strip()
            if rest and not rest.startswith('|'):
                expand_lines.append(rest)
        elif line.startswith('result:'):
            r = line.split(':', 1)[1].strip()
            result_reg = int(r.replace('R', '').strip())
            in_expand = False
        elif line.startswith('name:'):
            name = line.split(':', 1)[1].strip()
            in_expand = False
        elif line.startswith('description:'):
            description = line.split(':', 1)[1].strip()
            in_expand = False
        elif line.startswith('tags:'):
            tags_str = line.split(':', 1)[1].strip()
            tags = [t.strip() for t in tags_str.split(',')]
            in_expand = False
        elif in_expand:
            if line.startswith('|'):
                line = line[1:].strip()
            if line:
                expand_lines.append(line)

    if not pattern or not expand_lines:
        return None

    entry = VocabEntry(
        pattern=pattern,
        bytecode_template='\n'.join(expand_lines),
        result_reg=result_reg,
        name=name or pattern[:40],
        description=description,
        tags=tags,
    )
    entry.compile()
    return entry
