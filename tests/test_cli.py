# SPDX-License-Identifier: Unlicense
# This is free and unencumbered software released into the public domain.
# See UNLICENSE or <https://unlicense.org> for details.

"""Integration tests for the Click CLI.

CliRunner invokes commands in-process — no subprocess overhead.
catch_exceptions=False lets pytest surface real tracebacks on unexpected
errors instead of silently capturing them in result.exception.
CliRunner is instantiated with defaults only (no mix_stderr override).
"""

from __future__ import annotations

import json
import re

import pytest
from click.testing import CliRunner

from dftidy.cli import main


@pytest.fixture()
def runner() -> CliRunner:
    """CliRunner with default settings."""
    return CliRunner()


class TestMainGroup:
    """Top-level CLI group: help text and version format."""

    def test_help_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"], catch_exceptions=False)
        assert result.exit_code == 0

    def test_version_is_semver(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--version"], catch_exceptions=False)
        assert result.exit_code == 0
        assert re.search(r"\d+\.\d+\.\d+", result.output), (
            f"Version output did not contain a semver string: {result.output!r}"
        )

