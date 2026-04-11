"""
L0 Constitutional Primitives and the PRGF concept.

PRGF (Programmatically Relevant Grammatical Features) are the foundational
concepts that underpin the FLUX vocabulary system. The most important are
the L0 primitives — seven irreducible concepts every FLUX agent must know:

  SELF, OTHER, POSSIBLE, TRUE, CAUSE, VALUE, AGREEMENT

The L0Scrubber is a hostile audit agent that challenges any proposed new
primitives against these seven, preventing vocabulary bloat and maintaining
the integrity of the L0 layer.

Usage:
    from flux_vocabulary.concepts import scrub_primitive

    report = scrub_primitive("TRUST", "Belief that another will act in agreement")
    print(report.recommendation)  # 'accept', 'reject', or 'needs-refinement'
"""

import re
from typing import List, Optional, Set, Tuple
from dataclasses import dataclass, field


# The 7 constitutional L0 primitives
L0_PRIMITIVES = ['self', 'other', 'possible', 'true', 'cause', 'value', 'agreement']

# Definitions from the l0_primitives.ese file
L0_DEFINITIONS = {
    "SELF": "the unique referent designating this executing process as a locus of perspective, action, and valuation",
    "OTHER": "a recognized autonomous process possessing its own SELF, perspective, and potential intent",
    "POSSIBLE": "a modal assessment that a specific state or event is not ruled out by known constraints",
    "TRUE": "a commitment that a proposition corresponds to the shared environment, verifiable against consensus",
    "CAUSE": "a directed relational belief that one event increases the probability of another",
    "VALUE": "a valenced assessment of desirability (positive=benefit, negative=cost)",
    "AGREEMENT": "a mutually recognized alignment between agents regarding a proposition or pattern",
}

# Semantic patterns for detecting overlap with L0 primitives
SEMANTIC_PATTERNS = {
    'self': [
        r'\b(I|me|my|myself|agent|this\s+system)\b',
        r'\b(internal|subjective|first-person)\b',
        r'\b(own|personal|individual)\s+(perspective|view|stance)\b'
    ],
    'other': [
        r'\b(you|they|them|external|outside)\b',
        r'\b(second-person|third-person)\b',
        r'\b(separate|distinct\s+entity)\b'
    ],
    'possible': [
        r'\b(might|could|may|potential|alternativ)\w*\b',
        r'\b(modal|hypothetical|counterfactual)\b',
        r'\b(could\s+be|might\s+have|would\s+be)\b'
    ],
    'true': [
        r'\b(fact|verif|correspond|real|actual)\b',
        r'\b(accurate|correct|valid)\b',
        r'\b(truth|false|error|check|verify)\b'
    ],
    'cause': [
        r'\b(because|due\s+to|leads\s+to|result)\b',
        r'\b(causal|mechanism|effect|consequence)\b',
        r'\b(produces|generates|creates|triggers)\b'
    ],
    'value': [
        r'\b(good|bad|better|worse|prefer)\b',
        r'\b(should|ought|moral|ethical)\b',
        r'\b(util|worth|valuable|desirable)\b'
    ],
    'agreement': [
        r'\b(agree|contract|promise|commit)\b',
        r'\b(coordination|alignment|mutual)\b',
        r'\b(joint|shared|collective)\s+(decision|action)\b'
    ]
}


@dataclass
class ScrubReport:
    """Report from L0 constitutional scrubbing challenge."""
    candidate: str                          # Name of the candidate primitive
    definition: str                          # Definition/description of the candidate
    passed: bool                            # Whether the candidate passed all challenges
    can_tile: bool                          # True if it's just a composition of existing primitives
    conflicts: List[str]                    # List of conflicts with existing primitives
    challenges: List[str]                   # Edge-case semantic challenges generated
    recommendation: str                     # 'accept', 'reject', 'needs-refinement'
    reasoning: str = ""                     # Detailed reasoning for the recommendation
    semantic_overlap_score: float = 0.0     # 0-1 score of semantic overlap with existing primitives

    def __repr__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"ScrubReport({status} {self.candidate}: {self.recommendation})"


class L0Scrubber:
    """
    Hostile audit agent that challenges proposed L0 primitives.

    The 7 foundational L0 primitives are:
    - SELF: The agent's own perspective/existence
    - OTHER: Entities outside the agent
    - POSSIBLE: Potential states/alternatives
    - TRUE: Factual verification/correspondence
    - CAUSE: Causal relationships/mechanisms
    - VALUE: Valuation/goodness/preference
    - AGREEMENT: Coordination/alignment between agents

    Any candidate primitive must survive challenges against these.
    """

    def __init__(self):
        """Initialize the L0 scrubber with compiled semantic patterns."""
        self._compiled_patterns = {}
        for prim, patterns in SEMANTIC_PATTERNS.items():
            self._compiled_patterns[prim] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def challenge(self, candidate_name: str, candidate_definition: str) -> ScrubReport:
        """
        Challenge a candidate primitive against the L0 constitution.

        Args:
            candidate_name: Name of the proposed primitive
            candidate_definition: Definition/description of the primitive

        Returns:
            ScrubReport with detailed analysis
        """
        candidate_lower = candidate_name.lower().strip()
        definition_lower = candidate_definition.lower()

        report = ScrubReport(
            candidate=candidate_name,
            definition=candidate_definition,
            passed=False,
            can_tile=False,
            conflicts=[],
            challenges=[],
            recommendation='reject',
            semantic_overlap_score=0.0
        )

        # Check 1: Direct name conflict
        if candidate_lower in [p.lower() for p in L0_PRIMITIVES]:
            report.conflicts.append(
                f"Direct name conflict: '{candidate_name}' is already an L0 primitive"
            )
            report.recommendation = 'reject'
            report.reasoning = "Cannot redefine existing L0 primitives."
            return report

        # Check 2: Semantic overlap
        overlap_analysis = self._check_semantic_overlap(candidate_lower, definition_lower)
        report.semantic_overlap_score = overlap_analysis['score']
        report.conflicts.extend(overlap_analysis['conflicts'])

        # Check 3: Can tile into existing primitives
        can_tile = self._can_tile_into_existing(candidate_lower, definition_lower)
        report.can_tile = can_tile

        # Check 4: Generate edge-case challenges
        challenges = self._generate_challenges(candidate_lower, definition_lower)
        report.challenges = challenges

        # Check 5: Additional conflicts
        additional_conflicts = self._check_conflicts(candidate_name, candidate_definition)
        report.conflicts.extend(additional_conflicts)

        # Make recommendation
        report = self._make_recommendation(report)

        return report

    def _check_semantic_overlap(self, name: str, definition: str) -> dict:
        """Check semantic overlap with existing L0 primitives."""
        overlapping_prims = []
        total_matches = 0
        max_possible_matches = len(L0_PRIMITIVES) * 3

        combined_text = f"{name} {definition}"

        for prim in L0_PRIMITIVES:
            matches = 0
            patterns = self._compiled_patterns.get(prim, [])
            for pattern in patterns:
                if pattern.search(combined_text):
                    matches += 1
                    total_matches += 1
            if matches > 0:
                overlapping_prims.append((prim, matches))

        score = min(total_matches / max_possible_matches, 1.0)

        conflicts = []
        if overlapping_prims:
            for prim, count in overlapping_prims:
                conflicts.append(
                    f"Semantic overlap with L0 primitive '{prim.upper()}' "
                    f"({count} pattern matches)"
                )

        return {'score': score, 'conflicts': conflicts}

    def _can_tile_into_existing(self, name: str, definition: str) -> bool:
        """Check if a candidate can be expressed as a composition of existing primitives."""
        combined = f"{name} {definition}".lower()

        tiling_indicators = [
            r'\b(combination|composition|compound)\s+of\b',
            r'\b(both|and|plus)\s+.*\s+(and|plus)\s+',
            r'\b(mixture|blend|fusion)\b',
            r'\b(corresponds?\s+to)\s+.*\s+(combined|joined|merged)\b'
        ]

        for pattern in tiling_indicators:
            if re.search(pattern, combined):
                return True

        used_prims = []
        for prim in L0_PRIMITIVES:
            if self._compiled_patterns.get(prim):
                for pat in self._compiled_patterns[prim]:
                    if pat.search(combined):
                        used_prims.append(prim)
                        break

        if len(used_prims) >= 3:
            compositional_words = ['and', 'plus', 'combined', 'together', 'with']
            if any(word in combined for word in compositional_words):
                return True

        return False

    def _check_conflicts(self, name: str, definition: str) -> List[str]:
        """Check if the candidate conflicts with existing L0 primitives."""
        conflicts = []
        definition_lower = definition.lower()

        for prim in L0_PRIMITIVES:
            negation_patterns = [
                f'not {prim}',
                f'no {prim}',
                f'without {prim}',
                f'lack of {prim}',
                f'absence of {prim}'
            ]
            for pattern in negation_patterns:
                if pattern in definition_lower:
                    conflicts.append(
                        f"Negation conflict: Candidate appears to negate "
                        f"L0 primitive '{prim.upper()}'"
                    )
                    break

        return conflicts

    def _generate_challenges(self, name: str, definition: str) -> List[str]:
        """Generate edge-case semantic challenges for the candidate."""
        challenges = []
        challenges.append(
            f"Boundary: What is the negation of '{name}'? "
            f"How do you distinguish '{name}' from 'not-{name}'?"
        )
        challenges.append(
            f"L0 Mapping: Which of the 7 L0 primitives can express '{name}'? "
            f"If none, why is it foundational?"
        )
        challenges.append(
            f"Edge Case: What happens when '{name}' is applied to itself? "
            f"Is '{name}' reflexive, transitive, symmetric?"
        )
        challenges.append(
            f"Verification: How would an agent verify '{name}'? "
            f"What observation distinguishes '{name}' from non-'{name}'?"
        )
        challenges.append(
            f"Coordination: If two agents disagree on '{name}', "
            f"how would they resolve the disagreement using existing L0 primitives?"
        )
        if self._can_tile_into_existing(name, definition):
            challenges.append(
                f"Tiling: '{name}' appears to be expressible as a composition "
                f"of existing primitives. What does it add that cannot be tiled?"
            )
        challenges.append(
            f"Circularity: Is '{name}' defined in terms of itself? "
            f"Can '{name}' be understood without reference to '{name}'?"
        )
        return challenges

    def _make_recommendation(self, report: ScrubReport) -> ScrubReport:
        """Make a recommendation based on the analysis."""
        score = report.semantic_overlap_score
        num_conflicts = len(report.conflicts)
        can_tile = report.can_tile

        if score > 0.5 and can_tile:
            report.passed = False
            report.recommendation = 'reject'
            report.reasoning = (
                f"High semantic overlap ({score:.2f}) with existing L0 primitives "
                f"and can be tiled from existing primitives. This is redundant."
            )
        elif num_conflicts >= 3:
            report.passed = False
            report.recommendation = 'reject'
            report.reasoning = (
                f"Too many conflicts ({num_conflicts}) with existing L0 constitution. "
                f"Fundamental incompatibility."
            )
        elif can_tile:
            report.passed = False
            report.recommendation = 'needs-refinement'
            report.reasoning = (
                f"Can be expressed as tiling of existing primitives. "
                f"Must show why it cannot be decomposed."
            )
        elif score > 0.3:
            report.passed = False
            report.recommendation = 'needs-refinement'
            report.reasoning = (
                f"Moderate semantic overlap ({score:.2f}). "
                f"Must clarify distinction from existing primitives."
            )
        elif num_conflicts > 0:
            report.passed = False
            report.recommendation = 'needs-refinement'
            report.reasoning = (
                f"Has {num_conflicts} conflict(s) with existing L0 primitives. "
                f"Must resolve conflicts."
            )
        else:
            report.passed = True
            report.recommendation = 'accept'
            report.reasoning = (
                f"Low semantic overlap ({score:.2f}), no conflicts, "
                f"survived all challenges. Ready for L0 consideration."
            )

        return report

    def batch_challenge(self, candidates: List[Tuple[str, str]]) -> List[ScrubReport]:
        """Challenge multiple candidate primitives in batch."""
        return [self.challenge(name, defn) for name, defn in candidates]


def scrub_primitive(name: str, definition: str) -> ScrubReport:
    """Convenience function to scrub a single primitive."""
    scrubber = L0Scrubber()
    return scrubber.challenge(name, definition)
