# jupyter-agent

A Claude Code plugin for Jupyter notebook-based research. Connects to your existing Jupyter server, executes code, and fixes errors in-place.

## Features

- **Connects to your running Jupyter** — no separate server, you keep full browser access
- **Edits cells on error** — fixes broken cells in-place instead of creating new ones
- **Proper Claude Code plugin** — install via marketplace, no separate CLI needed
- **Collaborative** — detects user edits with notebook diffing/snapshots

## Installation

```bash
# Add the marketplace
/plugin marketplace add kdkyum/jupyter-agent

# Install the plugin
/plugin install jupyter-agent@jupyter-agent
```

## Quick Start

1. Start your Jupyter server:
   ```bash
   jupyter notebook --no-browser
   # Note the URL and token from the output
   ```

2. In Claude Code:
   ```
   /jupyter-agent:connect http://localhost:8888 YOUR_TOKEN research.ipynb
   ```

3. Start researching — the agent will create cells, execute code, and fix errors automatically.

## Commands

| Command | Description |
|---------|-------------|
| `/jupyter-agent:jupyter-agent <url> <token> [path]` | Start a full research session |
| `/jupyter-agent:connect <url> <token> [path]` | Connect to a Jupyter server |
| `/jupyter-agent:status` | Show current session status |

## MCP Tools

### Connection
- `connect` — Connect to an existing Jupyter server

### Notebook Management
- `create_notebook` — Create a new .ipynb and start a kernel
- `read_notebook` — Read notebook state (full, last_n, or summary)
- `add_cell` — Insert a cell without executing
- `edit_cell` — Edit a cell's source without executing
- `get_cell_output` — Get a specific cell's output

### Execution
- `execute_cell` — Execute code, optionally adding to notebook
- `edit_and_run_cell` — Edit + execute in one call (primary error-fix tool)

### Kernel Management
- `restart_kernel` — Restart the kernel
- `interrupt_kernel` — Interrupt running execution
- `install_package` — Install a pip package in the kernel

### Collaboration
- `diff_notebook` — Detect user changes since last snapshot
- `snapshot_notebook` — Save baseline for future diffs

## Architecture

```
User's Jupyter Server (JupyterLab / Notebook)
    ↕  REST API + WebSocket
MCP Server (connects to existing server)
    ↕
Claude Code (via plugin)
```

The plugin connects to your already-running Jupyter server. Both you and the agent share the same notebook and kernel — you can see cells appear and outputs update in real-time.

## Error Handling

When code execution fails, the agent:
1. Reads the error from the failed cell
2. Edits the same cell with fixed code using `edit_and_run_cell`
3. Never creates duplicate cells to work around errors

## Requirements

- Python 3.10+
- `mcp[cli]` and `aiohttp` (auto-installed on first run)
- A running Jupyter server (Notebook or JupyterLab)

## License

MIT
