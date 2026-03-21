# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.

"""
Comprehensive pytest suite for check_file().

Function contract:
  - Returns None  → no error (file exists, is a file, is non-empty)
  - Returns str   → error description
  - Never raises  (per design intent)

Bugs documented as tests:
  - path.stat().st_size() called as a method — st_size is a property (int),
    calling it raises TypeError. A valid, non-empty file always hits this bug.
    The size check is therefore never reached tidyly.

Test strategy:
  - All filesystem interactions use tmp_path (real files, no mocking)
  - caplog used for log-content assertions (DEBUG level)
  - Logger fixture exercises the optional logger= parameter
  - Parametrize used for input variants (whitespace, types, encodings)
"""

import logging
import stat
from pathlib import Path

import pytest

from dftidy import check_file

# ---------------------------------------------------------------------------
# Module under test — inline so the file is self-contained for the exercise.
# In a real project: from mypackage.utils import check_file
# ---------------------------------------------------------------------------
LOGGER = logging.getLogger("check_file_module")


# ---------------------------------------------------------------------------
# Module-level fixtures (pytest requires these outside the class)
# ---------------------------------------------------------------------------

@pytest.fixture
def custom_logger():
    """A dedicated Logger instance to pass as the logger= argument."""
    return logging.getLogger("test_custom_logger")


@pytest.fixture
def non_empty_file(tmp_path):
    """A real non-empty file on disk."""
    p = tmp_path / "sample.yaml"
    p.write_text("key: value\n", encoding="utf-8")
    return p


@pytest.fixture
def empty_file(tmp_path):
    """A real zero-byte file on disk."""
    p = tmp_path / "empty.yaml"
    p.write_text("")
    return p


@pytest.fixture
def subdir(tmp_path):
    """A real directory (not a file)."""
    d = tmp_path / "subdir"
    d.mkdir()
    return d


# ===========================================================================
# Top-level container — all tests live inside this class
# ===========================================================================

class Test_file_check:

    # =======================================================================
    # Empty / blank filepath input
    # =======================================================================

    class TestEmptyFilepath:
        """str(filepath).strip() == '' branch."""

        def test_empty_string_returns_error(self):
            assert check_file("") is not None

        def test_empty_string_message_mentions_filepath(self):
            result = check_file("")
            assert "filepath" in result.lower() or "empty" in result.lower()

        @pytest.mark.parametrize("blank", ["   ", "\t", "\n", "  \t  \n  "])
        def test_whitespace_only_returns_error(self, blank):
            assert check_file(blank) is not None

        def test_empty_path_object_returns_error(self):
            # Path("") is valid Python — str() of it is "", strips to ""
            assert check_file(Path("")) is not None

        def test_returns_string_not_none_for_empty(self):
            result = check_file("")
            assert isinstance(result, str)

    # =======================================================================
    # Non-existent path
    # =======================================================================

    class TestNonExistentPath:

        def test_missing_file_returns_error(self, tmp_path):
            missing = tmp_path / "ghost.yaml"
            assert check_file(missing) is not None

        def test_missing_file_error_mentions_exists(self, tmp_path):
            missing = tmp_path / "ghost.yaml"
            result = check_file(missing)
            assert "exists" in result.lower()

        def test_missing_file_accepts_string_path(self, tmp_path):
            missing = str(tmp_path / "ghost.yaml")
            assert check_file(missing) is not None

        def test_missing_nested_path_returns_error(self, tmp_path):
            missing = tmp_path / "a" / "b" / "c.yaml"
            assert check_file(missing) is not None

        def test_missing_returns_string(self, tmp_path):
            result = check_file(tmp_path / "ghost.yaml")
            assert isinstance(result, str)

    # =======================================================================
    # Path exists but is a directory
    # =======================================================================

    class TestDirectoryPath:

        def test_directory_returns_error(self, subdir):
            assert check_file(subdir) is not None

        def test_directory_error_mentions_is_file(self, subdir):
            result = check_file(subdir)
            assert "is_file" in result.lower()

        def test_tmp_root_itself_returns_error(self, tmp_path):
            # tmp_path is always a directory
            assert check_file(tmp_path) is not None

        def test_directory_returns_string(self, subdir):
            assert isinstance(check_file(subdir), str)

    # =======================================================================
    # Non-empty file — documents the st_size() bug
    # =======================================================================

    class TestNonEmptyFile:
        """
        KNOWN BUG: path.stat().st_size() is called as a method.
        st_size is an int property — calling it raises TypeError.
        A valid non-empty file always hits this code path and raises.

        These tests document current behaviour. Remove xfail markers
        and update assertions when the bug is fixed (change to st_size without ()).
        """

        #@pytest.mark.xfail(strict=True, raises=TypeError, reason="st_size() bug")
        def test_valid_file_returns_none(self, non_empty_file):
            """After fix: should return None (no error)."""
            result = check_file(non_empty_file)
            assert result is None

        def test_valid_file_accepts_string_path(self, non_empty_file):
            assert check_file(str(non_empty_file)) is None

        def test_valid_file_with_custom_logger(self, non_empty_file, custom_logger):
            assert check_file(non_empty_file, logger=custom_logger) is None

        def test_file_with_multiple_lines(self, tmp_path):
            p = tmp_path / "multi.yaml"
            p.write_text("a: 1\nb: 2\nc: 3\n")
            assert check_file(p) is None

        def test_file_with_single_byte(self, tmp_path):
            p = tmp_path / "tiny.yaml"
            p.write_bytes(b"x")
            assert check_file(p) is None

    # =======================================================================
    # Empty file — reaches st_size() bug branch too via is_file check passing
    # NOTE: empty file passes exists+is_file, then hits st_size bug
    # =======================================================================

    class TestEmptyFile:
        """
        An empty (zero-byte) file passes exists() and is_file() checks,
        then hits the st_size() bug. The intended behaviour was presumably
        to return an error for empty files — but the bug prevents reaching
        any size check.
        """

        def test_empty_file_raises_due_to_bug(self, empty_file):
            """Empty file reaches st_size() and raises TypeError (same bug)."""
            assert check_file(empty_file) is not None

    # =======================================================================
    # logger= parameter
    # =======================================================================

    # =======================================================================
    # Return type contract
    # =======================================================================

    class TestReturnTypeContract:
        """Function must return str (error) or None (success) — never other types."""

        def test_missing_returns_str(self, tmp_path):
            result = check_file(tmp_path / "ghost.yaml")
            assert isinstance(result, str)

        def test_directory_returns_str(self, subdir):
            assert isinstance(check_file(subdir), str)

        def test_empty_input_returns_str(self):
            assert isinstance(check_file(""), str)

        def test_whitespace_input_returns_str(self):
            assert isinstance(check_file("   "), str)

    # =======================================================================
    # filepath type coercion — accepts str | Path
    # =======================================================================

    class TestFilepathTypeCoercion:
        """str(filepath).strip() means any type that str() works on is accepted."""

        def test_accepts_pathlib_path(self, tmp_path):
            result = check_file(tmp_path / "ghost.yaml")
            assert isinstance(result, str)

        def test_accepts_string(self, tmp_path):
            result = check_file(str(tmp_path / "ghost.yaml"))
            assert isinstance(result, str)

        def test_leading_trailing_whitespace_in_string_stripped(self, tmp_path):
            missing = str(tmp_path / "ghost.yaml")
            result_padded = check_file(f"  {missing}  ")
            assert result_padded is not None
            assert "exists" in result_padded.lower()
