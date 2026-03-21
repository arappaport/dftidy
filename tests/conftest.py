# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.

"""Shared pytest fixtures.

Auto-discovered by pytest; no import needed in test modules.
All fixture DataFrames use exact numeric values so expected results
can be calculated by hand and asserted precisely.
"""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """Five-row mixed-type DataFrame used by most tests.

    Columns:
        value : [10, 20, 30, 40, 50]  mean=30, range=40
        score : [1, 2, 3, 4, 5]       mean=3,  range=4
        label : non-numeric — exercises the skip-non-numeric path in stats.py
    """
    return pd.DataFrame(
        {
            "value": [10.0, 20.0, 30.0, 40.0, 50.0],
            "score": [1.0, 2.0, 3.0, 4.0, 5.0],
            "label": list("abcde"),
        }
    )


@pytest.fixture()
def zero_variance_df() -> pd.DataFrame:
    """All values identical — exercises the zero-variance guard."""
    return pd.DataFrame({"value": [5.0, 5.0, 5.0]})


@pytest.fixture()
def tmp_csv(tmp_path: pytest.TempPathFactory, sample_df: pd.DataFrame) -> str:
    """Write sample_df to a temporary CSV file; return its path as str.

    Uses pytest's built-in tmp_path fixture for automatic tidyup —
    no teardown logic required here.
    """
    path = tmp_path / "sample.csv"
    sample_df.to_csv(path, index=False)
    return str(path)
