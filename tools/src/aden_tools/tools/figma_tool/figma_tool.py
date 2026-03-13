"""
Figma REST API Tool - Access Figma files, components, comments, and exports.

Supports:
- File inspection and node retrieval
- Image export (PNG, SVG, JPG, PDF)
- Comments (list, post, delete)
- Project and file browsing
- Component and style discovery
- Version history

API Reference: https://developers.figma.com/docs/rest-api/
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter


class _FigmaClient:
    """Internal client wrapping Figma REST API v1 calls."""

    API_BASE = "https://api.figma.com/v1"

    def __init__(self, token: str):
        self._token = token

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-Figma-Token": self._token}

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code == 403:
            return {"error": "Invalid or expired Figma access token"}
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code == 429:
            return {"error": "Rate limit exceeded. Try again later."}

        try:
            data = response.json()
        except Exception:
            if response.status_code >= 400:
                return {
                    "error": f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                }
            return {"error": "Invalid JSON response from Figma API"}

        if response.status_code >= 400:
            err = data.get("err", data.get("message", "Unknown error"))
            return {"error": f"Figma API error: {err}"}

        return data

    def get_file(
        self, file_key: str, depth: int | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        resp = httpx.get(
            f"{self.API_BASE}/files/{file_key}",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(resp)

    def get_file_nodes(
        self, file_key: str, ids: str, depth: int | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"ids": ids}
        if depth is not None:
            params["depth"] = depth
        resp = httpx.get(
            f"{self.API_BASE}/files/{file_key}/nodes",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(resp)

    def export_images(
        self,
        file_key: str,
        ids: str,
        fmt: str = "png",
        scale: float = 1.0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "ids": ids,
            "format": fmt,
            "scale": scale,
        }
        resp = httpx.get(
            f"{self.API_BASE}/images/{file_key}",
            headers=self._headers,
            params=params,
            timeout=60.0,
        )
        return self._handle_response(resp)

    def list_comments(self, file_key: str) -> dict[str, Any]:
        resp = httpx.get(
            f"{self.API_BASE}/files/{file_key}/comments",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(resp)

    def post_comment(
        self,
        file_key: str,
        message: str,
        comment_id: str | None = None,
        node_id: str | None = None,
        x: float | None = None,
        y: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"message": message}
        if comment_id:
            payload["comment_id"] = comment_id
        if node_id and x is not None and y is not None:
            payload["client_meta"] = {
                "node_id": node_id,
                "node_offset": {"x": x, "y": y},
            }
        resp = httpx.post(
            f"{self.API_BASE}/files/{file_key}/comments",
            headers=self._headers,
            json=payload,
            timeout=30.0,
        )
        return self._handle_response(resp)

    def delete_comment(
        self, file_key: str, comment_id: str
    ) -> dict[str, Any]:
        resp = httpx.delete(
            f"{self.API_BASE}/files/{file_key}/comments/{comment_id}",
            headers=self._headers,
            timeout=30.0,
        )
        if resp.status_code == 200:
            return {"success": True}
        return self._handle_response(resp)

    def list_projects(self, team_id: str) -> dict[str, Any]:
        resp = httpx.get(
            f"{self.API_BASE}/teams/{team_id}/projects",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(resp)

    def list_project_files(
        self, project_id: str
    ) -> dict[str, Any]:
        resp = httpx.get(
            f"{self.API_BASE}/projects/{project_id}/files",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(resp)

    def list_versions(self, file_key: str) -> dict[str, Any]:
        resp = httpx.get(
            f"{self.API_BASE}/files/{file_key}/versions",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(resp)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Figma REST API tools with the MCP server."""

    def _get_token() -> str | None:
        if credentials is not None:
            token = credentials.get("figma")
            if token is not None and not isinstance(token, str):
                raise TypeError(
                    f"Expected string from credentials.get('figma'), "
                    f"got {type(token).__name__}"
                )
            return token
        return os.getenv("FIGMA_ACCESS_TOKEN")

    def _get_client() -> _FigmaClient | dict[str, str]:
        token = _get_token()
        if not token:
            return {
                "error": "Figma credentials not configured",
                "help": (
                    "Set FIGMA_ACCESS_TOKEN environment variable "
                    "or configure via credential store"
                ),
            }
        return _FigmaClient(token)

    # --- File Inspection ---

    @mcp.tool()
    def figma_get_file(file_key: str, depth: int = 1) -> dict:
        """
        Get a Figma file's metadata and document structure.

        Returns file name, last modified date, pages, and the document
        tree up to the specified depth. Use depth=1 for pages only,
        depth=2 for top-level frames, or higher for deeper traversal.

        Args:
            file_key: The file key from the Figma URL
                (e.g., from figma.com/design/ABC123/...)
            depth: How deep to traverse the document tree (default 1).
                Higher values return more data but take longer.

        Returns:
            Dict with file name, lastModified, document tree, and
            component/style metadata
        """
        if not file_key:
            return {"error": "file_key is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.get_file(file_key, depth=depth)
            if "error" in result:
                return result
            return {
                "name": result.get("name"),
                "lastModified": result.get("lastModified"),
                "version": result.get("version"),
                "editorType": result.get("editorType"),
                "thumbnailUrl": result.get("thumbnailUrl"),
                "document": result.get("document"),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def figma_get_file_nodes(
        file_key: str, ids: str, depth: int = 0
    ) -> dict:
        """
        Get specific nodes from a Figma file by their IDs.

        Use this to retrieve detailed information about specific layers,
        frames, or components without fetching the entire file.

        Args:
            file_key: The file key from the Figma URL
            ids: Comma-separated node IDs (e.g., '1:2,1:3').
                Node IDs can be found in the Figma URL after ?node-id=
            depth: How deep to traverse below each node (0 = full subtree)

        Returns:
            Dict with node data including document structure, components,
            and styles for each requested node
        """
        if not file_key or not ids:
            return {"error": "file_key and ids are required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            d = depth if depth > 0 else None
            result = client.get_file_nodes(file_key, ids, depth=d)
            if "error" in result:
                return result
            return {
                "name": result.get("name"),
                "lastModified": result.get("lastModified"),
                "nodes": result.get("nodes"),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def figma_export_images(
        file_key: str,
        ids: str,
        format: str = "png",
        scale: float = 1.0,
    ) -> dict:
        """
        Export nodes from a Figma file as images.

        Renders the specified nodes and returns temporary download URLs
        (valid for 30 days). Supports PNG, SVG, JPG, and PDF formats.

        Args:
            file_key: The file key from the Figma URL
            ids: Comma-separated node IDs to export (e.g., '1:2,1:3')
            format: Image format — 'png', 'svg', 'jpg', or 'pdf'
                (default 'png')
            scale: Image scale factor, 0.01 to 4.0 (default 1.0).
                Only applies to raster formats (png, jpg).

        Returns:
            Dict with mapping of node IDs to image download URLs
        """
        if not file_key or not ids:
            return {"error": "file_key and ids are required"}
        fmt = format.lower()
        if fmt not in ("png", "svg", "jpg", "pdf"):
            return {"error": "format must be png, svg, jpg, or pdf"}
        if not 0.01 <= scale <= 4.0:
            return {"error": "scale must be between 0.01 and 4.0"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.export_images(
                file_key, ids, fmt=fmt, scale=scale
            )
            if "error" in result:
                return result
            return {
                "success": True,
                "images": result.get("images", {}),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Comments ---

    @mcp.tool()
    def figma_list_comments(file_key: str) -> dict:
        """
        List all comments on a Figma file.

        Returns comments with author info, message text, timestamps,
        and any replies.

        Args:
            file_key: The file key from the Figma URL

        Returns:
            Dict with list of comments including id, message, user,
            created_at, and resolved status
        """
        if not file_key:
            return {"error": "file_key is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.list_comments(file_key)
            if "error" in result:
                return result
            comments = [
                {
                    "id": c.get("id"),
                    "message": c.get("message"),
                    "user": c.get("user", {}).get("handle"),
                    "created_at": c.get("created_at"),
                    "resolved_at": c.get("resolved_at"),
                    "order_id": c.get("order_id"),
                }
                for c in result.get("comments", [])
            ]
            return {
                "success": True,
                "comments": comments,
                "count": len(comments),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def figma_post_comment(
        file_key: str,
        message: str,
        reply_to: str = "",
        node_id: str = "",
        x: float = 0.0,
        y: float = 0.0,
    ) -> dict:
        """
        Post a comment on a Figma file.

        Can post a top-level comment, a reply to an existing comment,
        or a comment anchored to a specific node at given coordinates.

        Args:
            file_key: The file key from the Figma URL
            message: The comment text
            reply_to: Optional comment ID to reply to
            node_id: Optional node ID to anchor the comment to.
                Requires x and y coordinates.
            x: X coordinate for positioned comment (used with node_id)
            y: Y coordinate for positioned comment (used with node_id)

        Returns:
            Dict with the created comment's id, message, and metadata
        """
        if not file_key or not message:
            return {"error": "file_key and message are required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.post_comment(
                file_key,
                message,
                comment_id=reply_to or None,
                node_id=node_id or None,
                x=x if node_id else None,
                y=y if node_id else None,
            )
            if "error" in result:
                return result
            return {
                "success": True,
                "id": result.get("id"),
                "message": result.get("message"),
                "user": result.get("user", {}).get("handle"),
                "created_at": result.get("created_at"),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def figma_delete_comment(
        file_key: str, comment_id: str
    ) -> dict:
        """
        Delete a comment from a Figma file.

        Only the comment creator can delete their own comments.

        Args:
            file_key: The file key from the Figma URL
            comment_id: The ID of the comment to delete

        Returns:
            Dict with success status or error
        """
        if not file_key or not comment_id:
            return {"error": "file_key and comment_id are required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.delete_comment(file_key, comment_id)
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Projects ---

    @mcp.tool()
    def figma_list_projects(team_id: str) -> dict:
        """
        List all projects in a Figma team.

        Args:
            team_id: The team ID (found in team URL or settings)

        Returns:
            Dict with list of projects including id and name
        """
        if not team_id:
            return {"error": "team_id is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.list_projects(team_id)
            if "error" in result:
                return result
            projects = [
                {"id": p.get("id"), "name": p.get("name")}
                for p in result.get("projects", [])
            ]
            return {
                "success": True,
                "projects": projects,
                "count": len(projects),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def figma_list_project_files(project_id: str) -> dict:
        """
        List all files in a Figma project.

        Args:
            project_id: The project ID (from figma_list_projects)

        Returns:
            Dict with list of files including key, name, and
            last_modified timestamp
        """
        if not project_id:
            return {"error": "project_id is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.list_project_files(project_id)
            if "error" in result:
                return result
            files = [
                {
                    "key": f.get("key"),
                    "name": f.get("name"),
                    "last_modified": f.get("last_modified"),
                    "thumbnail_url": f.get("thumbnail_url"),
                }
                for f in result.get("files", [])
            ]
            return {
                "success": True,
                "files": files,
                "count": len(files),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Components & Styles ---

    @mcp.tool()
    def figma_get_components(file_key: str) -> dict:
        """
        List all components in a Figma file.

        Returns metadata for every component in the file, including
        name, description, and node ID. Useful for design system
        inventory and component discovery.

        Args:
            file_key: The file key from the Figma URL

        Returns:
            Dict with list of components including id, name,
            description, and containing_frame
        """
        if not file_key:
            return {"error": "file_key is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.get_file(file_key, depth=1)
            if "error" in result:
                return result
            raw = result.get("components", {})
            components = [
                {
                    "node_id": node_id,
                    "name": meta.get("name"),
                    "description": meta.get("description"),
                    "containing_frame": meta.get(
                        "containing_frame", {}
                    ).get("name"),
                }
                for node_id, meta in raw.items()
            ]
            return {
                "success": True,
                "components": components,
                "count": len(components),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    @mcp.tool()
    def figma_get_styles(file_key: str) -> dict:
        """
        List all styles in a Figma file.

        Returns metadata for every style (colors, text styles,
        effects, grids) defined in the file. Useful for design
        system auditing.

        Args:
            file_key: The file key from the Figma URL

        Returns:
            Dict with list of styles including key, name,
            style_type, and description
        """
        if not file_key:
            return {"error": "file_key is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.get_file(file_key, depth=1)
            if "error" in result:
                return result
            raw = result.get("styles", {})
            styles = [
                {
                    "node_id": node_id,
                    "name": meta.get("name"),
                    "style_type": meta.get("styleType"),
                    "description": meta.get("description"),
                }
                for node_id, meta in raw.items()
            ]
            return {
                "success": True,
                "styles": styles,
                "count": len(styles),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}

    # --- Version History ---

    @mcp.tool()
    def figma_list_versions(file_key: str) -> dict:
        """
        Get the version history of a Figma file.

        Returns a list of saved versions with user, description,
        and timestamp. Useful for tracking design changes over time.

        Args:
            file_key: The file key from the Figma URL

        Returns:
            Dict with list of versions including id, label, user,
            description, and created_at
        """
        if not file_key:
            return {"error": "file_key is required"}

        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            result = client.list_versions(file_key)
            if "error" in result:
                return result
            versions = [
                {
                    "id": v.get("id"),
                    "label": v.get("label"),
                    "description": v.get("description"),
                    "user": v.get("user", {}).get("handle"),
                    "created_at": v.get("created_at"),
                }
                for v in result.get("versions", [])
            ]
            return {
                "success": True,
                "versions": versions,
                "count": len(versions),
            }
        except httpx.TimeoutException:
            return {"error": "Request timed out"}
        except httpx.RequestError as e:
            return {"error": f"Network error: {e}"}
