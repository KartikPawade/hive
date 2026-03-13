"""Tests for Figma tool with FastMCP."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastmcp import FastMCP

from aden_tools.tools.figma_tool import register_tools


@pytest.fixture
def mcp():
    """Create a FastMCP instance for testing."""
    return FastMCP("test-server")


def _get_tool_fn(mcp: FastMCP, name: str):
    """Register tools and return a specific tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools[name].fn


@pytest.fixture
def figma_get_file_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_get_file")


@pytest.fixture
def figma_get_file_nodes_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_get_file_nodes")


@pytest.fixture
def figma_export_images_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_export_images")


@pytest.fixture
def figma_list_comments_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_list_comments")


@pytest.fixture
def figma_post_comment_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_post_comment")


@pytest.fixture
def figma_delete_comment_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_delete_comment")


@pytest.fixture
def figma_list_projects_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_list_projects")


@pytest.fixture
def figma_list_project_files_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_list_project_files")


@pytest.fixture
def figma_get_components_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_get_components")


@pytest.fixture
def figma_get_styles_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_get_styles")


@pytest.fixture
def figma_list_versions_fn(mcp: FastMCP):
    return _get_tool_fn(mcp, "figma_list_versions")


class TestFigmaRegistration:
    """Tests for Figma tool registration."""

    def test_all_tools_registered(self, mcp: FastMCP):
        """All 11 Figma tools should be registered."""
        register_tools(mcp)
        tool_names = list(mcp._tool_manager._tools.keys())
        expected = [
            "figma_get_file",
            "figma_get_file_nodes",
            "figma_export_images",
            "figma_list_comments",
            "figma_post_comment",
            "figma_delete_comment",
            "figma_list_projects",
            "figma_list_project_files",
            "figma_get_components",
            "figma_get_styles",
            "figma_list_versions",
        ]
        for name in expected:
            assert name in tool_names, f"{name} not registered"

    def test_register_with_credential_store(self, mcp: FastMCP):
        """Registration works with a credential store adapter."""
        mock_creds = MagicMock()
        mock_creds.get.return_value = "figd_test_token"
        register_tools(mcp, credentials=mock_creds)
        assert "figma_get_file" in mcp._tool_manager._tools


class TestFigmaCredentials:
    """Tests for Figma credential handling."""

    def test_no_credentials_returns_error(
        self, figma_get_file_fn, monkeypatch
    ):
        monkeypatch.delenv("FIGMA_ACCESS_TOKEN", raising=False)
        result = figma_get_file_fn(file_key="abc123")
        assert "error" in result
        assert "not configured" in result["error"]

    def test_env_var_fallback(
        self, monkeypatch, mcp: FastMCP
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "figd_env_token")
        register_tools(mcp)
        fn = mcp._tool_manager._tools["figma_get_file"].fn

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "name": "Test File",
                "lastModified": "2024-01-01",
                "version": "1",
                "editorType": "figma",
                "thumbnailUrl": "https://example.com/thumb.png",
                "document": {"id": "0:0", "type": "DOCUMENT"},
            }
            mock_get.return_value = mock_resp

            result = fn(file_key="abc123")
            assert result["name"] == "Test File"

            call_headers = mock_get.call_args[1]["headers"]
            assert call_headers["X-Figma-Token"] == "figd_env_token"

    def test_credential_store_used(self, mcp: FastMCP):
        mock_creds = MagicMock()
        mock_creds.get.return_value = "figd_store_token"
        register_tools(mcp, credentials=mock_creds)
        fn = mcp._tool_manager._tools["figma_get_file"].fn

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "name": "File",
                "lastModified": "2024-01-01",
                "version": "1",
                "editorType": "figma",
                "thumbnailUrl": "",
                "document": {},
            }
            mock_get.return_value = mock_resp

            fn(file_key="abc123")
            call_headers = mock_get.call_args[1]["headers"]
            assert call_headers["X-Figma-Token"] == "figd_store_token"
            mock_creds.get.assert_called_with("figma")


class TestFigmaGetFile:
    """Tests for figma_get_file tool."""

    def test_get_file_success(
        self, figma_get_file_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "name": "My Design",
                "lastModified": "2024-06-01T10:00:00Z",
                "version": "12345",
                "editorType": "figma",
                "thumbnailUrl": "https://example.com/thumb.png",
                "document": {
                    "id": "0:0",
                    "type": "DOCUMENT",
                    "children": [],
                },
            }
            mock_get.return_value = mock_resp

            result = figma_get_file_fn(file_key="abc123")

        assert result["name"] == "My Design"
        assert result["version"] == "12345"
        assert "document" in result

    def test_get_file_empty_key(self, figma_get_file_fn, monkeypatch):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")
        result = figma_get_file_fn(file_key="")
        assert "error" in result

    def test_get_file_403(self, figma_get_file_fn, monkeypatch):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "bad-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_get.return_value = mock_resp

            result = figma_get_file_fn(file_key="abc123")

        assert "error" in result
        assert "token" in result["error"].lower()

    def test_get_file_404(self, figma_get_file_fn, monkeypatch):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_get.return_value = mock_resp

            result = figma_get_file_fn(file_key="nonexistent")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_get_file_timeout(
        self, figma_get_file_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            result = figma_get_file_fn(file_key="abc123")

        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_get_file_network_error(
        self, figma_get_file_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("refused")
            result = figma_get_file_fn(file_key="abc123")

        assert "error" in result
        assert "network" in result["error"].lower()


class TestFigmaGetFileNodes:
    """Tests for figma_get_file_nodes tool."""

    def test_get_nodes_success(
        self, figma_get_file_nodes_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "name": "My Design",
                "lastModified": "2024-06-01T10:00:00Z",
                "nodes": {
                    "1:2": {
                        "document": {
                            "id": "1:2",
                            "name": "Frame",
                            "type": "FRAME",
                        }
                    }
                },
            }
            mock_get.return_value = mock_resp

            result = figma_get_file_nodes_fn(
                file_key="abc123", ids="1:2"
            )

        assert result["nodes"]["1:2"]["document"]["type"] == "FRAME"

    def test_get_nodes_missing_args(
        self, figma_get_file_nodes_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")
        result = figma_get_file_nodes_fn(file_key="", ids="1:2")
        assert "error" in result

        result = figma_get_file_nodes_fn(file_key="abc", ids="")
        assert "error" in result


class TestFigmaExportImages:
    """Tests for figma_export_images tool."""

    def test_export_success(
        self, figma_export_images_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "images": {
                    "1:2": "https://example.com/image.png"
                }
            }
            mock_get.return_value = mock_resp

            result = figma_export_images_fn(
                file_key="abc123", ids="1:2", format="png"
            )

        assert result["success"] is True
        assert "1:2" in result["images"]

    def test_export_invalid_format(
        self, figma_export_images_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")
        result = figma_export_images_fn(
            file_key="abc123", ids="1:2", format="gif"
        )
        assert "error" in result
        assert "format" in result["error"]

    def test_export_invalid_scale(
        self, figma_export_images_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")
        result = figma_export_images_fn(
            file_key="abc123", ids="1:2", scale=5.0
        )
        assert "error" in result
        assert "scale" in result["error"]

    def test_export_svg_format(
        self, figma_export_images_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "images": {"1:2": "https://example.com/image.svg"}
            }
            mock_get.return_value = mock_resp

            result = figma_export_images_fn(
                file_key="abc123",
                ids="1:2",
                format="SVG",
            )

        assert result["success"] is True


class TestFigmaComments:
    """Tests for comment tools."""

    def test_list_comments_success(
        self, figma_list_comments_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "comments": [
                    {
                        "id": "c1",
                        "message": "Nice work!",
                        "user": {"handle": "alice"},
                        "created_at": "2024-06-01T10:00:00Z",
                        "resolved_at": None,
                        "order_id": "1",
                    },
                ]
            }
            mock_get.return_value = mock_resp

            result = figma_list_comments_fn(file_key="abc123")

        assert result["success"] is True
        assert result["count"] == 1
        assert result["comments"][0]["message"] == "Nice work!"

    def test_post_comment_success(
        self, figma_post_comment_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "id": "c2",
                "message": "Looks good",
                "user": {"handle": "bob"},
                "created_at": "2024-06-01T11:00:00Z",
            }
            mock_post.return_value = mock_resp

            result = figma_post_comment_fn(
                file_key="abc123", message="Looks good"
            )

        assert result["success"] is True
        assert result["id"] == "c2"

    def test_post_comment_missing_message(
        self, figma_post_comment_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")
        result = figma_post_comment_fn(
            file_key="abc123", message=""
        )
        assert "error" in result

    def test_delete_comment_success(
        self, figma_delete_comment_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.delete") as mock_delete:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_delete.return_value = mock_resp

            result = figma_delete_comment_fn(
                file_key="abc123", comment_id="c1"
            )

        assert result["success"] is True

    def test_delete_comment_missing_id(
        self, figma_delete_comment_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")
        result = figma_delete_comment_fn(
            file_key="abc123", comment_id=""
        )
        assert "error" in result


class TestFigmaProjects:
    """Tests for project and file listing tools."""

    def test_list_projects_success(
        self, figma_list_projects_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "projects": [
                    {"id": "p1", "name": "Project Alpha"},
                    {"id": "p2", "name": "Project Beta"},
                ]
            }
            mock_get.return_value = mock_resp

            result = figma_list_projects_fn(team_id="t1")

        assert result["success"] is True
        assert result["count"] == 2

    def test_list_projects_empty_team_id(
        self, figma_list_projects_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")
        result = figma_list_projects_fn(team_id="")
        assert "error" in result

    def test_list_project_files_success(
        self, figma_list_project_files_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "files": [
                    {
                        "key": "f1",
                        "name": "Homepage",
                        "last_modified": "2024-06-01T10:00:00Z",
                        "thumbnail_url": "https://example.com/t.png",
                    },
                ]
            }
            mock_get.return_value = mock_resp

            result = figma_list_project_files_fn(
                project_id="p1"
            )

        assert result["success"] is True
        assert result["files"][0]["name"] == "Homepage"


class TestFigmaComponentsAndStyles:
    """Tests for component and style discovery tools."""

    def test_get_components_success(
        self, figma_get_components_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "name": "Design System",
                "lastModified": "2024-06-01",
                "version": "1",
                "editorType": "figma",
                "thumbnailUrl": "",
                "document": {},
                "components": {
                    "1:100": {
                        "name": "Button/Primary",
                        "description": "Primary CTA button",
                        "containing_frame": {
                            "name": "Buttons"
                        },
                    },
                },
            }
            mock_get.return_value = mock_resp

            result = figma_get_components_fn(
                file_key="abc123"
            )

        assert result["success"] is True
        assert result["count"] == 1
        assert (
            result["components"][0]["name"] == "Button/Primary"
        )

    def test_get_styles_success(
        self, figma_get_styles_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "name": "Design System",
                "lastModified": "2024-06-01",
                "version": "1",
                "editorType": "figma",
                "thumbnailUrl": "",
                "document": {},
                "styles": {
                    "2:50": {
                        "name": "Brand/Blue",
                        "styleType": "FILL",
                        "description": "Primary brand color",
                    },
                },
            }
            mock_get.return_value = mock_resp

            result = figma_get_styles_fn(file_key="abc123")

        assert result["success"] is True
        assert result["count"] == 1
        assert result["styles"][0]["style_type"] == "FILL"


class TestFigmaVersions:
    """Tests for version history tool."""

    def test_list_versions_success(
        self, figma_list_versions_fn, monkeypatch
    ):
        monkeypatch.setenv("FIGMA_ACCESS_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "versions": [
                    {
                        "id": "v1",
                        "label": "Release 1.0",
                        "description": "First release",
                        "user": {"handle": "alice"},
                        "created_at": "2024-06-01T10:00:00Z",
                    },
                    {
                        "id": "v2",
                        "label": "",
                        "description": "Bug fix",
                        "user": {"handle": "bob"},
                        "created_at": "2024-06-02T10:00:00Z",
                    },
                ]
            }
            mock_get.return_value = mock_resp

            result = figma_list_versions_fn(
                file_key="abc123"
            )

        assert result["success"] is True
        assert result["count"] == 2
        assert result["versions"][0]["label"] == "Release 1.0"


class TestFigmaClient:
    """Tests for _FigmaClient internal methods."""

    def test_handle_response_rate_limit(self, monkeypatch):
        from aden_tools.tools.figma_tool.figma_tool import (
            _FigmaClient,
        )

        client = _FigmaClient("test-token")
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        result = client._handle_response(mock_resp)
        assert "rate limit" in result["error"].lower()

    def test_handle_response_json_error(self, monkeypatch):
        from aden_tools.tools.figma_tool.figma_tool import (
            _FigmaClient,
        )

        client = _FigmaClient("test-token")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.side_effect = ValueError("bad json")
        mock_resp.text = "Internal Server Error"
        result = client._handle_response(mock_resp)
        assert "error" in result
        assert "500" in result["error"]

    def test_headers_contain_token(self):
        from aden_tools.tools.figma_tool.figma_tool import (
            _FigmaClient,
        )

        client = _FigmaClient("my-secret-token")
        assert (
            client._headers["X-Figma-Token"] == "my-secret-token"
        )

    def test_handle_response_api_error_with_message(self):
        from aden_tools.tools.figma_tool.figma_tool import (
            _FigmaClient,
        )

        client = _FigmaClient("test-token")
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "err": "Invalid parameter"
        }
        result = client._handle_response(mock_resp)
        assert "Invalid parameter" in result["error"]
