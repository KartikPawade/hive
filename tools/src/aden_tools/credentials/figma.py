"""
Figma tool credentials.

Contains credentials for Figma REST API access.
Requires a personal access token from Figma.
"""

from .base import CredentialSpec

_FIGMA_TOOLS = [
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

FIGMA_CREDENTIALS = {
    "figma": CredentialSpec(
        env_var="FIGMA_ACCESS_TOKEN",
        tools=_FIGMA_TOOLS,
        required=True,
        startup_required=False,
        help_url="https://www.figma.com/developers/api#access-tokens",
        description="Figma personal access token for API access",
        direct_api_key_supported=True,
        api_key_instructions="""To get a Figma personal access token:
1. Log in to Figma at https://www.figma.com
2. Go to Settings (click your avatar > Settings)
3. Scroll to 'Personal access tokens'
4. Click 'Generate new token', give it a description
5. Copy the token (it won't be shown again)
6. Set the environment variable:
   export FIGMA_ACCESS_TOKEN=your-token-here""",
        health_check_endpoint="https://api.figma.com/v1/me",
        credential_id="figma",
        credential_key="api_key",
    ),
}
