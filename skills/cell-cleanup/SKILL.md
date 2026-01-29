# Cell Cleanup — Delete Unneeded Cells

## When to Delete a Cell

Use `delete_cell(cell_index)` when a cell is no longer needed:

- **Superseded cells** — an earlier exploratory cell that was replaced by a better version
- **Debugging cells** — temporary `print()` or inspection cells used during development
- **Failed experiments** — code paths that were tried and abandoned
- **Duplicate cells** — accidentally created copies
- **Empty cells** — cells with no content

## When NOT to Delete

- **Cells with useful output** — even if the code is simple, the output may be valuable
- **Cells the user wrote** — check `diff_notebook()` first; don't delete user-authored cells without asking
- **Setup cells** — imports, config, and data loading cells are needed even if they look trivial

## Procedure

1. Before deleting, confirm the cell is truly unneeded by reading its source and output.
2. Call `delete_cell(cell_index)`.
3. Note: all cell indices after the deleted cell shift down by one. Account for this when deleting multiple cells — delete from highest index to lowest to avoid shifting issues.

## Deleting Multiple Cells

When cleaning up several cells at once, always delete in **reverse index order**:

```
# Wrong — indices shift after each delete
delete_cell(3)  # deletes cell 3
delete_cell(5)  # now this deletes what was cell 6!

# Correct — delete from bottom to top
delete_cell(5)  # deletes cell 5
delete_cell(3)  # indices below 5 are unchanged, deletes cell 3
```
