# dftidy

[![CI](https://github.com/yourorg/dftidy/actions/workflows/ci.yml/badge.svg)](https://github.com/yourorg/dftidy/actions)
[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](UNLICENSE)
[![Coverage](https://img.shields.io/badge/coverage-≅82%25-brightgreen)](htmlcov/index.html)
[![PyPI](https://img.shields.io/pypi/v/dftidy)](https://pypi.org/project/dftidy/)

---

## Overview

`dftidy` is a simple set of utilities to prepare and tidy a pandas DataFrame.   
I tend to do the same things for every DateFrame - this DRY's up the processing. 

dftidy.tidy() is driven from an external configuration file.    See ./samples/config_sample.yaml for notes and example. 

It supports: 
 * Verify mandatory columns
 * Type conversions. Convert datetimes to strings: 8601 or other common dateformats, floats to int/
 * Renaming columns
 * Removing columns early in processing - example - remove any PI columns
 

### Pandas built-in type conversion
* https://pandas.pydata.org/docs/user_guide/io.html#csv-text-files


## Prerequisites

| Tool       | Min version | Install                          |
|------------|-------------|----------------------------------|
| Python     | 3.11        | [python.org](https://python.org) |
| Poetry     | 1.8         | `pip install poetry`             |
| Nox        | 2024.3      | `pipx install nox`               |
| pre-commit | 3.7         | `pipx install pre-commit`        |

> **Recommended:** install Nox and pre-commit via
> [pipx](https://pipx.pypa.io) so they are globally available without
> polluting any project venv.

---

## Installation

```bash
git clone https://github.com/arappaport/dftidy.git
cd dftidy

# Install runtime + all dev dependencies (includes click for the CLI)
poetry install --with dev

# Activate the managed virtualenv
poetry shell

# Install git hooks so ruff runs automatically on every commit
pre-commit install
```

> **Library-only install** (no CLI, no click):
> ```bash
> pip install dftidy
> ```
> Only `pandas` is required. `click` is never installed.

---

## CLI usage

The `dftidy` command is available after `poetry install --with dev`.

### Help

```bash
dftidy --help
dftidy stats    --help
dftidy pipeline --help
```

### `stats` — descriptive statistics from a CSV file

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--column` | `-c` | all numeric cols | Column to analyse |
| `--output` | `-o` | `pretty` | `pretty` or `json` |

```bash
# All numeric columns, pretty output
dftidy stats data.csv

# Single column
dftidy stats data.csv -c price

# JSON output (pipe-friendly)
dftidy stats data.csv -c price -o json
```

**Example pretty output:**

```
── value ──
  mean    : 30.0000
  median  : 30.0000
  std     : 15.8114
  min     : 10.0000
  max     : 50.0000
  count   : 5.0000
```

**Example JSON output:**

```json
{
  "value": {
    "mean": 30.0,
    "median": 30.0,
    "std": 15.811388300841896,
    "min": 10.0,
    "max": 50.0,
    "count": 5.0
  }
}
```

### `pipeline` — normalise → filter → stats

| Flag | Short | Required | Description |
|------|-------|----------|-------------|
| `--column` | `-c` | ✓ | Numeric column to process |
| `--output` | `-o` | — | `pretty` or `json` |

```bash
dftidy pipeline data.csv -c price
dftidy pipeline data.csv -c price -o json
```

**What the pipeline does:**

1. Min-max normalises `--column` to [0, 1].
2. Retains only rows where the normalised value is strictly above the mean.
3. Returns descriptive stats on the retained subset.

### Quick demo

```bash
printf 'value,label\n10,a\n20,b\n30,c\n40,d\n50,e\n' > /tmp/demo.csv

dftidy stats    /tmp/demo.csv
dftidy pipeline /tmp/demo.csv -c value -o json
```

---

## Running tests

### Full suite with coverage report

```bash
poetry run pytest
```

The run fails if branch coverage drops below **82%**.

### Useful flags

| Command | Purpose |
|---------|---------|
| `pytest -v` | Verbose test names |
| `pytest tests/test_transform.py -v` | Single file |
| `pytest -k "zero_variance"` | Keyword filter |
| `pytest -s` | Show stdout (debug) |
| `pytest --tb=long` | Full tracebacks |
| `pytest --cov-report=html` | Write HTML report to `htmlcov/` |

```bash
# Open HTML coverage report
poetry run pytest --cov-report=html && open htmlcov/index.html
```

---

## Nox sessions

```bash
nox -l           # list all available sessions
nox              # run defaults: lint, typecheck, tests-3.13
nox -s <name>    # run one specific session
```

| Session | Description |
|---------|-------------|
| `lint` | ruff lint + format check (read-only; safe for CI) |
| `format` | ruff auto-format + fix violations in-place |
| `typecheck` | mypy `--strict` over `dftidy/` |
| `tests-3.11` | pytest + coverage on Python 3.11 |
| `tests-3.12` | pytest + coverage on Python 3.12 |
| `tests-3.13` | pytest + coverage on Python 3.13 |
| `safety` | pip-audit CVE scan on runtime deps only |
| `ci` | lint + typecheck + tests-3.13 (fast PR gate) |

### Passing extra arguments to pytest

```bash
# Run one test file verbosely
nox -s tests-3.13 -- tests/test_transform.py -v

# Filter by test name
nox -s tests-3.13 -- -k "zero_variance" -v
```

### Full Python version matrix

```bash
nox -s tests     # runs 3.11, 3.12, 3.13 sequentially
```


---

## Library API

The library requires only `pandas`. `click` is never imported.

```python
import pandas as pd

from dftidy import (
    describe_dataframe,
    normalise_column,
    summary_stats,
    tidy,
    validate_cfg
)
from dftidy.main import run_pipeline

df = pd.DataFrame({"price": [10, 20, 30, 40, 50], "qty": [1, 2, 3, 4, 5]})

# Individual functions
print(summary_stats(df, "price"))
# {'mean': 30.0, 'median': 30.0, 'std': 15.81, 'min': 10.0, 'max': 50.0, 'count': 5.0}

print(describe_dataframe(df))
# {'price': {...}, 'qty': {...}}

normalised = normalise_column(df, "price")  # returns new DataFrame

# Full pipeline in one call
result = run_pipeline(df, "price")
print(result["stats"])  # nested dict of stats on the filtered subset
```

---

## Contributing

1. Fork and clone the repository.
2. Run `poetry install --with dev && pre-commit install`.
3. Create a feature branch: `git checkout -b feat/your-feature`.
4. Write tests first — ensure `nox -s ci` passes before opening a PR.
5. Add an entry under `[Unreleased]` in `CHANGELOG.md`.
6. Open a pull request against `main`.

---

## License

[MIT](UNLICENSE)


##TODO's
1. X - evaluate if normalize and stats are needed.  NO Dry it up. Also remove pipeline.  Keep tidy and validate_cfg only
2.  X Add links for default read_csv behavior in README
3. Add a sample run.py to samples.    load, validate, print
3. Decide on type's behavior. KISS.  SHould it convert strings to int? Should type convert floats to int.
5. Decision on load_cfg.   The file check is useful.  But the load is not single purpose.
   *   move to util.  check_file.     include OS full path. 
   * NO exceptions.   return useful error string.   Take logger. 