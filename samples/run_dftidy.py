# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.

"""
dftidy-demo: Load data_sample.csv and run dftidy pipeline.

dftidy public API (from arappaport/dftidy README):

NOTE: dftidy.tidy() is referenced in the README overview as config-driven
but is NOT exported in the public API. run_pipeline() is the canonical
entrypoint that chains normalise → filter → stats.
"""

from __future__ import annotations

import sys
from pathlib import Path
import logging
import yaml
import pandas as pd
import json
import dftidy

LOGGER = logging.getLogger(__name__)

CSV_ORIG_PATH              = Path("samples/data_sample.csv")
#PAth to where a csv of what we expect a tidied dataframe to look at based on CSV_ORIG_PATH
CSV_EXPECTED_TIDIED_PATH = Path("samples/data_tidied_expected.csv")
CSV_ACTUAL_TIDIED_PATH   = Path("samples/data_tidied_actual.csv")  #write ti this file

CFG_YAML_PATH             = Path("samples/config_sample.yaml")


def load_csv(path: Path) -> pd.DataFrame:
    """Load CSV with basic validation."""
    msg = dftidy.check_file(path, logger=LOGGER)
    if msg is not None:
        LOGGER.error(msg)
        raise ValueError(msg)


    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path.resolve()}")
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("CSV loaded but DataFrame is empty.")
    return df



def load_yaml(filepath: str | Path) -> dict | None:
    """
    Safely load a YAML file. Returns parsed dict or None on any error.
    Logs all failures with enough context to debug.
    """
    path = Path(filepath)

    if not path.exists():
        LOGGER.error("File not found: %s", path.resolve())
        return None

    if not path.is_file():
        LOGGER.error("Path is not a file: %s", path.resolve())
        return None

    if path.stat().st_size == 0:
        LOGGER.error("File is empty: %s", path.resolve())
        return None

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except PermissionError:
        LOGGER.error("Permission denied: %s", path.resolve())
        return None
    except UnicodeDecodeError as exc:
        LOGGER.error("File is not valid UTF-8: %s — %s", path.resolve(), exc)
        return None
    except yaml.YAMLError as exc:
        LOGGER.error("YAML parse error in %s:\n  %s", path.resolve(), exc)
        return None

    if data is None:
        LOGGER.error("File parsed but is empty document: %s", path.resolve())
        return None

    if not isinstance(data, dict):
        LOGGER.error("Expected a YAML mapping, got %s in %s", type(data).__name__, path.resolve())
        return None

    LOGGER.debug("Loaded %s (%d keys)", path.name, len(data))
    return data



#simple - generated
def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame) -> str | None:
    """
    Compare two DataFrames for structural and value equality.
    Returns None if identical, or an error string describing the first difference.
    """

    # shape
    if df1.shape != df2.shape:
        return f"Shape mismatch: {df1.shape} vs {df2.shape}"

    # columns — order matters
    if list(df1.columns) != list(df2.columns):
        return f"Column mismatch:\n  df1: {list(df1.columns)}\n  df2: {list(df2.columns)}"

    # dtypes
    if list(df1.dtypes) != list(df2.dtypes):
        return f"Dtype mismatch:\n{df1.dtypes.compare(df2.dtypes)}"

    # values — NaN-safe comparison
    if not df1.equals(df2):
        diff = df1.compare(df2)
        return f"Value mismatch in {len(diff)} row(s):\n{diff}"

    return None

def main() -> None:

    print(f"Using dftidy version: ", dftidy.__version__)

    print(f"Loading {CSV_ORIG_PATH} ...")
    df_orig = load_csv(CSV_ORIG_PATH)
    print(f"Pre-tidy:: {df_orig.shape[0]} rows × {df_orig.shape[1]} cols\n")

    print(f"Loading {CFG_YAML_PATH} ...")
    cfg = load_yaml(CFG_YAML_PATH)

    msg = dftidy.validate_cfg(colcfg=cfg)
    if msg is not None:
        LOGGER.error(msg)
        exit(-1)
    print(json.dumps(cfg, indent=2))

    df_tidied = dftidy.tidy(df_orig, cfg=cfg, inplace=False)

    print("after dftidy")
    print(df_tidied.head())

    df_expected = load_csv(CSV_EXPECTED_TIDIED_PATH)

    # standard — no index, utf-8
    df_tidied.to_csv(CSV_ACTUAL_TIDIED_PATH, index=False)
    print(f" wrote tidied dataframe to [{CSV_ACTUAL_TIDIED_PATH.resolve()}]")

    are_eq = df_tidied.equals(df_expected)
    LOGGER.info("df_tidied == df_expected: %s",are_eq)
    if are_eq:
        LOGGER.info("tidied dataframe equals expected.  See [%s]", Path(CSV_EXPECTED_TIDIED_PATH).resolve())
    else:

        LOGGER.error("not equal.  Check expected file: [%s]", Path(CSV_EXPECTED_TIDIED_PATH).resolve())
        LOGGER.error("comparing tidied to expected- using df_orig.compare()")
        LOGGER.error(df_tidied.compare(df_expected))

        msg = compare_dataframes(df_tidied, df_expected)
        LOGGER.error(msg)


    dbg = 12
