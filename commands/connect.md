# Connect to Jupyter Server

Connect to a running Jupyter server and optionally open a notebook.

## Usage

```
/jupyter-agent:connect <server_url> <token> [notebook_path]
```

## Behavior

1. Call `connect(server_url, token, notebook_path)` to establish the connection.
2. If a notebook path is provided:
   - If the notebook exists, attach to its kernel session.
   - If it doesn't exist, inform the user and suggest `create_notebook`.
3. Report the connection status.

## Examples

```
/jupyter-agent:connect http://localhost:8888 abc123
/jupyter-agent:connect http://localhost:8888 abc123 research/analysis.ipynb
```
