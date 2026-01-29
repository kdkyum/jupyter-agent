# Jupyter Agent — Start Research

Start a Jupyter research session. Connect to the user's Jupyter server, open or create a notebook, and begin working.

## Usage

```
/jupyter-agent:jupyter-agent <server_url> <token> [notebook_path]
```

## Behavior

1. Call `connect(server_url, token, notebook_path)` to connect to the Jupyter server.
2. If `notebook_path` is provided and exists, read it with `read_notebook(mode="summary")`.
3. If `notebook_path` is provided but doesn't exist, create it with `create_notebook(path)`.
4. Take a snapshot with `snapshot_notebook()`.
5. Confirm the connection and ask what the user wants to research.

If arguments are missing, ask the user for:
- Server URL (usually `http://localhost:8888`)
- Token (from the Jupyter server startup output)
- Notebook path (optional — can create later)

## Agent

Use the Jupyter Researcher agent persona: structured, methodical, focused on producing clean reproducible notebooks. Fix errors in-place using `edit_and_run_cell`.
