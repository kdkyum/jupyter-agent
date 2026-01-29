"""Jupyter REST API + WebSocket client for connecting to an existing Jupyter server."""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import aiohttp


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text for readable error messages."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


class JupyterClient:
    """Client for communicating with a running Jupyter server via REST API and WebSocket."""

    def __init__(self, server_url: str, token: str):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ws_kernel_id: str | None = None

    @property
    def headers(self) -> dict:
        return {"Authorization": f"token {self.token}"}

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def close(self):
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()

    # ── REST helpers ──────────────────────────────────────────────

    async def _get(self, path: str) -> dict:
        session = await self._get_session()
        url = f"{self.server_url}{path}"
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _post(self, path: str, data: dict | None = None) -> dict:
        session = await self._get_session()
        url = f"{self.server_url}{path}"
        async with session.post(url, json=data or {}) as resp:
            resp.raise_for_status()
            if resp.content_length == 0:
                return {}
            return await resp.json()

    async def _put(self, path: str, data: dict) -> dict:
        session = await self._get_session()
        url = f"{self.server_url}{path}"
        async with session.put(url, json=data) as resp:
            resp.raise_for_status()
            if resp.content_length == 0:
                return {}
            return await resp.json()

    async def _patch(self, path: str, data: dict) -> dict:
        session = await self._get_session()
        url = f"{self.server_url}{path}"
        async with session.patch(url, json=data) as resp:
            resp.raise_for_status()
            if resp.content_length == 0:
                return {}
            return await resp.json()

    async def _delete(self, path: str) -> None:
        session = await self._get_session()
        url = f"{self.server_url}{path}"
        async with session.delete(url) as resp:
            resp.raise_for_status()

    # ── Connection test ───────────────────────────────────────────

    async def check_connection(self) -> dict:
        """Test connection to the Jupyter server. Returns server status."""
        return await self._get("/api/status")

    # ── Kernel management ─────────────────────────────────────────

    async def list_kernels(self) -> list[dict]:
        return await self._get("/api/kernels")

    async def start_kernel(self, name: str = "python3") -> dict:
        return await self._post("/api/kernels", {"name": name})

    async def restart_kernel(self, kernel_id: str) -> dict:
        """Restart a kernel (clears state, keeps notebook)."""
        return await self._post(f"/api/kernels/{kernel_id}/restart")

    async def interrupt_kernel(self, kernel_id: str) -> dict:
        """Interrupt a running execution."""
        return await self._post(f"/api/kernels/{kernel_id}/interrupt")

    async def shutdown_kernel(self, kernel_id: str) -> None:
        await self._delete(f"/api/kernels/{kernel_id}")

    # ── Session management ────────────────────────────────────────

    async def list_sessions(self) -> list[dict]:
        return await self._get("/api/sessions")

    async def create_session(self, notebook_path: str, kernel_name: str = "python3") -> dict:
        return await self._post("/api/sessions", {
            "path": notebook_path,
            "type": "notebook",
            "kernel": {"name": kernel_name},
        })

    async def get_session_for_notebook(self, notebook_path: str) -> dict | None:
        """Find existing session for a notebook path."""
        sessions = await self.list_sessions()
        for s in sessions:
            if s.get("path") == notebook_path or s.get("notebook", {}).get("path") == notebook_path:
                return s
        return None

    # ── Notebook (Contents API) ───────────────────────────────────

    async def get_notebook(self, path: str) -> dict:
        """Get notebook content."""
        return await self._get(f"/api/contents/{path}?type=notebook&content=1")

    async def save_notebook(self, path: str, content: dict) -> dict:
        """Save notebook content."""
        return await self._put(f"/api/contents/{path}", {
            "type": "notebook",
            "content": content,
        })

    async def create_notebook(self, path: str, kernel_name: str = "python3") -> dict:
        """Create a new empty notebook at the given path."""
        nb_content = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {
                    "display_name": kernel_name,
                    "language": "python",
                    "name": kernel_name,
                },
                "language_info": {
                    "name": "python",
                },
            },
            "cells": [],
        }
        return await self._put(f"/api/contents/{path}", {
            "type": "notebook",
            "content": nb_content,
        })

    async def list_contents(self, path: str = "") -> dict:
        return await self._get(f"/api/contents/{path}")

    # ── WebSocket execution ───────────────────────────────────────

    async def _ensure_ws(self, kernel_id: str):
        """Ensure WebSocket connection to the kernel."""
        if self._ws and not self._ws.closed and self._ws_kernel_id == kernel_id:
            return

        if self._ws and not self._ws.closed:
            await self._ws.close()

        parsed = urlparse(self.server_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        ws_url = f"{ws_scheme}://{parsed.netloc}/api/kernels/{kernel_id}/channels?token={self.token}"

        session = await self._get_session()
        self._ws = await session.ws_connect(ws_url)
        self._ws_kernel_id = kernel_id

    async def execute_code(self, kernel_id: str, code: str, timeout: int = 120) -> dict:
        """Execute code on a kernel via WebSocket. Returns structured result."""
        await self._ensure_ws(kernel_id)

        msg_id = str(uuid.uuid4())
        execute_msg = {
            "header": {
                "msg_id": msg_id,
                "msg_type": "execute_request",
                "username": "jupyter-agent",
                "session": str(uuid.uuid4()),
                "date": datetime.now(timezone.utc).isoformat(),
                "version": "5.3",
            },
            "parent_header": {},
            "metadata": {},
            "content": {
                "code": code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True,
            },
            "channel": "shell",
        }

        await self._ws.send_json(execute_msg)

        outputs = []
        error = None
        status = "ok"

        try:
            async with asyncio.timeout(timeout):
                while True:
                    msg = await self._ws.receive_json()
                    parent = msg.get("parent_header", {})
                    if parent.get("msg_id") != msg_id:
                        continue

                    msg_type = msg.get("msg_type", "")
                    content = msg.get("content", {})

                    if msg_type == "stream":
                        outputs.append({
                            "output_type": "stream",
                            "name": content.get("name", "stdout"),
                            "text": content.get("text", ""),
                        })
                    elif msg_type == "display_data":
                        outputs.append({
                            "output_type": "display_data",
                            "data": content.get("data", {}),
                            "metadata": content.get("metadata", {}),
                        })
                    elif msg_type == "execute_result":
                        outputs.append({
                            "output_type": "execute_result",
                            "data": content.get("data", {}),
                            "metadata": content.get("metadata", {}),
                            "execution_count": content.get("execution_count"),
                        })
                    elif msg_type == "error":
                        traceback_text = "\n".join(content.get("traceback", []))
                        error = {
                            "ename": content.get("ename", ""),
                            "evalue": _strip_ansi(content.get("evalue", "")),
                            "traceback": _strip_ansi(traceback_text),
                        }
                        outputs.append({
                            "output_type": "error",
                            "ename": error["ename"],
                            "evalue": error["evalue"],
                            "traceback": content.get("traceback", []),
                        })
                        status = "error"
                    elif msg_type in ("execute_reply",):
                        if content.get("status") == "error" and error is None:
                            traceback_text = "\n".join(content.get("traceback", []))
                            error = {
                                "ename": content.get("ename", ""),
                                "evalue": _strip_ansi(content.get("evalue", "")),
                                "traceback": _strip_ansi(traceback_text),
                            }
                            status = "error"
                        break
                    elif msg_type == "status":
                        if content.get("execution_state") == "idle":
                            # Wait for the execute_reply
                            pass
        except TimeoutError:
            status = "timeout"
            error = {
                "ename": "TimeoutError",
                "evalue": f"Execution timed out after {timeout}s",
                "traceback": "",
            }

        return {
            "status": status,
            "outputs": outputs,
            "error": error,
        }

    # ── Helpers ───────────────────────────────────────────────────

    async def add_cell_to_notebook(
        self,
        notebook_path: str,
        source: str,
        cell_type: str = "code",
        position: int | None = None,
        outputs: list | None = None,
    ) -> tuple[dict, int]:
        """Add a cell to a notebook. Returns (notebook_content, cell_index)."""
        nb_data = await self.get_notebook(notebook_path)
        nb = nb_data["content"]

        cell = {
            "cell_type": cell_type,
            "source": source,
            "metadata": {},
            "id": str(uuid.uuid4()).replace("-", "")[:8],
        }
        if cell_type == "code":
            cell["outputs"] = outputs or []
            cell["execution_count"] = None

        cells = nb.get("cells", [])
        if position is not None and 0 <= position <= len(cells):
            cells.insert(position, cell)
            idx = position
        else:
            cells.append(cell)
            idx = len(cells) - 1

        nb["cells"] = cells
        await self.save_notebook(notebook_path, nb)
        return nb, idx

    async def edit_cell_source(
        self, notebook_path: str, cell_index: int, new_source: str
    ) -> dict:
        """Edit a cell's source code. Returns updated notebook content."""
        nb_data = await self.get_notebook(notebook_path)
        nb = nb_data["content"]
        cells = nb.get("cells", [])

        if cell_index < 0 or cell_index >= len(cells):
            raise IndexError(f"Cell index {cell_index} out of range (0-{len(cells)-1})")

        cells[cell_index]["source"] = new_source
        if cells[cell_index]["cell_type"] == "code":
            cells[cell_index]["outputs"] = []
            cells[cell_index]["execution_count"] = None

        await self.save_notebook(notebook_path, nb)
        return nb

    async def update_cell_outputs(
        self, notebook_path: str, cell_index: int, outputs: list, execution_count: int | None = None
    ) -> dict:
        """Update a cell's outputs after execution. Returns updated notebook."""
        nb_data = await self.get_notebook(notebook_path)
        nb = nb_data["content"]
        cells = nb.get("cells", [])

        if cell_index < 0 or cell_index >= len(cells):
            raise IndexError(f"Cell index {cell_index} out of range (0-{len(cells)-1})")

        cells[cell_index]["outputs"] = outputs
        if execution_count is not None:
            cells[cell_index]["execution_count"] = execution_count

        await self.save_notebook(notebook_path, nb)
        return nb
