# Code Extraction — Reusable Modules in `src/`

## When to Extract

Activate this skill when ANY of these conditions are met:

- **Reuse detected** — the same function, class, or utility appears in 2+ notebooks
- **Long cells** — a single code cell exceeds ~50 lines of non-trivial logic
- **Long notebooks** — the notebook exceeds ~30 code cells or the total code is hard to follow
- **General-purpose utility** — a function is clearly not specific to the current analysis (e.g., data loaders, plotting helpers, preprocessing pipelines)
- **Agent judgment** — the code would benefit other notebooks or future work

## `src/` Directory Structure

Organize extracted code by domain. Each module should have a clear, descriptive name.

```
src/
├── __init__.py              # Makes src a package
├── data/
│   ├── __init__.py
│   ├── loaders.py           # Data loading functions
│   ├── transforms.py        # Data cleaning / preprocessing
│   └── validation.py        # Schema checks, data quality
├── models/
│   ├── __init__.py
│   ├── training.py          # Model training utilities
│   └── evaluation.py        # Metrics, scoring, comparison
├── viz/
│   ├── __init__.py
│   ├── plots.py             # Reusable plot functions
│   └── styles.py            # Plot themes, color palettes
└── utils/
    ├── __init__.py
    ├── io.py                # File I/O helpers
    ├── math.py              # Numerical utilities
    └── text.py              # String / text processing
```

Only create subdirectories and files as needed — don't scaffold empty modules.

## Extraction Procedure

1. **Identify the candidate** — a function or class that is reusable.
2. **Choose the right module** — pick the `src/` submodule that fits (create if needed).
3. **Write the module file** — move the function to `src/<domain>/<module>.py` with:
   - A module-level docstring explaining what this module provides
   - Type hints on all function signatures
   - A brief docstring per function
   - No notebook-specific state (no globals, no hardcoded paths)
4. **Add `__init__.py` exports** — re-export key names for easy imports:
   ```python
   # src/data/__init__.py
   from .loaders import load_csv, load_parquet
   ```
5. **Update the notebook cell** — replace the inline code with an import:
   ```python
   # Before (inline, 40 lines)
   def load_and_clean(path): ...

   # After (1 line)
   from src.data.loaders import load_and_clean
   ```
   Use `edit_and_run_cell` to update the cell in-place and verify the import works.
6. **Ensure `src/` is importable** — if the notebook's working directory doesn't include `src/`, add a sys.path cell at the top of the notebook:
   ```python
   import sys
   sys.path.insert(0, "/path/to/project")
   ```
   Or better, ensure the Jupyter server is started from the project root.

## Naming Conventions

- **Module names**: lowercase, snake_case, descriptive (`loaders.py` not `utils2.py`)
- **Function names**: verb_noun pattern (`load_csv`, `plot_distribution`, `compute_metrics`)
- **Class names**: PascalCase (`DataPipeline`, `ModelEvaluator`)
- **No catch-all modules**: avoid `helpers.py`, `misc.py`, `common.py` — be specific

## What NOT to Extract

- **One-off analysis code** — code specific to a single notebook's dataset or question
- **Notebook narrative** — exploratory code that tells a story (keep inline)
- **Trivial code** — a 3-line function used once doesn't need extraction
- **Configuration** — keep experiment configs, hyperparameters, and paths in the notebook

## Refactoring a Long Notebook

When a notebook is too long (>30 code cells or hard to follow):

1. Read the full notebook with `read_notebook(mode="full")`.
2. Identify clusters of related functions that could form a module.
3. Extract each cluster into the appropriate `src/` module.
4. Replace inline code with imports using `edit_and_run_cell`.
5. Delete any cells that are now empty or only had the extracted code using `delete_cell`.
6. The notebook should read as high-level steps with clear imports, not walls of implementation.

## Telling the User

After extracting code, inform the user:
- What was extracted and where it lives
- How to import it in other notebooks: `from src.data.loaders import load_csv`
- That the `src/` modules can be used outside notebooks too (scripts, tests, etc.)
