# Path Component Case Conflict Checker

Detects case-insensitive collisions between path components — the segments between separators — that would break when transferring files between case-insensitive filesystems (macOS, Windows) and case-sensitive ones (Linux).

```python
from path_component_case_conflict_checker import check_path, check_components, Conflict

# Returns a list of Conflict objects, one per case-collision group.
conflicts = check_path("project/Source/src")
for c in conflicts:
    print(c.key, c.variants, c.positions)

# Or pass pre-split components directly.
conflicts = check_components(["FOO", "foo", "bar"])
```

A `Conflict` has three fields: `key` (the casefolded form shared by every colliding component), `variants` (distinct original spellings, sorted for deterministic output), and `positions` (zero-based indices into the component list where any variant appeared).

## Why this exists

On a case-insensitive volume you can have `Source` and `source` in the same directory and the OS treats them as distinct files. Copy that directory to ext4 and the second one silently overwrites the first. This library finds those collisions before you transfer.

The trade-off is that it only looks **within a single path**. It does not compare one path against another, and it does not touch the filesystem. You give it a path string or a list of components; it tells you which components would collide with each other under case-insensitive comparison. Keeping the scope narrow is what makes the edge cases tractable.

## Edge cases you will hit

- **Separators**: both `/` and `\` split components. `C:\foo` becomes `["C:", "foo"]`, so `C:` and `c:` collide — which is the correct risk on a case-insensitive volume, but not what you want if you expected drive letters to be special. Normalise before calling if you need that.
- **Runs of separators collapse**, and trailing separators are dropped. `a//b/` and `a/b` produce the same component list.
- **Repeated identical spelling is not a collision.** `foo/foo` has no distinct variants, so it returns no conflict. Only components that differ in case while sharing a casefolded key count.
- **Comparison uses `str.casefold()`**, not `lower()`. This means `STRASSE` and `straße` are flagged as a collision, which is usually what you want for Unicode but may surprise you if you assumed ASCII-only folding.
