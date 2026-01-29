# jupyter-agent

A Claude Code plugin for Jupyter notebook-based research. Connects to your existing Jupyter server, executes code, and fixes errors in-place.

## Features

- **Connects to your running Jupyter** -- no separate server, you keep full browser access
- **Edits cells on error** -- fixes broken cells in-place instead of creating new ones
- **Proper Claude Code plugin** -- install via marketplace, no separate CLI needed
- **Custom kernel support** -- point at any `.venv` and the plugin registers it as a Jupyter kernel
- **Collaborative** -- detects user edits with notebook diffing/snapshots

## Installation

```bash
# Add the marketplace
/plugin marketplace add kdkyum/jupyter-agent

# Install the plugin
/plugin install jupyter-agent@jupyter-agent
```

The plugin runs via `uv run`, so [uv](https://docs.astral.sh/uv/) must be installed on your system.

## Quick Start

1. Start your Jupyter server:
   ```bash
   jupyter notebook --no-browser
   # Note the URL and token from the output
   ```

2. In Claude Code, connect to the server:
   ```
   /jupyter-agent:connect http://localhost:8888 YOUR_TOKEN research.ipynb
   ```

3. (Optional) Point at a project venv so the kernel uses its packages:
   ```
   setup_kernel("/path/to/project/.venv")
   ```

4. Start researching -- the agent will create cells, execute code, and fix errors automatically.

## Commands

| Command | Description |
|---------|-------------|
| `/jupyter-agent:jupyter-agent <url> <token> [path]` | Start a full research session |
| `/jupyter-agent:connect <url> <token> [path]` | Connect to a Jupyter server |
| `/jupyter-agent:status` | Show current session status |

## MCP Tools

### Connection
- `connect(server_url, token, notebook_path?, kernel_name?)` -- Connect to an existing Jupyter server. Optionally open a notebook and choose a kernel.

### Kernel Setup
- `setup_kernel(venv_path, kernel_name?)` -- Register a `.venv` as a Jupyter kernel. Installs `ipykernel` into the venv and registers it so all subsequent sessions use that environment.

### Notebook Management
- `create_notebook(path, title?, kernel_name?)` -- Create a new `.ipynb` and start a kernel session
- `read_notebook(mode?, last_n?)` -- Read notebook state (`full`, `last_n`, or `summary`)
- `add_cell` -- Insert a cell without executing
- `edit_cell` -- Edit a cell's source without executing
- `get_cell_output` -- Get a specific cell's output

### Execution
- `execute_cell` -- Execute code, optionally adding to notebook
- `edit_and_run_cell` -- Edit + execute in one call (primary error-fix tool)

### Kernel Management
- `restart_kernel` -- Restart the kernel
- `interrupt_kernel` -- Interrupt running execution
- `install_package` -- Install a package via `uv pip install` into the kernel's venv

### Collaboration
- `diff_notebook` -- Detect user changes since last snapshot
- `snapshot_notebook` -- Save baseline for future diffs

## Architecture

```
User's Jupyter Server (JupyterLab / Notebook)
    ↕  REST API + WebSocket
MCP Server (uv run python mcp/server.py)
    ↕
Claude Code (via plugin)
```

The plugin connects to your already-running Jupyter server. Both you and the agent share the same notebook and kernel -- you can see cells appear and outputs update in real-time.

## Error Handling

When code execution fails, the agent:
1. Reads the error from the failed cell
2. Edits the same cell with fixed code using `edit_and_run_cell`
3. Never creates duplicate cells to work around errors

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (used to run the plugin and install packages)
- `mcp[cli]` and `aiohttp` (auto-installed by `uv` on first run)
- A running Jupyter server (Notebook or JupyterLab)

## License

MIT
