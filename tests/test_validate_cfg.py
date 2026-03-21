# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.

"""
Comprehensive pytest suite for validate_cfg.py.

Coverage strategy:
  - validate_cfg: top-level guard, empty dict, each field branch, field combinations
  - _validate_columns: tested indirectly via validate_cfg (private fn, no direct import)

Known behavioural quirks documented as tests (not bugs to fix here):
  - include-unmatched-columns present + valid → early return, skips remove/columns validation
  - include-unmatched-columns: empty string "" is accepted as valid
  - _validate_columns validates structure only; inner key VALUES are not checked
"""

import pytest
from dftidy.validate_cfg import validate_cfg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_valid(result) -> bool:
    return result is None


def is_error(result) -> bool:
    return isinstance(result, str) and len(result) > 0


# ===========================================================================
# validate_cfg — top-level type guard
# ===========================================================================

class TestTopLevelTypeGuard:
    """colcfg must be a dict."""

    @pytest.mark.parametrize("bad_input", [
        None,
        [],
        "string",
        42,
        3.14,
        ("a", "b"),
        set(),
    ])
    def test_non_dict_returns_error(self, bad_input):
        result = validate_cfg(bad_input)
        assert is_error(result)
        assert "dictionary" in result.lower()

    def test_empty_dict_returns_error(self):
        result = validate_cfg({})
        assert is_error(result)
        assert "empty" in result.lower()


# ===========================================================================
# validate_cfg — minimal valid configs
# ===========================================================================

class TestMinimalValidConfigs:
    """Any non-empty dict with recognised keys in valid state → None."""

    def test_only_remove_valid(self):
        assert is_valid(validate_cfg({"remove": ["col_a", "col_b"]}))

    def test_only_columns_valid(self):
        cfg = {"columns": [{"mandatory": True, "rename": "new_name", "type": "int"}]}
        assert is_valid(validate_cfg(cfg))

    def test_only_include_unmatched_true(self):
        assert is_valid(validate_cfg({"include-unmatched-columns": True}))

    def test_only_include_unmatched_false(self):
        assert is_valid(validate_cfg({"include-unmatched-columns": False}))

    def test_only_include_unmatched_none(self):
        # None value is explicitly allowed
        assert is_valid(validate_cfg({"include-unmatched-columns": None}))

    def test_only_include_unmatched_empty_string(self):
        # "" is treated as valid (same branch as None)
        assert is_valid(validate_cfg({"include-unmatched-columns": ""}))

    def test_unknown_top_level_key_only(self):
        # No validation for unknown keys — should pass (no error path hits)
        assert is_valid(validate_cfg({"unknown_key": "anything"}))


# ===========================================================================
# include-unmatched-columns
# ===========================================================================

class TestIncludeUnmatchedColumns:
    """Field-level validation for include-unmatched-columns."""

    @pytest.mark.parametrize("valid_value", [True, False, None, ""])
    def test_valid_values(self, valid_value):
        assert is_valid(validate_cfg({"include-unmatched-columns": valid_value}))

    @pytest.mark.parametrize("bad_value", [
        "yes", "true", "false", "1", 1, 0, [], {}, 3.14,
    ])
    def test_invalid_values_return_error(self, bad_value):
        result = validate_cfg({"include-unmatched-columns": bad_value})
        assert is_error(result)
        assert "include-unmatched-columns" in result

    def test_early_return_skips_remove_validation(self):
        """
        KNOWN BEHAVIOUR: when include-unmatched-columns is present and valid,
        validate_cfg returns None immediately — invalid 'remove' is NOT caught.
        This test documents the current behaviour; update if the bug is fixed.
        """
        cfg = {
            "include-unmatched-columns": True,
            "remove": "not-a-list",   # would normally be an error
        }
        result = validate_cfg(cfg)
        # Current behaviour: early return → None (no error raised for 'remove')
        assert is_valid(result)

    def test_early_return_skips_columns_validation(self):
        """
        KNOWN BEHAVIOUR: same early-return issue; invalid 'columns' not caught.
        """
        cfg = {
            "include-unmatched-columns": False,
            "columns": "not-a-list",  # would normally be an error
        }
        result = validate_cfg(cfg)
        assert is_valid(result)


# ===========================================================================
# remove
# ===========================================================================

class TestRemoveField:

    def test_valid_list_of_strings(self):
        assert is_valid(validate_cfg({"remove": ["a", "b", "c"]}))

    def test_empty_list_is_valid(self):
        # No constraint on minimum length
        assert is_valid(validate_cfg({"remove": []}))

    def test_single_string_element(self):
        assert is_valid(validate_cfg({"remove": ["only_one"]}))

    @pytest.mark.parametrize("bad_remove", [
        "a_string",
        42,
        None,
        {"key": "val"},
        ("a", "b"),
    ])
    def test_non_list_returns_error(self, bad_remove):
        result = validate_cfg({"remove": bad_remove})
        assert is_error(result)
        assert "remove" in result.lower()

    @pytest.mark.parametrize("bad_elements", [
        [1, 2, 3],
        ["valid", 99],
        [None],
        [["nested"]],
        [{"dict": "item"}],
    ])
    def test_non_string_elements_return_error(self, bad_elements):
        result = validate_cfg({"remove": bad_elements})
        assert is_error(result)
        assert "remove" in result.lower()


# ===========================================================================
# columns — top-level field
# ===========================================================================

class TestColumnsFieldTopLevel:

    def test_valid_empty_list(self):
        assert is_valid(validate_cfg({"columns": []}))

    def test_valid_single_entry_all_keys(self):
        cfg = {"columns": [{"mandatory": True, "rename": "x", "type": "str"}]}
        assert is_valid(validate_cfg(cfg))

    def test_valid_multiple_entries(self):
        cfg = {"columns": [
            {"mandatory": True},
            {"rename": "new_col"},
            {"type": "float"},
        ]}
        assert is_valid(validate_cfg(cfg))

    @pytest.mark.parametrize("bad_value", [
        "not-a-list",
        42,
        None,
        {"key": "val"},
        ("a",),
    ])
    def test_non_list_columns_returns_error(self, bad_value):
        result = validate_cfg({"columns": bad_value})
        assert is_error(result)
        assert "columns" in result.lower()


# ===========================================================================
# _validate_columns — via columns entries
# ===========================================================================

class TestColumnsEntryValidation:
    """Validates each dict entry inside the columns list."""

    def test_entry_must_be_dict(self):
        result = validate_cfg({"columns": ["not-a-dict"]})
        assert is_error(result)
        assert "dictionary" in result.lower()

    def test_entry_integer_returns_error(self):
        result = validate_cfg({"columns": [42]})
        assert is_error(result)

    def test_entry_none_returns_error(self):
        result = validate_cfg({"columns": [None]})
        assert is_error(result)

    def test_invalid_key_in_entry(self):
        result = validate_cfg({"columns": [{"unknown_key": "val"}]})
        assert is_error(result)
        assert "unknown_key" in result

    def test_invalid_key_reports_correct_index(self):
        cfg = {"columns": [
            {"mandatory": True},         # index 0 — valid
            {"bad_key": "val"},           # index 1 — invalid
        ]}
        result = validate_cfg(cfg)
        assert is_error(result)
        assert "columns[1]" in result

    @pytest.mark.parametrize("valid_key", ["mandatory", "rename", "type"])
    def test_each_allowed_key_individually(self, valid_key):
        cfg = {"columns": [{valid_key: "anything"}]}
        assert is_valid(validate_cfg(cfg))

    def test_all_allowed_keys_together(self):
        cfg = {"columns": [{"mandatory": True, "rename": "col", "type": "int"}]}
        assert is_valid(validate_cfg(cfg))

    def test_empty_dict_entry_is_valid(self):
        # No required keys enforced — empty dict has no disallowed keys
        assert is_valid(validate_cfg({"columns": [{}]}))

    def test_values_of_allowed_keys_not_validated(self):
        """
        KNOWN BEHAVIOUR: _validate_columns only checks key names, not values.
        Nonsense values for mandatory/rename/type pass through.
        """
        cfg = {"columns": [{"mandatory": "not-a-bool", "type": 9999, "rename": []}]}
        assert is_valid(validate_cfg(cfg))

    def test_mixed_valid_and_invalid_entries(self):
        cfg = {"columns": [
            {"mandatory": True},
            {"invalid_key": "x"},
        ]}
        result = validate_cfg(cfg)
        assert is_error(result)

    def test_multiple_valid_entries_all_pass(self):
        cfg = {"columns": [
            {"mandatory": False},
            {"rename": "new"},
            {"type": "datetime"},
            {"mandatory": True, "rename": "x", "type": "float"},
        ]}
        assert is_valid(validate_cfg(cfg))


# ===========================================================================
# Field combinations (without include-unmatched-columns — avoids early-return)
# ===========================================================================

class TestFieldCombinations:
    """
    Combinations of remove + columns without include-unmatched-columns,
    since that key triggers early return and masks subsequent validation.
    """

    def test_remove_and_columns_both_valid(self):
        cfg = {
            "remove": ["drop_me"],
            "columns": [{"mandatory": True, "rename": "kept"}],
        }
        assert is_valid(validate_cfg(cfg))

    def test_valid_remove_invalid_columns(self):
        cfg = {
            "remove": ["drop_me"],
            "columns": "not-a-list",
        }
        result = validate_cfg(cfg)
        assert is_error(result)

    def test_invalid_remove_valid_columns(self):
        cfg = {
            "remove": 999,
            "columns": [{"mandatory": True}],
        }
        result = validate_cfg(cfg)
        assert is_error(result)
        assert "remove" in result.lower()

    def test_invalid_remove_invalid_columns_remove_checked_first(self):
        """remove is checked before columns in source order."""
        cfg = {
            "remove": "bad",
            "columns": "also-bad",
        }
        result = validate_cfg(cfg)
        assert is_error(result)
        assert "remove" in result.lower()

    def test_unknown_key_alongside_valid_fields(self):
        cfg = {
            "remove": ["x"],
            "columns": [{"type": "int"}],
            "unrecognised": True,
        }
        assert is_valid(validate_cfg(cfg))