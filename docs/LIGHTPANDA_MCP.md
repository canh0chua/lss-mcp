# Lightpanda Native MCP Integration

This guide covers how to enable Lightpanda's native MCP server (LP domain) in your LSS-MCP Docker setup, giving you access to advanced browser automation features alongside your workspace tools.

## Overview

Lightpanda provides a native MCP server built into its browser binary. It exposes powerful LP domain commands:

- `goto` - Navigate to URLs
- `markdown` - Token-efficient page content extraction
- `semantic_tree` - Pruned interactive DOM representation
- `links` - Extract all hyperlinks
- `interactiveElements` - Find clickable/typeable elements
- `structuredData` - Extract JSON-LD, OpenGraph, meta tags
- `evaluate` - Run JavaScript in page context

These complement LSS-MCP's codebase and file tools.

## Prerequisites

LSS-MCP's `docker-compose.yml` already includes a `lightpanda-mcp` service guarded by a Compose profile. You just need to start it with the `--profile` flag.

## Step 1: Enable the Lightpanda MCP profile

Start or restart the stack with the `lightpanda-mcp` profile enabled:

```bash
docker compose --profile lightpanda-mcp up -d
```

This starts the `lightpanda-mcp` container alongside the core services (lightpanda, crw, mcp-server).

To stop it:

```bash
docker compose --profile lightpanda-mcp stop
```

To start it again later without rebuilding:

```bash
docker compose --profile lightpanda-mcp start
```

## Step 2: Configure Your MCP Client

Add the Lightpanda MCP server to your MCP client configuration. The client will launch `docker exec` to attach to the running container's stdio.

### Claude Desktop / Cursor / Windsurf

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

```json
{
  "mcpServers": {
    "lss-mcp": {
      "command": "docker",
      "args": ["exec", "-i", "lss-mcp_support_server", "python", "/app/server.py"]
    },
    "lightpanda": {
      "command": "docker",
      "args": ["exec", "-i", "lss-mcp_lightpanda_mcp", "/bin/lightpanda", "mcp"]
    }
  }
}
```

### Hermes (via skill)

Add both servers to your Hermes MCP configuration (`~/.hermes/config.yaml`):

```yaml
mcp_servers:
  lss-mcp:
    command: "docker"
    args: ["exec", "-i", "lss-mcp_support_server", "python", "/app/server.py"]
  lightpanda:
    command: "docker"
    args: ["exec", "-i", "lss-mcp_lightpanda_mcp", "/bin/lightpanda", "mcp"]
```

### Generic MCP Clients

Use this connection command:

```
docker exec -i lss-mcp_lightpanda_mcp /bin/lightpanda mcp
```

## Step 3: Restart Your MCP Client

After updating the config, restart your MCP client. It should discover tools from both servers:

- LSS-MCP tools: `web_search`, `read_document`, `safe_read_file`, `search_codebase`, etc.
- Lightpanda tools: `goto`, `markdown`, `semantic_tree`, `interactiveElements`, `structuredData`, `links`, `evaluate`

## Usage Examples

### Web page interaction (Lightpanda)

```
goto("https://example.com")
markdown()  # get content
semantic_tree(format="text")  # get interactive structure
interactiveElements()  # list clickable elements
```

### Codebase operations (LSS-MCP)

```
search_codebase("class User")
read_file_skeleton("src/main.py")
focused_glob("**/*.py")
```

You can combine both in a single agent session.

## Troubleshooting

**"Command not found" for lightpanda-mcp**  
Ensure the container is running: `docker ps | grep lss-mcp_lightpanda_mcp`. If not, start it: `docker compose --profile lightpanda-mcp up -d`.

**MCP client fails to connect**  
Check that `docker exec` works manually:  
`docker exec -i lss-mcp_lightpanda_mcp /bin/lightpanda mcp`  
It should output JSON-RPC messages. Press Ctrl+C to exit.

**Container not found**  
Ensure you used `--profile lightpanda-mcp` when starting the stack. Regular `docker compose up -d` does NOT start profile-guarded services.

**Memory errors**  
Both Lightpanda instances (one for CRW, one for MCP) each allocate ~1GB. Ensure your system has enough RAM. Adjust `mem_limit` in `docker-compose.yml` if needed.

**Port conflicts**  
Lightpanda MCP uses stdio only; no ports are exposed. Ensure no other service uses container name `lss-mcp_lightpanda_mcp`.

## Architecture Notes

- The `lightpanda` service (CDP mode) is used by CRW for web scraping and search.
- The `lightpanda-mcp` service (MCP mode) exposes LP domain tools directly to your AI assistant.
- They run independently; you can disable one without affecting the other.
- No code changes to LSS-MCP are required.
- The `lightpanda-mcp` service is disabled by default; enable with `--profile lightpanda-mcp`.

## Uninstall

To remove Lightpanda MCP:

1. Stop the service: `docker compose --profile lightpanda-mcp stop`
2. Remove the `lightpanda-mcp` entry from your MCP client config
3. (Optional) Remove the profile guard from `docker-compose.yml` if you want to permanently disable it

The original `lightpanda` service (for CRW) remains untouched.
