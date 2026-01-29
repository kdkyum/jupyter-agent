"""Notebook diff/snapshot tracking for detecting user changes."""

import copy
import hashlib
import json


class NotebookTracker:
    """Tracks notebook state and detects changes between snapshots."""

    def __init__(self):
        self._snapshot: dict | None = None
        self._snapshot_hash: str | None = None

    def take_snapshot(self, notebook_content: dict) -> str:
        """Save a baseline snapshot. Returns hash of the snapshot."""
        self._snapshot = copy.deepcopy(notebook_content)
        self._snapshot_hash = self._hash_notebook(notebook_content)
        return self._snapshot_hash

    def has_snapshot(self) -> bool:
        return self._snapshot is not None

    def diff(self, current_content: dict) -> dict:
        """Compare current notebook against saved snapshot.

        Returns a dict with:
          - changed: bool
          - summary: str
          - added_cells: list of cell indices added
          - removed_cells: list of cell indices removed
          - modified_cells: list of cell indices with changed source
          - current_hash: str
          - snapshot_hash: str
        """
        current_hash = self._hash_notebook(current_content)

        if self._snapshot is None:
            return {
                "changed": False,
                "summary": "No snapshot taken yet. Use snapshot_notebook first.",
                "added_cells": [],
                "removed_cells": [],
                "modified_cells": [],
                "current_hash": current_hash,
                "snapshot_hash": None,
            }

        if current_hash == self._snapshot_hash:
            return {
                "changed": False,
                "summary": "No changes detected since last snapshot.",
                "added_cells": [],
                "removed_cells": [],
                "modified_cells": [],
                "current_hash": current_hash,
                "snapshot_hash": self._snapshot_hash,
            }

        snap_cells = self._snapshot.get("cells", [])
        curr_cells = current_content.get("cells", [])

        snap_sources = [self._cell_source(c) for c in snap_cells]
        curr_sources = [self._cell_source(c) for c in curr_cells]

        # Match cells by ID first, then by position
        snap_ids = {c.get("id", i): i for i, c in enumerate(snap_cells)}
        curr_ids = {c.get("id", i): i for i, c in enumerate(curr_cells)}

        added = []
        removed = []
        modified = []

        # Check for removed cells (in snapshot but not in current)
        for cell_id, snap_idx in snap_ids.items():
            if cell_id not in curr_ids:
                removed.append(snap_idx)

        # Check for added/modified cells
        for cell_id, curr_idx in curr_ids.items():
            if cell_id not in snap_ids:
                added.append(curr_idx)
            else:
                snap_idx = snap_ids[cell_id]
                if snap_sources[snap_idx] != curr_sources[curr_idx]:
                    modified.append(curr_idx)

        parts = []
        if added:
            parts.append(f"{len(added)} cell(s) added (indices: {added})")
        if removed:
            parts.append(f"{len(removed)} cell(s) removed (snapshot indices: {removed})")
        if modified:
            parts.append(f"{len(modified)} cell(s) modified (indices: {modified})")

        summary = "; ".join(parts) if parts else "Metadata changes only."

        return {
            "changed": True,
            "summary": summary,
            "added_cells": added,
            "removed_cells": removed,
            "modified_cells": modified,
            "current_hash": current_hash,
            "snapshot_hash": self._snapshot_hash,
        }

    @staticmethod
    def _cell_source(cell: dict) -> str:
        source = cell.get("source", "")
        if isinstance(source, list):
            return "".join(source)
        return source

    @staticmethod
    def _hash_notebook(nb: dict) -> str:
        cells = nb.get("cells", [])
        cell_data = []
        for c in cells:
            source = c.get("source", "")
            if isinstance(source, list):
                source = "".join(source)
            cell_data.append({
                "type": c.get("cell_type", "code"),
                "source": source,
                "id": c.get("id", ""),
            })
        return hashlib.sha256(json.dumps(cell_data, sort_keys=True).encode()).hexdigest()[:16]
