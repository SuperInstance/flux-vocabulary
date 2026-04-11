"""
Ghost Vessel Loader — Resurrect tombstoned vocabulary entries.

When vocabulary entries are pruned from an active vocabulary, they are
"tombstoned" — marked as removed but not deleted entirely. The Ghost Vessel
Loader can resurrect these entries as read-only "ghosts" that new agents
can consult for historical context, debugging, or understanding what
previous agents knew.

Usage:
    from flux_vocabulary.ghost import GhostLoader, GhostEntry

    loader = GhostLoader()
    ghosts = loader.load_tombstones("path/to/tombstones.json")

    # Consult ghosts for context
    relevant = loader.consult(ghosts, "compute fibonacci")

    # Resurrect a ghost if needed
    entry = loader.resurrect(ghosts[0])
"""

import json
import os
import time
import hashlib
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class GhostEntry:
    """A tombstoned vocabulary entry that was pruned but preserved as a ghost."""
    name: str
    pattern: str
    bytecode_template: str
    sha256: str
    pruned_reason: str
    pruned_at: float
    original_name: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    usage_count: int = 0
    last_used: float = 0.0

    def __repr__(self) -> str:
        return f"GhostEntry(name='{self.name}', pruned_reason='{self.pruned_reason[:30]}...')"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'GhostEntry':
        """Create from dictionary."""
        return cls(**data)

    def age_days(self) -> float:
        """Get the age of this ghost in days."""
        return (time.time() - self.pruned_at) / (24 * 3600)

    def is_recent(self, days: int = 30) -> bool:
        """Check if this ghost is from the last N days."""
        return self.age_days() <= days


@dataclass
class ResurrectionContext:
    """Context for resurrection operations."""
    timestamp: float = field(default_factory=time.time)
    agent_name: str = ""
    reason: str = ""
    target_vocabulary: str = ""

    def __repr__(self) -> str:
        return f"ResurrectionContext(agent='{self.agent_name}', reason='{self.reason}')"


@dataclass
class ResurrectedEntry:
    """A resurrected vocabulary entry that can be added back to a vocabulary."""
    name: str
    pattern: str
    bytecode_template: str
    result_reg: int = 0
    description: str = ""
    tags: List[str] = field(default_factory=list)
    _ghost_origin: Optional[GhostEntry] = None

    def compile(self):
        """Compile the pattern into a regex."""
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
        """Try to match text against this pattern."""
        if not hasattr(self, '_regex'):
            self.compile()
        m = self._regex.search(text)
        if m:
            return {k: v for k, v in m.groupdict().items() if v is not None}
        return None


class GhostLoader:
    """
    Loads and manages tombstoned vocabulary entries as ghosts.

    Ghosts are read-only historical records of vocabulary that was once
    active but has been pruned. They can be consulted for context or
    selectively resurrected.
    """

    def __init__(self):
        self._ghosts: List[GhostEntry] = []
        self._index: Dict[str, List[GhostEntry]] = {}

    def load_tombstones(self, path: str) -> List[GhostEntry]:
        """Load tombstoned entries from a JSON file."""
        if not os.path.exists(path):
            return []

        with open(path, 'r') as f:
            data = json.load(f)

        ghosts = []
        for entry_data in data.get('tombstones', []):
            ghost = GhostEntry.from_dict(entry_data)
            ghosts.append(ghost)

        self._ghosts = ghosts
        self._rebuild_index()

        return ghosts

    def save_tombstones(self, path: str, ghosts: Optional[List[GhostEntry]] = None):
        """Save tombstoned entries to a JSON file."""
        if ghosts is None:
            ghosts = self._ghosts

        data = {
            'version': '1.0',
            'timestamp': time.time(),
            'count': len(ghosts),
            'tombstones': [g.to_dict() for g in ghosts]
        }

        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def resurrect(self, ghost: GhostEntry, context: Optional[dict] = None) -> Optional[ResurrectedEntry]:
        """Resurrect a ghost as a full vocabulary entry."""
        if not ghost.pattern or not ghost.bytecode_template:
            return None

        entry = ResurrectedEntry(
            name=ghost.original_name or ghost.name,
            pattern=ghost.pattern,
            bytecode_template=ghost.bytecode_template,
            description=ghost.description,
            tags=ghost.tags,
            _ghost_origin=ghost
        )

        return entry

    def consult(self, ghosts: List[GhostEntry], query: str, limit: int = 5) -> List[GhostEntry]:
        """Consult ghosts to find entries matching a query."""
        query_lower = query.lower()
        scored = []

        for ghost in ghosts:
            score = 0.0
            if query_lower in ghost.name.lower():
                score += 10.0
            if query_lower in ghost.pattern.lower():
                score += 5.0
            if query_lower in ghost.description.lower():
                score += 3.0
            for tag in ghost.tags:
                if query_lower in tag.lower():
                    score += 2.0
            if query_lower in ghost.pruned_reason.lower():
                score += 1.0
            if score > 0:
                scored.append((ghost, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [ghost for ghost, score in scored[:limit]]

    def find_by_name(self, name: str) -> List[GhostEntry]:
        """Find all ghosts with a given name."""
        return self._index.get(name, [])

    def find_by_hash(self, sha256: str) -> Optional[GhostEntry]:
        """Find a ghost by its SHA256 hash."""
        for ghost in self._ghosts:
            if ghost.sha256 == sha256:
                return ghost
        return None

    def find_recent(self, days: int = 30) -> List[GhostEntry]:
        """Find ghosts pruned within the last N days."""
        return [g for g in self._ghosts if g.is_recent(days)]

    def get_statistics(self) -> dict:
        """Get statistics about loaded ghosts."""
        if not self._ghosts:
            return {
                'total_ghosts': 0,
                'unique_names': 0,
                'avg_age_days': 0,
                'most_recent': None,
                'oldest': None
            }

        now = time.time()
        ages = [(now - g.pruned_at) / (24 * 3600) for g in self._ghosts]
        unique_names = set(g.name for g in self._ghosts)
        most_recent = min(self._ghosts, key=lambda g: g.pruned_at)
        oldest = max(self._ghosts, key=lambda g: g.pruned_at)

        reason_counts = {}
        for ghost in self._ghosts:
            reason = ghost.pruned_reason
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        return {
            'total_ghosts': len(self._ghosts),
            'unique_names': len(unique_names),
            'avg_age_days': sum(ages) / len(ages) if ages else 0,
            'most_recent': most_recent.pruned_at,
            'oldest': oldest.pruned_at,
            'pruned_reasons': reason_counts
        }

    def merge(self, other_ghosts: List[GhostEntry]):
        """Merge another list of ghosts into this loader."""
        existing_hashes = set(g.sha256 for g in self._ghosts)
        for ghost in other_ghosts:
            if ghost.sha256 not in existing_hashes:
                self._ghosts.append(ghost)
                existing_hashes.add(ghost.sha256)
        self._rebuild_index()

    def clear_recent(self, days: int = 90):
        """Clear ghosts older than N days."""
        self._ghosts = [g for g in self._ghosts if g.age_days() <= days]
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild the name index for faster lookups."""
        self._index = {}
        for ghost in self._ghosts:
            name = ghost.name
            if name not in self._index:
                self._index[name] = []
            self._index[name].append(ghost)


def create_tombstone(vocab_entry, reason: str, usage_count: int = 0,
                     last_used: float = 0.0) -> GhostEntry:
    """Convenience function to create a tombstone from a vocabulary entry."""
    content = f"{vocab_entry.pattern}|{vocab_entry.bytecode_template}"
    sha256 = hashlib.sha256(content.encode()).hexdigest()

    return GhostEntry(
        name=vocab_entry.name,
        pattern=vocab_entry.pattern,
        bytecode_template=vocab_entry.bytecode_template,
        sha256=sha256,
        pruned_reason=reason,
        pruned_at=time.time(),
        original_name=vocab_entry.name,
        description=getattr(vocab_entry, 'description', ''),
        tags=getattr(vocab_entry, 'tags', []),
        usage_count=usage_count,
        last_used=last_used
    )
