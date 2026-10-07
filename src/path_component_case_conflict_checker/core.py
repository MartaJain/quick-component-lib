"""Core logic for case-insensitive path component collision detection.

The checker compares individual path components (the segments between
separators) rather than whole paths. Two components collide when they differ
only in letter case but compare equal under a case-insensitive comparison.
This is what breaks when moving files between case-insensitive filesystems
(macOS HFS+/APFS default, Windows NTFS) and case-sensitive ones (Linux ext4,
XFS), because two names that coexist happily on the source can overwrite one
another on the destination.

Design decisions (stated plainly so the behaviour is predictable):

1. Separator. Both forward slash and backslash are treated as component
   separators. A path like "a\\b/c" splits into ["a", "b", "c"]. We do not try
   to honour Windows drive letters or UNC prefixes specially: "C:\\foo" splits
   into ["C:", "foo"]. The drive-letter component is just another component,
   so "C:" and "c:" would collide, which matches the real risk on a
   case-insensitive volume. If you need drive-letter handling, normalise before
   calling.

2. Collapsing separators. Runs of separators collapse: "a//b" splits into
   ["a", "b"], matching how every mainstream OS resolves multiple separators.

3. Trailing separators. A trailing separator is dropped after splitting,
   so "foo/" and "foo" produce the same component list. A path that is only
   separators (e.g. "/" or "\\\\") splits to an empty list and has no
   collisions.

4. Empty components elsewhere. Because separators collapse, there are no
   empty-string components in the output. This avoids a degenerate collision
   where every path would collide with itself at the empty-string key.

5. Case folding. We use str.casefold() for the comparison key. casefold() is
   the right call for case-insensitive matching of arbitrary Unicode, and it
   is good enough for the ASCII-heavy paths that dominate this problem. We do
   not attempt full Unicode normalisation; doing both casefold and NFKC would
   be more thorough but also more surprising, and the brief asks for one clear
   decision. casefold alone is the decision.

6. Position is informational. A Conflict records the list of positions at
   which a case-variant of the key appeared, in ascending order. We do not
   promise that a later component "wins" or that the first one is canonical;
   the caller decides what to do.

7. Scope. We compare within a single path only. We do not compare one path
   against another; the caller can concatenate paths if they need that, but
   keeping the function single-purpose makes the edge cases tractable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Conflict:
    """A case-insensitive collision between path components.

    Attributes:
        key: The casefolded form shared by every colliding component. Two
            components collide when they share a key but differ in their
            original (pre-casefold) spelling.
        variants: Distinct original spellings that share ``key``, sorted to
            make output deterministic. Sorting is lexical by Unicode code
            point; it is a presentation choice, not a claim about which
            variant is canonical.
        positions: Zero-based indices into the split component list where any
            variant of ``key`` appeared, ascending.
    """

    key: str
    variants: List[str] = field(default_factory=list)
    positions: List[int] = field(default_factory=list)


def _split_components(path: str) -> List[str]:
    """Split a path into non-empty components.

    Both / and \\ are separators, runs collapse, and leading/trailing
    separators are dropped. A path of only separators yields an empty list.
    """
    if not path:
        return []
    components: List[str] = []
    current: List[str] = []
    for ch in path:
        if ch == "/" or ch == "\\":
            if current:
                components.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        components.append("".join(current))
    return components


def check_components(components: List[str]) -> List[Conflict]:
    """Find case-insensitive collisions among a list of path components.

    Args:
        components: Pre-split path components. Empty strings are ignored to
            stay consistent with :func:`_split_components`; a caller passing
            their own split should not get spurious empty-key collisions.

    Returns:
        Conflicts sorted by first appearance position, so output is stable
        across runs. A component with no case-variant twin produces no
        conflict.
    """
    # Map from casefolded key to list of (position, original). We keep the
    # original spelling so variants can be reported verbatim, and the position
    # so the caller can locate the collision in the input.
    groups: dict[str, list[tuple[int, str]]] = {}
    order: list[str] = []  # keys in first-seen order, for stable output
    for i, comp in enumerate(components):
        if comp == "":
            # An empty component would collide only with other empty
            # components, which is noise rather than a real filesystem risk.
            continue
        key = comp.casefold()
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((i, comp))

    conflicts: List[Conflict] = []
    for key in order:
        entries = groups[key]
        # Deduplicate identical spellings at the same position is not needed
        # because each position appears once; but the same spelling can recur
        # at different positions. Distinct spellings are what matter.
        distinct_variants = sorted({orig for _, orig in entries})
        if len(distinct_variants) < 2:
            continue
        positions = sorted(i for i, _ in entries)
        conflicts.append(
            Conflict(
                key=key,
                variants=distinct_variants,
                positions=positions,
            )
        )
    return conflicts


def check_path(path: str) -> List[Conflict]:
    """Find case-insensitive collisions among the components of ``path``.

    Convenience wrapper around :func:`check_components` that splits the path
    first. See the module docstring for the splitting rules.
    """
    return check_components(_split_components(path))
