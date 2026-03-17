# MIT License
# Copyright (c) 2026 Andy Rappaport
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


# GENERATED FILE - DO NOT EDIT DIRECTLY. Prompt:[cdfclean.txt] version:[1.0] at[2026-03-01T23:49:22Z]
"""
clean.py
--------
Production-grade DataFrame cleaning function driven by a dfclean YAML samples.

Supported samples syntax version: 1.0

Type coercion supports all pandas-native types plus the following custom types:
  - ``datestring`` : converts to string in ``YYYY-MM-DD`` format
  - ``8601``       : converts to ISO-8601 string without milliseconds
                     e.g. ``"2024-01-15T10:30:00"``
  -   datestimestring - string of date in format YYYYMMDD-HHMMSS
"""

from __future__ import annotations

import logging

from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_VERSION: float = 1.0

# Custom type tokens handled explicitly before pandas fallback
_CUSTOM_TYPES: frozenset[str] = frozenset({"datestring", "datetimestring", "8601"})

# Pandas-native type aliases accepted in cfg.type
_PANDAS_TYPE_MAP: dict[str, str] = {
    "int":      "Int64",      # nullable integer
    "integer":  "Int64",
    "float":    "float64",
    "double":   "float64",
    "str":      "string",
    "string":   "string",
    "bool":     "boolean",
    "boolean":  "boolean",
    "datetime": "datetime64[ns]",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_version(cfg: dict) -> None:
    """Validate the samples ``version`` field.

    Args:
        cfg: Parsed YAML samples dictionary.

    Raises:
        ValueError: If the version is not ``1`` or ``1.0``.
    """
    raw = cfg.get("version", 1.0)
    try:
        version = float(raw)
    except (TypeError, ValueError):
        raise ValueError(
            f"Only dfclean samples version 1.0 is supported, got: {raw!r}"
        )
    if version != SUPPORTED_VERSION:
        raise ValueError(
            f"Only dfclean samples version 1.0 is supported, got: {version}"
        )


def _get_include_unmatched(cfg: dict) -> bool:
    """Read and validate the ``include-unmatched-columns`` flag.

    Defaults to ``True`` when absent.

    Args:
        cfg: Parsed YAML samples dictionary.

    Returns:
        ``True`` if unmatched DataFrame columns should be retained.

    Raises:
        TypeError: If the value is present but is not a Python ``bool``.
    """
    value = cfg.get("include-unmatched-columns", True)
    if value is None:
        value = True
    if not isinstance(value, bool):
        raise TypeError(
            f"'include-unmatched-columns' must be a boolean (true/false), "
            f"got {type(value).__name__!r}: {value!r}"
        )
    return value


def _parse_column_definitions(cfg: dict) -> list[tuple[str, dict]]:
    """Extract and normalise column definitions from the samples.

    Each YAML ``columns`` entry is a single-key mapping::

        - col1:
            mandatory: true
            rename: col1-new
            type: datetime

    After ``yaml.safe_load`` this becomes a list of one-key dicts.

    Args:
        cfg: Parsed YAML samples dictionary.

    Returns:
        Ordered list of ``(column_name, properties_dict)`` tuples.

    Raises:
        TypeError:  If ``columns`` is not a list, or an entry is malformed.
        ValueError: If a column name is empty or duplicated.
    """
    raw = cfg.get("columns", []) or []
    if not isinstance(raw, list):
        raise TypeError(
            f"'columns' must be a YAML sequence (list), got {type(raw).__name__!r}."
        )

    seen: set[str] = set()
    result: list[tuple[str, dict]] = []

    for index, item in enumerate(raw):
        if not isinstance(item, dict) or len(item) != 1:
            raise TypeError(
                f"Entry {index} under 'columns' must be a single-key mapping, "
                f"got: {item!r}"
            )
        col_name, props = next(iter(item.items()))
        col_name = str(col_name).strip()

        if not col_name:
            raise ValueError(f"Column at index {index} has an empty name.")
        if col_name in seen:
            raise ValueError(
                f"Duplicate column name '{col_name}' at index {index} in samples."
            )
        seen.add(col_name)

        props = props if isinstance(props, dict) else {}
        result.append((col_name, props))

    return result


def _is_mandatory(props: dict) -> bool:
    """Return ``True`` only when ``mandatory`` is explicitly ``True``.

    A bare YAML key (``mandatory:``) resolves to ``None`` after ``safe_load``,
    which is treated as *not* mandatory — same as ``mandatory: false``.

    Args:
        props: Property dict for a single column definition.

    Returns:
        ``True`` if the column is mandatory; ``False`` otherwise.
    """
    return props.get("mandatory", None) is True


def _validate_rename(rename_val: str, col_name: str, columns: pd.Index) -> None:
    """Validate a proposed rename target.

    Args:
        rename_val: Intended new column name.
        col_name:   Current column name (for error messages).
        columns:    Current DataFrame column index.

    Raises:
        ValueError: If ``rename_val`` is empty, or already exists under a
                    different name.
    """

    #rename column is option.
    if not rename_val:
        raise ValueError(f"empty column rename value. Column name:[{col_name!r}]")
    if rename_val in columns and rename_val != col_name:
        raise ValueError(
            f"Column '{col_name}': cannot rename to '{rename_val}' — "
            f"a column with that name already exists in the DataFrame."
        )


def _coerce_series_type(
    series: pd.Series,
    col_type: str,
    col_name: str,
) -> pd.Series:
    """Coerce a Series to the type specified in the samples.

    Custom types handled first:

    * ``datestring`` — ISO date string ``"YYYY-MM-DD"``.
    * ``8601``       — ISO-8601 datetime string without milliseconds,
                       e.g. ``"2024-01-15T10:30:00"``.

    All other values are treated as pandas dtype aliases (e.g. ``"int"``,
    ``"float"``, ``"string"``, ``"bool"``, ``"datetime"``).  Unknown values
    emit a warning and leave the Series unchanged.

    Args:
        series:   The pandas Series to coerce.
        col_type: Type token from the samples.
        col_name: Column name used in error messages.

    Returns:
        A new Series with values coerced to the requested type.

    Raises:
        ValueError: If the conversion fails.
    """
    normalised = str(col_type).strip().lower()

    # ------------------------------------------------------------------
    # Custom types
    # ------------------------------------------------------------------
    if normalised == "datestring":
        try:
            return pd.to_datetime(series, format="mixed",errors="coerce").dt.strftime("%Y-%m-%d")
        except Exception as exc:
            raise ValueError(
                f"Column '{col_name}': datestring conversion failed — {exc}"
            ) from exc

    if normalised == "datetimestring":
        try:
            return pd.to_datetime(series, format="mixed",errors="coerce").dt.strftime("%Y%m%d-%H%M%S")
        except Exception as exc:
            raise ValueError(
                f"Column '{col_name}': datestring conversion failed — {exc}"
            ) from exc

    if normalised == "8601":
        try:
            dt = pd.to_datetime(series, format="mixed",errors="coerce")
            # Strip sub-second precision and timezone offset for clean ISO strings
            return dt.dt.floor("s").dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception as exc:
            raise ValueError(
                f"Column '{col_name}': 8601 conversion failed — {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Pandas-native type aliases
    # ------------------------------------------------------------------
    pandas_dtype = _PANDAS_TYPE_MAP.get(normalised, normalised)

    if pandas_dtype.startswith("datetime"):
        try:
            return pd.to_datetime(series, format="mixed", errors="coerce")
        except Exception as exc:
            raise ValueError(
                f"Column '{col_name}': datetime conversion failed — {exc}"
            ) from exc

    try:
        return series.astype(pandas_dtype)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Column '{col_name}': cannot cast to type '{col_type}' "
            f"(resolved: '{pandas_dtype}') — {exc}"
        ) from exc
    except Exception:
        log.warning(
            "Column '%s': unknown type '%s' — skipping coercion.",
            col_name,
            col_type,
        )
        return series


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def clean(
    df: pd.DataFrame,
    cfg: dict,
    inplace: bool = False,
) -> Optional[pd.DataFrame]:
    """Clean and validate a pandas DataFrame using a dfclean YAML samples.

    Operations performed in order:

    1. Type-validates all three arguments.
    2. Validates samples version (only ``1.0`` supported).
    3. Reads ``include-unmatched-columns`` (defaults to ``False``).
    4. Parses ordered column definitions from ``cfg["columns"]``.
    5. For each defined column:

       a. Checks presence; raises ``KeyError`` if mandatory and absent.
       b. Coerces the column type when ``type`` is specified.
       c. Collects renames for atomic application after the loop.

    6. Applies all renames in a single ``DataFrame.rename()`` call.
    7. Reorders output columns to match the samples order.
    8. Drops or retains unmatched columns per ``include-unmatched-columns``.

    Args:
        df: Source pandas DataFrame to clean.
        cfg: Python dict produced by ``yaml.safe_load()`` on a dfclean
            samples file.
        inplace: If ``True``, mutate *df* in place and return ``None``.
            If ``False`` (default), operate on a copy and return it.

    Returns:
        Cleaned ``pd.DataFrame`` when ``inplace=False``, or ``None`` when
        ``inplace=True``.

    Raises:
        TypeError: If *df* is not a ``pd.DataFrame``, *cfg* is not a ``dict``,
            *inplace* is not a ``bool``, or a samples value has the wrong type.
        ValueError: If the samples version is unsupported, a rename target is
            invalid, or type coercion fails.
        KeyError: If a mandatory column is absent from the DataFrame.

    Example::

        import yaml, pandas as pd
        from clean import clean

        cfg = yaml.safe_load(open("sample.yaml"))
        df  = pd.DataFrame({
            "col1": ["2024-01-01"],
            "col2": ["2023-06-15"],
            "col3": ["2022-03-10"],
        })
        result = clean(df, cfg)
        # result has columns: col1-new (datetime64), col2-new (datetime64),
        #                      col3-new (YYYY-MM-DD string)
    """
    # ------------------------------------------------------------------
    # 1. Argument type validation
    # ------------------------------------------------------------------
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"'df' must be a pandas DataFrame, got {type(df).__name__!r}."
        )
    if not isinstance(cfg, dict):
        raise TypeError(
            f"'cfg' must be a dict, got {type(cfg).__name__!r}."
        )
    if not isinstance(inplace, bool):
        raise TypeError(
            f"'inplace' must be a bool, got {type(inplace).__name__!r}."
        )

    # ------------------------------------------------------------------
    # 2. Config-level validation
    # ------------------------------------------------------------------
    _validate_version(cfg)
    include_unmatched: bool = _get_include_unmatched(cfg)
    col_defs: list[tuple[str, dict]] = _parse_column_definitions(cfg)
    cfg_col_names: list[str] = [name for name, _ in col_defs]

    log.info(
        "dfclean: %d column(s) in samples | include-unmatched-columns=%s",
        len(cfg_col_names),
        include_unmatched,
    )

    # ------------------------------------------------------------------
    # 3. Work on a copy unless inplace
    # ------------------------------------------------------------------
    target: pd.DataFrame = df if inplace else df.copy()

    # ------------------------------------------------------------------
    # 4. Per-column: mandatory → coerce → collect rename
    # ------------------------------------------------------------------
    rename_map: dict[str, str] = {}

    for col_name, props in col_defs:
        col_exists: bool = col_name in target.columns

        # --- 4a. Mandatory check ---------------------------------------
        if not col_exists:
            if _is_mandatory(props):
                raise KeyError(
                    f"Mandatory column '{col_name}' is missing from the DataFrame. "
                    f"Present columns: {list(target.columns)}"
                )
            log.warning(
                "Optional column '%s' not found in DataFrame — skipping.", col_name
            )
            continue

        log.info("Processing column '%s'.", col_name)

        # --- 4b. Type coercion -----------------------------------------
        col_type: Optional[str] = props.get("type", None)
        if col_type is not None:
            target[col_name] = _coerce_series_type(
                target[col_name], col_type, col_name
            )
            log.info("  '%s' coerced to type '%s'.", col_name, col_type)

        # --- 4c. Rename collection -------------------------------------
        val = props.get("rename", None)
        if val is not None:
            val = str(val).strip()
            _validate_rename(val, col_name, target.columns)
            rename_map[col_name] = val
            log.info("  Queued rename: '%s' → '%s'.", col_name, val)

        # --- 4d. Change value collection -------------------------------------
        val = props.get("value", None)
        if val is not None:
            target[col_name] = val
            log.info("  Col[%s] → '%s'.", col_name, val)


    # ------------------------------------------------------------------
    # 5. Apply all renames atomically
    # ------------------------------------------------------------------
    if rename_map:
        target.rename(columns=rename_map, inplace=True)
        log.info("Applied renames: %s", rename_map)

    # ------------------------------------------------------------------
    # 6. Build final column order
    #    cfg columns (post-rename) first, in samples order.
    #    Unmatched columns appended at end if include_unmatched=True.
    # ------------------------------------------------------------------
    ordered_cfg_cols: list[str] = []
    for original_name in cfg_col_names:
        final_name = rename_map.get(original_name, original_name)
        if final_name in target.columns:
            ordered_cfg_cols.append(final_name)

    if include_unmatched:
        unmatched = [c for c in target.columns if c not in ordered_cfg_cols]
        final_col_order = ordered_cfg_cols + unmatched
        log.info(
            "Retaining %d unmatched column(s): %s", len(unmatched), unmatched
        )
    else:
        dropped = [c for c in target.columns if c not in ordered_cfg_cols]
        final_col_order = ordered_cfg_cols
        if dropped:
            log.info(
                "Dropping %d unmatched column(s): %s", len(dropped), dropped
            )

    target = target[final_col_order]

    #handle column case change - happens last - after all other processing has happened
    if cfg.get("columns-case") == "lower":
        target.columns = target.columns.str.lower()
    elif cfg.get("columns-case") == "upper":
        target.columns = target.columns.str.upper()



    # ------------------------------------------------------------------
    # 7. Return
    # ------------------------------------------------------------------
    if inplace:
        df.__dict__.update(target.__dict__)
        return None
    return target
