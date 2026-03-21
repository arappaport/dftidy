# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.

"""
run_dftidy.py
-------------
Comprehensive pytest suite for ``tidy()`` in ``tidy.py``.

Test classes:
  TestInputTypeValidation       — TypeError on bad argument types
  TestVersionValidation         — version field acceptance / rejection
  TestIncludeUnmatchedCols      — flag behaviour and type checking
  TestMandatoryColumns          — mandatory/optional presence logic
  TestColumnRename              — rename correctness and conflict detection
  TestTypeCoercionCustom        — datestring and 8601 custom types
  TestTypeCoercionPandas        — pandas-native type aliases
  TestColumnOrdering            — output column order matches samples
  TestInplaceBehaviour          — copy vs in-place mutation semantics
  TestEdgeCases                 — empty df, empty samples, duplicates, etc.
"""

from __future__ import annotations

import pytest
import pandas as pd

from dftidy import tidy


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def base_df() -> pd.DataFrame:
    """DataFrame with all columns referenced by ``base_cfg``."""
    return pd.DataFrame(
        {
            "col1": ["2024-01-01", "2024-06-15"],
            "col2": ["2023-03-01", "2023-07-20"],
            "col3": ["2022-11-05", "2022-08-19"],
        }
    )


@pytest.fixture()
def base_cfg() -> dict:
    """Valid samples matching ``sample.yaml``."""
    return {
        "version": 1.0,
        "include-unmatched-columns": False,
        "columns": [
            {"col1": {"mandatory": None, "rename": "col1-new", "type": "datetime"}},
            {"col2": {"mandatory": False, "rename": "col2-new", "type": "datetime"}},
            {"col3": {"mandatory": True,  "rename": "col3-new", "type": "datestring"}},
        ],
    }


# ---------------------------------------------------------------------------
# 1. Input type validation
# ---------------------------------------------------------------------------


class TestInputTypeValidation:
    """tidy() must raise TypeError when arguments have wrong types."""

    def test_df_dict_raises(self, base_cfg):
        with pytest.raises(TypeError, match="'df' must be a pandas DataFrame"):
            tidy(df={"col1": [1]}, cfg=base_cfg)

    def test_df_none_raises(self, base_cfg):
        with pytest.raises(TypeError, match="'df' must be a pandas DataFrame"):
            tidy(df=None, cfg=base_cfg)

    def test_df_list_raises(self, base_cfg):
        with pytest.raises(TypeError, match="'df' must be a pandas DataFrame"):
            tidy(df=[[1, 2]], cfg=base_cfg)

    def test_df_string_raises(self, base_cfg):
        with pytest.raises(TypeError, match="'df' must be a pandas DataFrame"):
            tidy(df="dataframe", cfg=base_cfg)

    def test_cfg_string_raises(self, base_df):
        with pytest.raises(TypeError, match="'cfg' must be a dict"):
            tidy(df=base_df, cfg="samples")

    def test_cfg_none_raises(self, base_df):
        with pytest.raises(TypeError, match="'cfg' must be a dict"):
            tidy(df=base_df, cfg=None)

    def test_cfg_list_raises(self, base_df):
        with pytest.raises(TypeError, match="'cfg' must be a dict"):
            tidy(df=base_df, cfg=[{"version": 1.0}])

    def test_inplace_string_raises(self, base_df, base_cfg):
        with pytest.raises(TypeError, match="'inplace' must be a bool"):
            tidy(df=base_df, cfg=base_cfg, inplace="true")

    def test_inplace_int_raises(self, base_df, base_cfg):
        with pytest.raises(TypeError, match="'inplace' must be a bool"):
            tidy(df=base_df, cfg=base_cfg, inplace=1)

    def test_inplace_none_raises(self, base_df, base_cfg):
        with pytest.raises(TypeError, match="'inplace' must be a bool"):
            tidy(df=base_df, cfg=base_cfg, inplace=None)


# ---------------------------------------------------------------------------
# 2. Version validation
# ---------------------------------------------------------------------------


class TestVersionValidation:
    """Version field: accept 1 / 1.0 / absent; reject everything else."""

    def test_version_absent_defaults_allowed(self, base_df, base_cfg):
        cfg = {k: v for k, v in base_cfg.items() if k != "version"}
        assert tidy(base_df, cfg) is not None

    def test_version_int_1_allowed(self, base_df, base_cfg):
        base_cfg["version"] = 1
        assert tidy(base_df, base_cfg) is not None

    def test_version_float_1_0_allowed(self, base_df, base_cfg):
        base_cfg["version"] = 1.0
        assert tidy(base_df, base_cfg) is not None

    def test_version_string_1_0_allowed(self, base_df, base_cfg):
        base_cfg["version"] = "1.0"
        assert tidy(base_df, base_cfg) is not None

    def test_version_2_0_raises(self, base_df, base_cfg):
        base_cfg["version"] = 2.0
        with pytest.raises(ValueError, match="Only dftidy samples version 1.0"):
            tidy(base_df, base_cfg)

    def test_version_0_raises(self, base_df, base_cfg):
        base_cfg["version"] = 0
        with pytest.raises(ValueError, match="Only dftidy samples version 1.0"):
            tidy(base_df, base_cfg)

    def test_version_string_latest_raises(self, base_df, base_cfg):
        base_cfg["version"] = "latest"
        with pytest.raises(ValueError, match="Only dftidy samples version 1.0"):
            tidy(base_df, base_cfg)

    def test_version_none_raises(self, base_df, base_cfg):
        base_cfg["version"] = None
        with pytest.raises(ValueError, match="Only dftidy samples version 1.0"):
            tidy(base_df, base_cfg)


# ---------------------------------------------------------------------------
# 3. include-unmatched-columns
# ---------------------------------------------------------------------------


class TestIncludeUnmatchedColumns:
    """Unmatched columns are dropped (False) or retained (True)."""

    def test_false_drops_extra_column(self, base_cfg):
        df = pd.DataFrame(
            {"col1": ["2024-01-01"], "col2": ["2023-03-01"],
             "col3": ["2022-11-05"], "extra": ["drop-me"]}
        )
        base_cfg["include-unmatched-columns"] = False
        result = tidy(df, base_cfg)
        assert "extra" not in result.columns

    def test_true_retains_extra_column(self, base_cfg):
        df = pd.DataFrame(
            {"col1": ["2024-01-01"], "col2": ["2023-03-01"],
             "col3": ["2022-11-05"], "extra": ["keep-me"]}
        )
        base_cfg["include-unmatched-columns"] = True
        result = tidy(df, base_cfg)
        assert "extra" in result.columns

    def test_true_extra_column_content_unchanged(self, base_cfg):
        df = pd.DataFrame(
            {"col1": ["2024-01-01"], "col2": ["2023-03-01"],
             "col3": ["2022-11-05"], "extra": ["keep-me"]}
        )
        base_cfg["include-unmatched-columns"] = True
        result = tidy(df, base_cfg)
        assert result["extra"].iloc[0] == "keep-me"

    def test_true_unmatched_appended_after_cfg_cols(self, base_cfg):
        df = pd.DataFrame(
            {"z_extra": [1], "col1": ["2024-01-01"], "col3": ["2022-11-05"],
             "a_extra": [2], "col2": ["2023-03-01"]}
        )
        base_cfg["include-unmatched-columns"] = True
        result = tidy(df, base_cfg)
        cols = list(result.columns)
        cfg_max = max(cols.index(c) for c in ["col1-new", "col2-new", "col3-new"])
        unmatched_min = min(cols.index(c) for c in ["z_extra", "a_extra"])
        assert cfg_max < unmatched_min

    def test_non_bool_raises_type_error(self, base_df, base_cfg):
        base_cfg["include-unmatched-columns"] = "yes"
        with pytest.raises(TypeError, match="include-unmatched-columns"):
            tidy(base_df, base_cfg)

    def test_absent_defaults_to_true(self, base_cfg):
        #if "include-unmatched-columns" is not set it defaults to rtue.   Which means
        #  columns not mentioned in cfg are left as is.
        del base_cfg["include-unmatched-columns"]
        df = pd.DataFrame(
            {"col1": [1,2], "col2": [10,11],
             "extra": ["eee1", "eee2"]}
        )
        base_cfg["columns"] = [
            {"col1": {}},
            {"col2": {}},
            {"col3": {}}
        ]

        #cfg = {k: v for k, v in base_cfg.items() if k != "include-unmatched-columns"}
        result = tidy(df, base_cfg)
        #verify extra clumn is unchanged
        assert "extra" in result.columns
        assert result["extra"].tolist() == ["eee1", "eee2"]


# ---------------------------------------------------------------------------
# 4. Mandatory / optional column logic
# ---------------------------------------------------------------------------


class TestMandatoryColumns:
    """Mandatory columns must exist; optional ones may be absent."""

    def test_mandatory_true_absent_raises_key_error(self, base_cfg):
        df = pd.DataFrame({"col1": ["2024-01-01"], "col2": ["2023-03-01"]})
        with pytest.raises(KeyError, match="col3"):
            tidy(df, base_cfg)

    def test_mandatory_none_absent_no_raise(self, base_cfg):
        # col1 has mandatory: None (bare YAML key) — should be skipped silently
        df = pd.DataFrame({"col2": ["2023-03-01"], "col3": ["2022-11-05"]})
        result = tidy(df, base_cfg)
        assert "col1-new" not in result.columns

    def test_mandatory_false_absent_no_raise(self, base_cfg):
        df = pd.DataFrame({"col1": ["2024-01-01"], "col3": ["2022-11-05"]})
        result = tidy(df, base_cfg)
        assert "col2-new" not in result.columns

    def test_all_mandatory_present_succeeds(self, base_df, base_cfg):
        assert tidy(base_df, base_cfg) is not None

    def test_mandatory_col_present_in_output(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg)
        assert "col3-new" in result.columns


# ---------------------------------------------------------------------------
# 5. Column rename
# ---------------------------------------------------------------------------


class TestColumnRename:
    """Rename applied correctly; conflicts and empty values rejected."""

    def test_rename_removes_original_name(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg)
        assert "col1" not in result.columns

    def test_rename_adds_new_name(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg)
        assert "col1-new" in result.columns

    def test_all_renames_applied(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg)
        for orig in ["col1", "col2", "col3"]:
            assert orig not in result.columns
        for renamed in ["col1-new", "col2-new", "col3-new"]:
            assert renamed in result.columns

    def test_rename_target_collision_raises(self, base_cfg):
        df = pd.DataFrame(
            {"col1": ["2024-01-01"], "col2": ["2023-03-01"],
             "col3": ["2022-11-05"], "col1-new": ["collision"]}
        )
        base_cfg["include-unmatched-columns"] = True
        with pytest.raises(ValueError, match="already exists"):
            tidy(df, base_cfg)

    def test_rename_empty_string_raises(self, base_df):
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"col1": {"rename": "   "}}],
        }
        with pytest.raises(ValueError, match="empty column rename value"):
            tidy(base_df, cfg)

    def test_no_rename_key_name_preserved(self):
        df = pd.DataFrame({"col1": ["hello"]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"col1": {"mandatory": True}}],
        }
        result = tidy(df, cfg)
        assert "col1" in result.columns


# ---------------------------------------------------------------------------
# 6. Type coercion — custom types
# ---------------------------------------------------------------------------


class TestTypeCoercionCustom:
    """``datestring`` and ``8601`` produce correctly formatted strings."""

    def test_datestring_produces_object_dtype(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg)
        #changed
        #assert result["col3-new"].dtype == object
        assert pd.api.types.is_string_dtype(result["col3-new"])

    def test_datestring_format_yyyy_mm_dd(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg)
        assert result["col3-new"].iloc[0] == "2022-11-05"
        assert result["col3-new"].iloc[1] == "2022-08-19"

    def test_8601_format_no_milliseconds(self):
        df = pd.DataFrame({"ts": ["2024-01-15 10:30:45.123", "2024-06-01 00:00:00"]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"ts": {"type": "8601"}}],
        }
        result = tidy(df, cfg)
        assert result["ts"].iloc[0] == "2024-01-15T10:30:45"
        assert result["ts"].iloc[1] == "2024-06-01T00:00:00"

    def test_8601_strips_milliseconds(self):
        df = pd.DataFrame({"ts": ["2024-03-10 12:00:00.999999"]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"ts": {"type": "8601"}}],
        }
        result = tidy(df, cfg)
        assert "." not in result["ts"].iloc[0]


# ---------------------------------------------------------------------------
# 7. Type coercion — pandas-native types
# ---------------------------------------------------------------------------


class TestTypeCoercionPandas:
    """Pandas dtype aliases are applied correctly."""

    def test_datetime_produces_datetime64(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg)
        assert pd.api.types.is_datetime64_any_dtype(result["col1-new"])

    def test_datetime_correct_timestamp(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg)
        assert result["col1-new"].iloc[0] == pd.Timestamp("2024-01-01")


    #note - this isn't a valid test.  somehow the "1"'s are already converted when
    #  the df is loaded.
    def test_int_coercion(self):
        df = pd.DataFrame({"qty": ["1", "2", "3", "4"]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"qty": {"type": "int"}}],
        }
        result = tidy(df, cfg)
        assert result["qty"].iloc[0] == 1

    def test_float_coercion(self):
        df = pd.DataFrame({"price": ["1.5", "2.75"]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"price": {"type": "float"}}],
        }
        result = tidy(df, cfg)
        assert result["price"].iloc[0] == pytest.approx(1.5)

    def test_string_coercion(self):
        df = pd.DataFrame({"name": [1, 2, 3]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"name": {"type": "string"}}],
        }
        result = tidy(df, cfg)
        assert pd.api.types.is_string_dtype(result["name"])

    def test_bool_coercion(self):
        df = pd.DataFrame({"flag": [True, False, True]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"flag": {"type": "bool"}}],
        }
        result = tidy(df, cfg)
        assert result["flag"].iloc[0] is True or result["flag"].iloc[0]

    def test_unknown_type_does_raise(self, base_df):
        """Unknown type tokens raise an exception."""
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"col1": {"type": "unknownxyz"}}],
        }
        with pytest.raises(ValueError):
            result = tidy(base_df, cfg)

    def test_no_type_key_content_unchanged(self):
        df = pd.DataFrame({"col1": ["hello", "world"]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"col1": {"mandatory": True}}],
        }
        result = tidy(df, cfg)
        assert list(result["col1"]) == ["hello", "world"]

    def test_datetime_with_null_values(self):
        df = pd.DataFrame(
            {
             "col1": ["2024-01-01", None],
             "col2": ["2024-01-01", None],
             "col3": ["2024-01-01", None]}
        )
        cfg = {
            "columns": [{"col1": {"type": "datetime"}}],
        }
        result = tidy(df, cfg)
        assert pd.isna(result["col1"].iloc[1])

    @pytest.mark.parametrize("datetype", ["8601", "datetime", "datetimestring", "datestring"])
    def test_timetypes_with_blanks(self,datetype):
        df = pd.DataFrame(
            {
             "col1": ["2024-01-01", None,'', ' ']}
        )
        cfg = {
            "columns": [{"col1": {"type": datetype}}],
        }
        result = tidy(df, cfg)
        assert pd.isna(result["col1"].iloc[1])
        assert pd.isna(result["col1"].iloc[2])
        assert pd.isna(result["col1"].iloc[3])



# ---------------------------------------------------------------------------
# 8. Column ordering
# ---------------------------------------------------------------------------


class TestColumnOrdering:
    """Output column order must match samples order."""

    def test_scrambled_df_matches_cfg_order(self, base_cfg):
        df = pd.DataFrame(
            {"col3": ["2022-11-05"], "col1": ["2024-01-01"], "col2": ["2023-03-01"]}
        )
        result = tidy(df, base_cfg)
        assert list(result.columns) == ["col1-new", "col2-new", "col3-new"]

    def test_missing_optional_col_absent_from_order(self, base_cfg):
        df = pd.DataFrame({"col1": ["2024-01-01"], "col3": ["2022-11-05"]})
        result = tidy(df, base_cfg)
        assert list(result.columns) == ["col1-new", "col3-new"]

    def test_unmatched_cols_appended_after_cfg_cols(self, base_cfg):
        df = pd.DataFrame(
            {"z": [9], "col3": ["2022-11-05"], "col1": ["2024-01-01"],
             "col2": ["2023-03-01"], "a": [1]}
        )
        base_cfg["include-unmatched-columns"] = True
        result = tidy(df, base_cfg)
        cols = list(result.columns)
        assert cols[:3] == ["col1-new", "col2-new", "col3-new"]
        assert set(cols[3:]) == {"z", "a"}


# ---------------------------------------------------------------------------
# 9. inplace vs copy behaviour
# ---------------------------------------------------------------------------


class TestInplaceBehaviour:
    """inplace=False returns a copy; inplace=True mutates df and returns None."""

    def test_inplace_false_returns_dataframe(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg, inplace=False)
        assert isinstance(result, pd.DataFrame)

    def test_inplace_false_original_columns_unchanged(self, base_df, base_cfg):
        original_cols = list(base_df.columns)
        tidy(base_df, base_cfg, inplace=False)
        assert list(base_df.columns) == original_cols

    def test_inplace_true_returns_none(self, base_df, base_cfg):
        assert tidy(base_df, base_cfg, inplace=True) is None

    def test_inplace_true_mutates_df(self, base_df, base_cfg):
        tidy(base_df, base_cfg, inplace=True)
        assert "col1-new" in base_df.columns
        assert "col1" not in base_df.columns

    def test_inplace_false_result_independent_of_original(self, base_df, base_cfg):
        result = tidy(base_df, base_cfg, inplace=False)
        result["col1-new"] = "MODIFIED"
        assert "col1-new" not in base_df.columns


# ---------------------------------------------------------------------------
# 10. Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary and structural edge cases."""

    def test_empty_df_no_mandatory_no_error(self):
        df = pd.DataFrame()
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"col1": {"mandatory": False}}],
        }
        result = tidy(df, cfg)
        assert list(result.columns) == []

    def test_empty_df_mandatory_col_raises(self):
        df = pd.DataFrame()
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"col1": {"mandatory": True}}],
        }
        with pytest.raises(KeyError, match="col1"):
            tidy(df, cfg)

    def test_empty_columns_list_returns_empty(self, base_df):
        cfg = {"version": 1.0, "include-unmatched-columns": False, "columns": []}
        result = tidy(base_df, cfg)
        assert list(result.columns) == []

    def test_empty_columns_list_include_true_retains_all(self, base_df):
        cfg = {"version": 1.0, "include-unmatched-columns": True, "columns": []}
        result = tidy(base_df, cfg)
        assert set(result.columns) == set(base_df.columns)

    def test_columns_key_absent_returns_empty(self, base_df):
        cfg = {"version": 1.0, "include-unmatched-columns": False}
        result = tidy(base_df, cfg)
        assert list(result.columns) == []

    def test_single_row_dataframe(self, base_cfg):
        df = pd.DataFrame(
            {"col1": ["2024-01-01"], "col2": ["2023-03-01"], "col3": ["2022-11-05"]}
        )
        result = tidy(df, base_cfg)
        assert len(result) == 1

    def test_large_dataframe_row_count_preserved(self, base_cfg):
        n = 1000
        df = pd.DataFrame(
            {
                "col1": pd.date_range("2020-01-01", periods=n).astype(str),
                "col2": pd.date_range("2021-01-01", periods=n).astype(str),
                "col3": pd.date_range("2022-01-01", periods=n).astype(str),
            }
        )
        result = tidy(df, base_cfg)
        assert len(result) == n

    def test_duplicate_column_in_cfg_raises(self, base_df):
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [
                {"col1": {"mandatory": True}},
                {"col1": {"mandatory": True}},  # duplicate
            ],
        }
        with pytest.raises(ValueError, match="Duplicate column name"):
            tidy(base_df, cfg)

    def test_columns_not_a_list_raises(self, base_df):
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": {"col1": {}},
        }
        with pytest.raises(TypeError, match="'columns' must be a YAML sequence"):
            tidy(base_df, cfg)

    def test_columns_entry_multi_key_raises(self, base_df):
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"col1": {}, "col2": {}}],
        }
        with pytest.raises(TypeError, match="single-key mapping"):
            tidy(base_df, cfg)

    def test_all_optional_absent_empty_output(self):
        df = pd.DataFrame({"unrelated": [1, 2, 3]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [
                {"col1": {"mandatory": False}},
                {"col2": {"mandatory": False}},
            ],
        }
        result = tidy(df, cfg)
        assert list(result.columns) == []

    def test_props_bare_key_no_subkeys(self):
        """Column entry with no sub-keys (props=None after safe_load) is safe."""
        df = pd.DataFrame({"col1": ["hello"]})
        cfg = {
            "version": 1.0, "include-unmatched-columns": False,
            "columns": [{"col1": None}],  # bare key, no props
        }
        result = tidy(df, cfg)
        assert "col1" in result.columns
        assert result["col1"].iloc[0] == "hello"
