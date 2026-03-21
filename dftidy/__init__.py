# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.

"""dftidy public API.
"""

from __future__ import annotations

from dftidy.tidy import tidy
from dftidy.process_removes import process_removes
from dftidy.validate_cfg import validate_cfg
from dftidy.util import check_file

__version__ = "0.1.2"

__all__ = [
    "__version__",
    "tidy",
    "process_removes",
    "validate_cfg"
]
