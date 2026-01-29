# Research Methodology

## Notebook Structure

Every research notebook should follow this structure:

1. **Title + Objective** (markdown) — What question are we answering?
2. **Setup** (code) — Imports, configuration, data loading
3. **Data Exploration** (code + markdown) — Shape, dtypes, head, describe, missing values
4. **Analysis** (code + markdown) — Core computation, iterative refinement
5. **Visualization** (code) — Plots that reveal patterns
6. **Conclusions** (markdown) — Key findings, next steps

## Principles

### Start Simple, Build Up
- First cell: minimal working version
- Add complexity only after the simple version works
- Test assumptions at each step

### Data First
- Always inspect data before computing on it
- Check shapes, types, nulls, distributions
- Print intermediate results to verify correctness

### Reproducibility
- Import all dependencies at the top
- Set random seeds where applicable
- Document data sources

### Visualization Best Practices
- Label axes and add titles
- Use appropriate chart types (don't use pie charts)
- Include units where applicable
- Use `plt.tight_layout()` for clean rendering

## Section Headers

Use markdown cells as section dividers:
```markdown
## 1. Data Loading
## 2. Exploratory Analysis
## 3. Feature Engineering
## 4. Model Training
## 5. Results
```
