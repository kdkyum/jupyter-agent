# Notebook Finalize — Table of Contents

## When to Finalize

After all notebook editing is complete — analysis done, errors fixed, cells cleaned up — create a Table of Contents at the top of the notebook.

## Procedure

1. Read the full notebook with `read_notebook(mode="full")`.
2. Scan all markdown cells for headers (`#`, `##`, `###`).
3. Build a TOC as a markdown cell with linked entries.
4. Insert the TOC at position 0 using `add_cell(source, "markdown", position=0)`.
5. If a TOC cell already exists (first cell starts with `# Table of Contents`), update it with `edit_cell(0, new_source)` instead of adding a new one.

## TOC Format

```markdown
# Table of Contents

1. [Section Title](#section-title)
   1. [Subsection](#subsection)
2. [Another Section](#another-section)
   1. [Details](#details)
```

## Rules

- Only include `##` and `###` level headers in the TOC (skip the notebook title `#` if present).
- Use numbered lists for top-level sections, nested numbered lists for subsections.
- Generate anchors by lowercasing the header text and replacing spaces with hyphens.
- Strip any leading/trailing whitespace from header text.
- If the notebook has fewer than 3 sections, skip the TOC — it's not worth it.

## Example

Given these markdown cells in the notebook:
```
Cell 0: # My Analysis
Cell 2: ## 1. Data Loading
Cell 5: ## 2. Exploratory Analysis
Cell 8: ### 2.1 Missing Values
Cell 10: ### 2.2 Distributions
Cell 14: ## 3. Modeling
Cell 20: ## 4. Results
```

Generate:
```markdown
# Table of Contents

1. [Data Loading](#1-data-loading)
2. [Exploratory Analysis](#2-exploratory-analysis)
   1. [Missing Values](#21-missing-values)
   2. [Distributions](#22-distributions)
3. [Modeling](#3-modeling)
4. [Results](#4-results)
```
