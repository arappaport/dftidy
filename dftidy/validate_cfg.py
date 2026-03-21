# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.

"""
Validation utilities for dftidy configuration dictionaries.
"""

from typing import Any, Dict, List, Optional


def _validate_columns(value: Any) -> Optional[str]:
    """Validate the columns field.

    Args:
        value: The value to validate.

    Returns:
        None if valid, otherwise an error message.
    """
    if not isinstance(value, list):
        return "\'columns\' must be a list."

    for idx, col in enumerate(value):
        if not isinstance(col, dict):
            return f"columns[{idx}] must be a dictionary."

        allowed_keys = {"mandatory", "rename", "type"}
        for key in col.keys():
            if key not in allowed_keys:
                return f"columns[{idx}] contains invalid key '{key}'."

    return None


def validate_cfg(colcfg: Dict[str, Any]) -> Optional[str]:
    """Validate a dftidy configuration dictionary.

    Args:
        colcfg: A dictionary representing dftidy configuration.

    Returns:
        None if the configuration is valid, otherwise a string describing the error.

    Raises:
        TypeError: If colcfg is not a dictionary.
    """
    if not isinstance(colcfg, dict):
        return "colcfg must be a dictionary."

    if not colcfg:
        return "Configuration dictionary must not be empty."

    # include-unmatched-columns
    if "include-unmatched-columns" in colcfg:
        value = colcfg.get("include-unmatched-columns")
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            return None
        return "include-unmatched-columns must be blank or a boolean."


    # remove
    if "remove" in colcfg:
        val = colcfg.get("remove")
        if not isinstance(val, list):
            return "remove must be a list of strings."
        if not all(isinstance(item, str) for item in val):
            return "remove must contain only strings."

    # columns
    if "columns" in colcfg:
        error = _validate_columns(colcfg["columns"])
        if error:
            return error

    return None
