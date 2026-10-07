import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from path_component_case_conflict_checker import (  # noqa: E402
    Conflict,
    check_components,
    check_path,
)


class TestSplitting(unittest.TestCase):
    def test_no_collision_returns_empty(self):
        self.assertEqual(check_path("foo/bar/baz"), [])

    def test_empty_path_returns_empty(self):
        self.assertEqual(check_path(""), [])

    def test_single_component_no_collision(self):
        self.assertEqual(check_path("foo"), [])

    def test_only_separators_returns_empty(self):
        self.assertEqual(check_path("///"), [])
        self.assertEqual(check_path("\\\\\\"), [])

    def test_leading_and_trailing_separators_ignored(self):
        # "foo/" and "foo" are the same component set.
        self.assertEqual(check_path("/foo/Bar/"), check_path("foo/Bar"))

    def test_collapsed_separators(self):
        # "a//b" splits to ["a", "b"]; no empty-component collision.
        self.assertEqual(check_path("a//b"), [])

    def test_backslash_is_separator(self):
        # A mixed-separator path splits into three components; only the
        # case-collision matters.
        result = check_path("a\\\\B/c")
        self.assertEqual(result, [])


class TestCollisions(unittest.TestCase):
    def test_simple_case_collision(self):
        result = check_path("foo/Foo")
        self.assertEqual(len(result), 1)
        c = result[0]
        self.assertEqual(c.key, "foo")
        self.assertEqual(c.variants, ["Foo", "foo"])
        self.assertEqual(c.positions, [0, 1])

    def test_three_variants(self):
        result = check_path("FOO/foo/Foo")
        self.assertEqual(len(result), 1)
        c = result[0]
        self.assertEqual(c.key, "foo")
        self.assertEqual(c.variants, ["FOO", "Foo", "foo"])
        self.assertEqual(c.positions, [0, 1, 2])

    def test_same_case_repeated_is_not_a_collision(self):
        # "foo/foo" share a key AND share a spelling; no distinct variants.
        result = check_path("foo/foo")
        self.assertEqual(result, [])

    def test_multiple_independent_collisions(self):
        result = check_path("foo/Foo/bar/BAR")
        self.assertEqual(len(result), 2)
        # Sorted by first appearance position.
        self.assertEqual(result[0].key, "foo")
        self.assertEqual(result[0].positions, [0, 1])
        self.assertEqual(result[1].key, "bar")
        self.assertEqual(result[1].positions, [2, 3])

    def test_collision_with_other_components_between(self):
        result = check_path("foo/middle/Foo")
        self.assertEqual(len(result), 1)
        c = result[0]
        self.assertEqual(c.variants, ["Foo", "foo"])
        self.assertEqual(c.positions, [0, 2])

    def test_unicode_case_collision(self):
        # German sharp s: "STRASSE".casefold() == "straße".casefold().
        # This is exactly the kind of edge case casefold is meant to catch.
        result = check_path("STRASSE/straße")
        self.assertEqual(len(result), 1)
        c = result[0]
        self.assertEqual(c.key, "strasse")
        self.assertEqual(c.variants, ["STRASSE", "straße"])

    def test_variants_sorted_for_determinism(self):
        # Order of input should not affect the sorted variants output.
        r1 = check_path("Foo/foo")
        r2 = check_path("foo/Foo")
        self.assertEqual(r1[0].variants, r2[0].variants)
        self.assertEqual(r1[0].variants, ["Foo", "foo"])

    def test_non_adjacent_duplicate_spelling(self):
        # Same spelling at two positions is not a collision (no distinct
        # variant), even with unrelated components between.
        self.assertEqual(check_path("foo/a/foo"), [])


class TestCheckComponents(unittest.TestCase):
    def test_accepts_pre_split_list(self):
        result = check_components(["Foo", "foo"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].positions, [0, 1])

    def test_ignores_empty_string_components(self):
        # Empty strings are skipped to avoid degenerate empty-key collisions.
        self.assertEqual(check_components(["", "", "foo"]), [])

    def test_empty_list_returns_empty(self):
        self.assertEqual(check_components([]), [])


class TestConflictShape(unittest.TestCase):
    def test_conflict_is_frozen(self):
        c = Conflict(key="x", variants=["x"], positions=[0])
        with self.assertRaises(Exception):
            c.key = "y"  # type: ignore[misc]

    def test_conflict_fields(self):
        c = Conflict(key="k", variants=["A", "a"], positions=[0, 1])
        self.assertEqual(c.key, "k")
        self.assertEqual(c.variants, ["A", "a"])
        self.assertEqual(c.positions, [0, 1])


if __name__ == "__main__":
    unittest.main()
