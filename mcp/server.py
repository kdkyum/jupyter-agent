"""MCP server providing Jupyter notebook tools for Claude Code."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Sibling imports resolved in _init_imports() at startup
JupyterClient = None
NotebookTracker = None

# ── State ────────────────────────────────────────────────────────

_client = None  # JupyterClient instance
_notebook_path: str | None = None
_kernel_id: str | None = None
_kernel_name: str | None = None
_venv_path: str | None = None
_tracker = None  # NotebookTracker instance

SESSION_FILE = Path.home() / ".jupyter-agent-session.json"

mcp = FastMCP(
    "jupyter-agent",
    description="Jupyter notebook tools — connect, execute, edit, and manage notebooks",
)


def _save_session():
    """Persist session info for reconnection."""
    data = {
        "server_url": _client.server_url if _client else None,
        "token": _client.token if _client else None,
        "notebook_path": _notebook_path,
        "kernel_id": _kernel_id,
        "kernel_name": _kernel_name,
        "venv_path": _venv_path,
    }
    SESSION_FILE.write_text(json.dumps(data))


def _load_session() -> dict | None:
    """Load saved session info."""
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return None


def _require_notebook() -> str | None:
    """Return an error message if no notebook is open, else None."""
    if not _client or not _notebook_path:
        return "No notebook open. Use connect() or create_notebook() first."
    return None


def _require_kernel() -> str | None:
    """Return an error message if no kernel is available, else None."""
    if not _client or not _kernel_id:
        return "No kernel available. Use connect() or create_notebook() first."
    return None


def _format_outputs(outputs: list) -> str:
    """Format cell outputs into readable text. Strips ANSI codes."""
    parts = []
    for out in outputs:
        otype = out.get("output_type", "")
        if otype == "stream":
            text = out.get("text", "")
            parts.append(text)
        elif otype in ("execute_result", "display_data"):
            data = out.get("data", {})
            if "text/plain" in data:
                parts.append(data["text/plain"])
            elif "text/html" in data:
                parts.append("[HTML output]")
            elif "image/png" in data:
                parts.append("[Image output (PNG)]")
            else:
                parts.append(f"[{otype}: {list(data.keys())}]")
        elif otype == "error":
            ename = out.get("ename", "Error")
            evalue = out.get("evalue", "")
            tb = out.get("traceback", [])
            tb_text = "\n".join(tb) if isinstance(tb, list) else str(tb)
            parts.append(f"{ename}: {evalue}\n{tb_text}")
    text = "\n".join(parts)
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def _format_execution_result(result: dict, cell_index: int) -> str:
    """Format execution result dict into a user-facing message."""
    output_text = _format_outputs(result["outputs"])

    if result["status"] == "ok":
        msg = f"Executed successfully (cell {cell_index})."
        if output_text.strip():
            msg += f"\n\nOutput:\n{output_text.strip()}"
        return msg

    err = result.get("error", {})
    msg = f"Execution error in cell {cell_index}.\n\n"
    msg += f"{err.get('ename', 'Error')}: {err.get('evalue', '')}\n"
    if err.get("traceback"):
        msg += f"\nTraceback:\n{err['traceback']}"
    msg += f"\n\nUse edit_and_run_cell(cell_index={cell_index}, new_source=...) to fix this cell."
    return msg


# ── Connection ───────────────────────────────────────────────────

@mcp.tool()
async def connect(server_url: str, token: str, notebook_path: str = "", kernel_name: str = "") -> str:
    """Connect to an existing Jupyter server.

    Args:
        server_url: The URL of the Jupyter server (e.g. http://localhost:8888)
        token: Authentication token for the Jupyter server
        notebook_path: Optional path to a notebook to open (e.g. "work/analysis.ipynb")
        kernel_name: Kernel to use for new sessions (defaults to kernel set by setup_kernel, or "python3")
    """
    global _client, _notebook_path, _kernel_id

    _client = JupyterClient(server_url, token)

    try:
        await _client.check_connection()
    except Exception as e:
        _client = None
        return f"Failed to connect: {e}"

    result_parts = [f"Connected to Jupyter server at {server_url}"]

    kname = kernel_name or _kernel_name or "python3"

    if notebook_path:
        _notebook_path = notebook_path
        try:
            session = await _client.get_session_for_notebook(notebook_path)
            if session:
                _kernel_id = session["kernel"]["id"]
                result_parts.append(f"Found existing session for {notebook_path} (kernel: {_kernel_id[:8]}...)")
            else:
                session = await _client.create_session(notebook_path, kernel_name=kname)
                _kernel_id = session["kernel"]["id"]
                result_parts.append(f"Created session for {notebook_path} (kernel: {kname}, {_kernel_id[:8]}...)")
        except Exception as e:
            result_parts.append(f"Note: could not open notebook '{notebook_path}': {e}")
            result_parts.append("Use create_notebook to create a new one, or connect with a valid path.")

    _save_session()
    return "\n".join(result_parts)


# ── Kernel Setup ─────────────────────────────────────────────────

@mcp.tool()
async def setup_kernel(venv_path: str, kernel_name: str = "") -> str:
    """Set up a Jupyter kernel from a .venv directory.

    Installs ipykernel into the venv and registers it as a Jupyter kernel.
    All subsequent notebook operations will use this kernel.

    Args:
        venv_path: Path to the .venv directory (e.g. "/path/to/project/.venv")
        kernel_name: Display name for the kernel (defaults to venv directory name)
    """
    global _venv_path, _kernel_name

    venv = Path(venv_path).resolve()
    if not venv.exists():
        return f"venv not found: {venv}. Create it first with: uv venv {venv}"

    python = venv / "bin" / "python"
    if not python.exists():
        return f"No python binary at {python}. Is this a valid venv?"

    if not kernel_name:
        kernel_name = venv.parent.name or "jupyter-agent"

    _venv_path = str(venv)
    _kernel_name = kernel_name

    # Install ipykernel into the venv
    uv = shutil.which("uv")
    if not uv:
        return "uv not found on PATH. Install it: https://docs.astral.sh/uv/"

    try:
        subprocess.run(
            [uv, "pip", "install", "ipykernel", "--python", str(python)],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        return f"Failed to install ipykernel: {e.stderr}"

    # Register the kernel
    try:
        subprocess.run(
            [str(python), "-m", "ipykernel", "install", "--user",
             f"--name={kernel_name}", f"--display-name={kernel_name}"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        return f"Failed to register kernel: {e.stderr}"

    _save_session()
    return (
        f"Kernel '{kernel_name}' set up from {venv}\n"
        f"ipykernel installed and registered.\n"
        f"Use create_notebook() or connect() — sessions will use this kernel."
    )


# ── Notebook Management ──────────────────────────────────────────

@mcp.tool()
async def create_notebook(path: str, title: str = "", kernel_name: str = "") -> str:
    """Create a new .ipynb notebook and start a kernel session for it.

    Args:
        path: Path for the new notebook (e.g. "research/experiment.ipynb")
        title: Optional title — added as a markdown cell at the top
        kernel_name: Kernel to use (defaults to kernel set by setup_kernel, or "python3")
    """
    global _notebook_path, _kernel_id

    if not _client:
        return "Not connected. Use connect() first."

    kname = kernel_name or _kernel_name or "python3"

    try:
        await _client.create_notebook(path, kernel_name=kname)
    except Exception as e:
        return f"Failed to create notebook: {e}"

    # Add title cell if provided
    if title:
        await _client.add_cell_to_notebook(path, f"# {title}", cell_type="markdown", position=0)

    # Create session (starts kernel)
    try:
        session = await _client.create_session(path, kernel_name=kname)
        _kernel_id = session["kernel"]["id"]
    except Exception as e:
        return f"Notebook created at {path} but failed to start kernel: {e}"

    _notebook_path = path
    _save_session()

    return f"Created notebook: {path}\nKernel: {kname} ({_kernel_id[:8]}...)\nReady for execution."


@mcp.tool()
async def read_notebook(mode: str = "full", last_n: int = 5) -> str:
    """Read the current notebook's state.

    Args:
        mode: "full" — all cells, "last_n" — last N cells, "summary" — cell count + types
        last_n: Number of recent cells to show when mode is "last_n"
    """
    if err := _require_notebook():
        return err

    try:
        nb_data = await _client.get_notebook(_notebook_path)
    except Exception as e:
        return f"Failed to read notebook: {e}"

    nb = nb_data["content"]
    cells = nb.get("cells", [])

    if mode == "summary":
        code_cells = sum(1 for c in cells if c["cell_type"] == "code")
        md_cells = sum(1 for c in cells if c["cell_type"] == "markdown")
        return (
            f"Notebook: {_notebook_path}\n"
            f"Total cells: {len(cells)} ({code_cells} code, {md_cells} markdown)\n"
            f"Kernel: {_kernel_id[:8] + '...' if _kernel_id else 'none'}"
        )

    if mode == "last_n":
        cells_to_show = cells[-last_n:] if len(cells) > last_n else cells
        start_idx = max(0, len(cells) - last_n)
    else:
        cells_to_show = cells
        start_idx = 0

    parts = [f"Notebook: {_notebook_path} ({len(cells)} cells)\n"]
    for i, cell in enumerate(cells_to_show):
        idx = start_idx + i
        ctype = cell["cell_type"]
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)

        parts.append(f"--- Cell {idx} [{ctype}] ---")
        parts.append(source)

        if ctype == "code" and cell.get("outputs"):
            output_text = _format_outputs(cell["outputs"])
            if output_text.strip():
                parts.append(f"[Output]: {output_text.strip()}")
        parts.append("")

    return "\n".join(parts)


@mcp.tool()
async def add_cell(source: str, cell_type: str = "code", position: int = -1) -> str:
    """Add a new cell to the notebook without executing it.

    Args:
        source: Cell content (code or markdown)
        cell_type: "code" or "markdown"
        position: Where to insert (-1 = end, 0 = beginning, etc.)
    """
    if err := _require_notebook():
        return err

    pos = None if position < 0 else position
    try:
        _, idx = await _client.add_cell_to_notebook(_notebook_path, source, cell_type, pos)
    except Exception as e:
        return f"Failed to add cell: {e}"

    return f"Added {cell_type} cell at index {idx}."


@mcp.tool()
async def edit_cell(cell_index: int, new_source: str) -> str:
    """Edit a cell's source code without executing it.

    Args:
        cell_index: Index of the cell to edit (0-based)
        new_source: New source code for the cell
    """
    if err := _require_notebook():
        return err

    try:
        await _client.edit_cell_source(_notebook_path, cell_index, new_source)
    except IndexError as e:
        return str(e)
    except Exception as e:
        return f"Failed to edit cell: {e}"

    return f"Cell {cell_index} updated."


@mcp.tool()
async def get_cell_output(cell_index: int) -> str:
    """Get the output of a specific cell.

    Args:
        cell_index: Index of the cell (0-based)
    """
    if err := _require_notebook():
        return err

    try:
        nb_data = await _client.get_notebook(_notebook_path)
    except Exception as e:
        return f"Failed to read notebook: {e}"

    cells = nb_data["content"].get("cells", [])
    if cell_index < 0 or cell_index >= len(cells):
        return f"Cell index {cell_index} out of range (0-{len(cells)-1})"

    cell = cells[cell_index]
    if cell["cell_type"] != "code":
        return f"Cell {cell_index} is a {cell['cell_type']} cell (no outputs)."

    outputs = cell.get("outputs", [])
    if not outputs:
        return f"Cell {cell_index} has no outputs."

    return f"Cell {cell_index} output:\n{_format_outputs(outputs)}"


# ── Execution ────────────────────────────────────────────────────

@mcp.tool()
async def execute_cell(
    code: str,
    timeout: int = 120,
    add_to_notebook: bool = True,
    cell_index: int = -1,
) -> str:
    """Execute code in the kernel.

    Args:
        code: Python code to execute
        timeout: Max execution time in seconds
        add_to_notebook: If True, add/update the code as a cell in the notebook
        cell_index: If >= 0 and add_to_notebook, execute in this existing cell. If -1, append new cell.
    """
    if err := _require_kernel():
        return err

    result = await _client.execute_code(_kernel_id, code, timeout)

    actual_index = -1

    if add_to_notebook and _notebook_path:
        try:
            if cell_index >= 0:
                # Execute in existing cell — update source and outputs
                await _client.edit_cell_source(_notebook_path, cell_index, code)
                await _client.update_cell_outputs(_notebook_path, cell_index, result["outputs"])
                actual_index = cell_index
            else:
                # Append new cell with outputs
                _, actual_index = await _client.add_cell_to_notebook(
                    _notebook_path, code, "code", outputs=result["outputs"]
                )
        except Exception:
            pass  # Non-critical -- code still executed

    return _format_execution_result(result, actual_index)


@mcp.tool()
async def edit_and_run_cell(cell_index: int, new_source: str, timeout: int = 120) -> str:
    """Edit a cell's source and execute it in one atomic operation.
    This is the PRIMARY tool for fixing errors — edit the broken cell in-place and re-run.

    Args:
        cell_index: Index of the cell to edit and execute (0-based)
        new_source: New source code for the cell
        timeout: Max execution time in seconds
    """
    if not _client or not _kernel_id or not _notebook_path:
        return "No notebook/kernel available. Use connect() or create_notebook() first."

    # Edit the cell
    try:
        await _client.edit_cell_source(_notebook_path, cell_index, new_source)
    except IndexError as e:
        return str(e)
    except Exception as e:
        return f"Failed to edit cell {cell_index}: {e}"

    # Execute the code
    result = await _client.execute_code(_kernel_id, new_source, timeout)

    # Update outputs in notebook
    try:
        await _client.update_cell_outputs(_notebook_path, cell_index, result["outputs"])
    except Exception:
        pass  # Non-critical

    return _format_execution_result(result, cell_index)


# ── Kernel Management ────────────────────────────────────────────

@mcp.tool()
async def restart_kernel() -> str:
    """Restart the kernel (clears all state, keeps notebook cells)."""
    if err := _require_kernel():
        return err

    try:
        await _client.restart_kernel(_kernel_id)
    except Exception as e:
        return f"Failed to restart kernel: {e}"

    return "Kernel restarted. All variables cleared. Re-run cells to restore state."


@mcp.tool()
async def interrupt_kernel() -> str:
    """Interrupt a running execution in the kernel."""
    if err := _require_kernel():
        return err

    try:
        await _client.interrupt_kernel(_kernel_id)
    except Exception as e:
        return f"Failed to interrupt kernel: {e}"

    return "Kernel interrupted."


@mcp.tool()
async def install_package(package: str) -> str:
    """Install a Python package into the kernel's venv using uv pip install.

    Args:
        package: Package name (e.g. "pandas", "numpy>=1.21")
    """
    if err := _require_kernel():
        return err

    uv = shutil.which("uv")
    if not uv:
        return "uv not found on PATH. Install it: https://docs.astral.sh/uv/"

    # Install into the kernel's venv via uv
    cmd = [uv, "pip", "install", package]
    if _venv_path:
        python = str(Path(_venv_path) / "bin" / "python")
        cmd.extend(["--python", python])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        msg = f"Installed {package} via uv"
        if _venv_path:
            msg += f" into {_venv_path}"
        if result.stdout.strip():
            msg += f"\n{result.stdout.strip()}"
        return msg
    except subprocess.CalledProcessError as e:
        return f"Failed to install {package}: {e.stderr}"
    except subprocess.TimeoutExpired:
        return f"Installation of {package} timed out."


# ── Collaboration ────────────────────────────────────────────────

@mcp.tool()
async def diff_notebook() -> str:
    """Detect changes the user made to the notebook since last snapshot."""
    if err := _require_notebook():
        return err

    try:
        nb_data = await _client.get_notebook(_notebook_path)
    except Exception as e:
        return f"Failed to read notebook: {e}"

    result = _tracker.diff(nb_data["content"])

    if not result["changed"]:
        return result["summary"]

    parts = [result["summary"]]
    cells = nb_data["content"].get("cells", [])

    for label, key in [("Added", "added_cells"), ("Modified", "modified_cells")]:
        if result[key]:
            parts.append(f"\n{label} cells:")
            for idx in result[key]:
                if idx < len(cells):
                    src = cells[idx].get("source", "")[:200]
                    parts.append(f"  [{idx}] {cells[idx]['cell_type']}: {src}")

    return "\n".join(parts)


@mcp.tool()
async def snapshot_notebook() -> str:
    """Save a snapshot of the current notebook state for future diffs."""
    if err := _require_notebook():
        return err

    try:
        nb_data = await _client.get_notebook(_notebook_path)
    except Exception as e:
        return f"Failed to read notebook: {e}"

    hash_val = _tracker.take_snapshot(nb_data["content"])
    cells = nb_data["content"].get("cells", [])
    return f"Snapshot saved ({len(cells)} cells, hash: {hash_val})."


# ── Main ─────────────────────────────────────────────────────────

def _init_imports():
    """Resolve sibling imports at startup."""
    global JupyterClient, NotebookTracker, _tracker
    sys.path.insert(0, str(Path(__file__).parent))
    from jclient import JupyterClient as _JC
    from notebook_tracker import NotebookTracker as _NT
    JupyterClient = _JC
    NotebookTracker = _NT
    _tracker = _NT()


if __name__ == "__main__":
    _init_imports()
    mcp.run()
