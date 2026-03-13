# Figma Tool

Access Figma files, components, comments, and exports via the Figma REST API.

## Setup

1. **Get a Personal Access Token** from Figma:
   - Go to Figma > Settings > Account > Personal access tokens
   - Click "Generate new token"
   - Copy the token

2. **Configure the credential**:
   ```bash
   export FIGMA_ACCESS_TOKEN=figd_your_token_here
   ```

   Or configure via the Hive credential store.

## Tools (11)

### File Inspection

| Tool | Description |
|------|-------------|
| `figma_get_file` | Get a file's metadata and document tree (pages, frames, layers) |
| `figma_get_file_nodes` | Retrieve specific nodes by ID without fetching the entire file |

### Image Export

| Tool | Description |
|------|-------------|
| `figma_export_images` | Export nodes as PNG, SVG, JPG, or PDF with configurable scale |

### Comments

| Tool | Description |
|------|-------------|
| `figma_list_comments` | List all comments on a file |
| `figma_post_comment` | Post a comment (top-level, reply, or anchored to a node) |
| `figma_delete_comment` | Delete a comment by ID |

### Project Browsing

| Tool | Description |
|------|-------------|
| `figma_list_projects` | List all projects in a team |
| `figma_list_project_files` | List all files in a project |

### Components & Styles

| Tool | Description |
|------|-------------|
| `figma_get_components` | Discover all components in a file (design system inventory) |
| `figma_get_styles` | List all styles (colors, text, effects, grids) in a file |

### Version History

| Tool | Description |
|------|-------------|
| `figma_list_versions` | Get saved version history with labels and descriptions |

## Usage Examples

### Inspect a Figma File

```
figma_get_file(file_key="abc123DEF", depth=2)
```

The `file_key` is extracted from the Figma URL:
`https://www.figma.com/design/abc123DEF/My-Design` -> `abc123DEF`

### Export Assets

```
figma_export_images(file_key="abc123DEF", ids="1:2,1:3", format="svg", scale=2.0)
```

Returns temporary download URLs (valid for 30 days).

### Post a Design Review Comment

```
figma_post_comment(
    file_key="abc123DEF",
    message="The spacing here looks off — should be 16px",
    node_id="1:42",
    x=100.0,
    y=200.0,
)
```

### Browse a Team's Projects

```
figma_list_projects(team_id="12345")
figma_list_project_files(project_id="67890")
```

## API Reference

- **Base URL**: `https://api.figma.com/v1`
- **Auth**: `X-Figma-Token` header with personal access token
- **API Docs**: https://developers.figma.com/docs/rest-api/

## Rate Limits

Figma applies rate limits per token:
- **Tier 1** (reads): ~30 requests/minute
- **Tier 2** (writes): ~10 requests/minute
- **Tier 3** (image exports): ~5 requests/minute

The tool returns a clear error when rate-limited.

## Scope & Limitations

- **Read-only for design content** — you cannot create or modify Figma designs via the API
- **Comments are read/write** — you can add and delete comments
- **Exports produce URLs** — not raw binary data; URLs are valid for 30 days
- **No real-time updates** — this is a polling API, not a webhook/websocket connection
- **File size** — very large files may take longer or time out; use `depth` to limit data

## Error Handling

All tools return `{"error": "..."}` on failure:
- `403` — Invalid or expired token
- `404` — File, node, or project not found
- `429` — Rate limit exceeded
- Timeout — Request took too long (30s for most, 60s for exports)
- Network errors — Connection refused, DNS failure, etc.
