# Error Handling — Edit-in-Place

## Rule: ALWAYS edit the existing cell. NEVER create a new cell to fix errors.

When code execution fails, the tool response includes the `cell_index` of the failed cell. Use this to fix the error in-place.

## Procedure

1. **Read the error message** — understand what went wrong.
2. **Call `edit_and_run_cell(cell_index=<failed_index>, new_source=<fixed_code>)`** — this edits the cell AND re-executes it in one step.
3. **If it fails again**, analyze the new error and call `edit_and_run_cell` again on the SAME cell.
4. **After 3 failures**, reconsider:
   - Is a dependency missing? → `install_package()`
   - Is the kernel state stale? → `restart_kernel()` + re-run setup
   - Is the approach wrong? → Rewrite with a fundamentally different approach

## Examples

### Import Error
```
# execute_cell returns: ModuleNotFoundError: No module named 'seaborn' (cell 3)
→ install_package("seaborn")
→ edit_and_run_cell(cell_index=3, new_source="import seaborn as sns\n...")
```

### Name Error
```
# execute_cell returns: NameError: name 'df' is not defined (cell 5)
→ Check if earlier cells need re-running
→ edit_and_run_cell(cell_index=5, new_source=<fixed code that defines or imports df>)
```

### Syntax Error
```
# execute_cell returns: SyntaxError: invalid syntax (cell 7)
→ edit_and_run_cell(cell_index=7, new_source=<corrected syntax>)
```

## Anti-Patterns (NEVER do these)

- Creating cell 8 to fix an error in cell 7
- Adding a "fix" cell below the broken cell
- Leaving broken cells in the notebook and working around them
- Creating duplicate cells with slightly different code
