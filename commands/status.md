# Session Status

Show the current Jupyter Agent session status.

## Usage

```
/jupyter-agent:status
```

## Behavior

1. Check if connected to a Jupyter server.
2. If connected, show:
   - Server URL
   - Notebook path (if any)
   - Kernel ID (if any)
   - Notebook summary via `read_notebook(mode="summary")`
3. If not connected, inform the user and suggest using `/jupyter-agent:connect`.
