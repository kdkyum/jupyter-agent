# Notebook Conventions

## Cell Organization

- **One logical step per cell** — don't cram multiple operations into one cell
- **Markdown before code** — explain what the next cell does
- **Keep cells short** — prefer 5–20 lines per code cell
- **Imports in a single cell** at the top of the notebook

## Code Style

- Use descriptive variable names (`customer_df` not `df2`)
- Add inline comments for non-obvious operations
- Use f-strings for print statements
- Prefer pandas operations over loops where possible

## Output Management

- Use `print()` for important intermediate results
- Display dataframes with `.head()` or `.sample()` — never dump entire large frames
- For plots: one figure per cell, call `plt.show()` explicitly
- Suppress noisy output with semicolons: `result = computation();`

## Error Prevention

- Check data shapes after transforms: `print(f"Shape: {df.shape}")`
- Use `.info()` and `.describe()` before analysis
- Validate joins: check row counts before and after
- Guard against missing data: check `.isna().sum()` early

## Collaboration Notes

- The user can see and edit the notebook in real-time in their browser
- Don't modify cells the user is actively editing
- Use `diff_notebook()` before major changes to check for user edits
- Take snapshots (`snapshot_notebook()`) at natural breakpoints
