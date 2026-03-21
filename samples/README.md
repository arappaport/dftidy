# dftidy-demo

Minimal Poetry project demonstrating `arappaport/dftidy`.

## Setup

```bash
poetry install
```

## Run

```bash
poetry run python run_dftidy.py
```

Or with a custom CSV:
```bash
cp /your/path/data_tidied_expected.csv .
poetry run python -m dftidy_demo.main
```

## Notes

- `dftidy` is installed directly from GitHub (not on PyPI under this name).
- `dftidy.tidy()` is not in the exported public API; this project uses
  `tidy()` which is the documented entrypoint for the tidy(). See `dftidy_demo/run_dftidy.py`.
