# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.



# SPDX-License-Identifier: Unlicense
"""
Comprehensive pytest suite for process_removes.py

Coverage targets:
  - _validate_dataframe
  - _validate_df_config
  - _validate_inplace
  - _get_columns_to_remove
  - _drop_columns
  - process_removes (integration + edge cases)
"""

from __future__ import annotations

import pytest
import pandas as pd

from dftidy.process_removes import (
    _validate_dataframe,
    _validate_df_config,
    _validate_inplace,
    _get_columns_to_remove,
    _drop_columns,
    process_removes,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_df() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})


@pytest.fixture
def base_config() -> dict:
    return {"remove": ["a", "b"]}


# ---------------------------------------------------------------------------
# _validate_dataframe
# ---------------------------------------------------------------------------

class TestValidateDataframe:
    def test_valid_dataframe_passes(self, simple_df):
        _validate_dataframe(simple_df)  # no exception

    def test_not_a_dataframe_raises_type_error(self):
        with pytest.raises(TypeError, match="pandas DataFrame"):
            _validate_dataframe({"a": [1, 2]})

    def test_list_raises_type_error(self):
        with pytest.raises(TypeError):
            _validate_dataframe([1, 2, 3])

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            _validate_dataframe(None)

    def test_empty_dataframe_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_dataframe(pd.DataFrame())

    def test_dataframe_with_no_rows_raises_value_error(self):
        """Zero-row DF with columns is still considered empty by pandas."""
        with pytest.raises(ValueError):
            _validate_dataframe(pd.DataFrame({"a": pd.Series([], dtype=int)}))


# ---------------------------------------------------------------------------
# _validate_df_config
# ---------------------------------------------------------------------------

class TestValidateDfConfig:
    def test_valid_config_passes(self):
        _validate_df_config({"remove": ["a"]})

    def test_not_a_dict_raises_type_error(self):
        with pytest.raises(TypeError, match="dictionary"):
            _validate_df_config(["remove", "a"])

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            _validate_df_config(None)

    def test_empty_dict_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_df_config({})

    def test_config_without_remove_key_passes(self):
        """Keys other than 'remove' are valid; missing 'remove' is fine."""
        _validate_df_config({"keep": ["x"]})


# ---------------------------------------------------------------------------
# _validate_inplace
# ---------------------------------------------------------------------------

class TestValidateInplace:
    def test_true_passes(self):
        _validate_inplace(True)

    def test_false_passes(self):
        _validate_inplace(False)

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError, match="boolean"):
            _validate_inplace("true")

    def test_int_raises_type_error(self):
        """1 / 0 are ints, not bool — even though bool subclasses int in Python."""
        # bool IS a subclass of int, but isinstance(True, bool) is True
        # whereas isinstance(1, bool) is False — this test confirms ints fail
        with pytest.raises(TypeError):
            _validate_inplace(1)

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            _validate_inplace(None)


# ---------------------------------------------------------------------------
# _get_columns_to_remove
# ---------------------------------------------------------------------------

class TestGetColumnsToRemove:
    def test_returns_list_when_remove_key_present(self):
        result = _get_columns_to_remove({"remove": ["a", "b"]})
        assert result == ["a", "b"]

    def test_returns_empty_list_when_remove_key_missing(self):
        result = _get_columns_to_remove({"other": "value"})
        assert result == []

    def test_returns_empty_list_when_remove_is_none(self):
        result = _get_columns_to_remove({"remove": None})
        assert result == []

    def test_returns_empty_list_for_empty_remove_list(self):
        result = _get_columns_to_remove({"remove": []})
        assert result == []

    def test_raises_type_error_when_remove_not_a_list(self):
        with pytest.raises(TypeError, match="list of strings"):
            _get_columns_to_remove({"remove": "a"})

    def test_raises_type_error_when_remove_contains_non_strings(self):
        with pytest.raises(TypeError, match="strings"):
            _get_columns_to_remove({"remove": ["a", 42]})

    def test_raises_type_error_when_remove_is_tuple(self):
        with pytest.raises(TypeError):
            _get_columns_to_remove({"remove": ("a", "b")})


# ---------------------------------------------------------------------------
# _drop_columns
# ---------------------------------------------------------------------------

class TestDropColumns:
    def test_drops_existing_columns_not_inplace(self, simple_df):
        result = _drop_columns(simple_df, ["a", "b"], inplace=False)
        assert list(result.columns) == ["c"]
        assert "a" in simple_df.columns  # original unchanged

    def test_drops_existing_columns_inplace(self, simple_df):
        result = _drop_columns(simple_df, ["a"], inplace=True)
        assert "a" not in result.columns
        assert result is simple_df  # same object

    def test_ignores_nonexistent_columns(self, simple_df):
        result = _drop_columns(simple_df, ["z", "x"], inplace=False)
        assert set(result.columns) == {"a", "b", "c"}

    def test_empty_columns_to_remove_returns_copy_not_inplace(self, simple_df):
        result = _drop_columns(simple_df, [], inplace=False)
        assert list(result.columns) == list(simple_df.columns)
        assert result is not simple_df  # must be a copy

    def test_empty_columns_to_remove_returns_same_object_inplace(self, simple_df):
        result = _drop_columns(simple_df, [], inplace=True)
        assert result is simple_df

    def test_partial_overlap_drops_only_existing(self, simple_df):
        result = _drop_columns(simple_df, ["a", "nonexistent"], inplace=False)
        assert "a" not in result.columns
        assert "b" in result.columns

    def test_drop_all_columns(self, simple_df):
        result = _drop_columns(simple_df, ["a", "b", "c"], inplace=False)
        assert result.empty

    def test_data_integrity_preserved(self, simple_df):
        result = _drop_columns(simple_df, ["a"], inplace=False)
        assert result["b"].tolist() == [3, 4]
        assert result["c"].tolist() == [5, 6]


# ---------------------------------------------------------------------------
# process_removes — integration tests
# ---------------------------------------------------------------------------

class TestProcessRemoves:

    # --- happy path ---

    def test_basic_remove_not_inplace(self, simple_df, base_config):
        result = process_removes(simple_df, base_config, inplace=False)
        assert "a" not in result.columns
        assert "b" not in result.columns
        assert "c" in result.columns

    def test_basic_remove_inplace(self, simple_df, base_config):
        result = process_removes(simple_df, base_config, inplace=True)
        assert result is simple_df
        assert "a" not in simple_df.columns

    def test_no_remove_key_returns_copy(self, simple_df):
        result = process_removes(simple_df, {"keep": ["c"]}, inplace=False)
        assert list(result.columns) == list(simple_df.columns)
        assert result is not simple_df

    def test_remove_nonexistent_columns_no_error(self, simple_df):
        result = process_removes(simple_df, {"remove": ["x", "y"]}, inplace=False)
        assert set(result.columns) == {"a", "b", "c"}

    def test_remove_empty_list(self, simple_df):
        result = process_removes(simple_df, {"remove": []}, inplace=False)
        assert list(result.columns) == list(simple_df.columns)

    def test_default_inplace_is_false(self, simple_df, base_config):
        result = process_removes(simple_df, base_config)
        assert result is not simple_df
        assert "a" in simple_df.columns  # original unmodified

    def test_config_with_extra_keys(self, simple_df):
        config = {"remove": ["a"], "dtype": "float32", "fillna": 0}
        result = process_removes(simple_df, config)
        assert "a" not in result.columns
        assert "b" in result.columns

    def test_single_row_dataframe(self):
        df = pd.DataFrame({"x": [1], "y": [2]})
        result = process_removes(df, {"remove": ["x"]})
        assert list(result.columns) == ["y"]

    def test_wide_dataframe_removes_subset(self):
        cols = [f"col_{i}" for i in range(50)]
        df = pd.DataFrame({c: [1] for c in cols})
        to_remove = cols[:10]
        result = process_removes(df, {"remove": to_remove})
        assert len(result.columns) == 40
        assert not any(c in result.columns for c in to_remove)

    def test_column_order_preserved(self, simple_df):
        result = process_removes(simple_df, {"remove": ["b"]})
        assert list(result.columns) == ["a", "c"]

    def test_returns_dataframe_type(self, simple_df, base_config):
        result = process_removes(simple_df, base_config)
        assert isinstance(result, pd.DataFrame)

    # --- type/value error propagation ---

    def test_raises_type_error_for_non_dataframe(self, base_config):
        with pytest.raises(TypeError):
            process_removes({"a": [1]}, base_config)

    def test_raises_value_error_for_empty_dataframe(self, base_config):
        with pytest.raises(ValueError):
            process_removes(pd.DataFrame(), base_config)

    def test_raises_type_error_for_non_dict_config(self, simple_df):
        with pytest.raises(TypeError):
            process_removes(simple_df, ["remove", "a"])

    def test_raises_value_error_for_empty_config(self, simple_df):
        with pytest.raises(ValueError):
            process_removes(simple_df, {})

    def test_raises_type_error_for_non_bool_inplace(self, simple_df, base_config):
        with pytest.raises(TypeError):
            process_removes(simple_df, base_config, inplace="yes")

    def test_raises_type_error_when_remove_contains_int(self, simple_df):
        with pytest.raises(TypeError):
            process_removes(simple_df, {"remove": [1, 2]})

    def test_raises_type_error_when_remove_is_string_not_list(self, simple_df):
        with pytest.raises(TypeError):
            process_removes(simple_df, {"remove": "a"})

    # --- data integrity ---

    def test_values_unchanged_after_remove(self, simple_df):
        result = process_removes(simple_df, {"remove": ["a"]})
        assert result["b"].tolist() == [3, 4]
        assert result["c"].tolist() == [5, 6]

    def test_index_preserved(self):
        df = pd.DataFrame({"a": [10, 20], "b": [30, 40]}, index=[5, 10])
        result = process_removes(df, {"remove": ["a"]})
        assert list(result.index) == [5, 10]

    def test_dtypes_preserved(self):
        df = pd.DataFrame({"a": pd.array([1], dtype="int32"), "b": ["x"]})
        result = process_removes(df, {"remove": ["a"]})
        assert result["b"].dtype == object
