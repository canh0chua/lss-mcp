# AI Agent Configuration

Instructions for connecting LSS-MCP to various AI coding assistants.

## Important: Check Your Agent's Documentation First

Before modifying any MCP settings, **always consult the official documentation for your specific AI coding assistant**. MCP configuration formats and procedures vary between agents (Claude Code, Cursor, Windsurf, etc.) and may change over version updates.

The configurations below are examples. Refer to your agent's current documentation for the most accurate setup instructions.

## OpenCode

Add the following to your `opencode.json` or `opencode.jsonc` configuration file:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "local-support-stack": {
      "type": "local",
      "command": ["docker", "exec", "-i", "lss-mcp_support_server", "python", "/app/server.py"],
      "enabled": true
    }
  }
}
```

Restart OpenCode to load the MCP server. All LSS-MCP tools will be available automatically. You can optionally control tool access via the `tools` configuration:

```json
{
  "tools": {
    "local-support-stack_*": true
  }
}
```

Use tools by mentioning them in your prompts, e.g., `use web_search` or `use read_document`.

For more details on MCP server configuration, see the [OpenCode MCP documentation](https://opencode.ai/docs/mcp-servers/).

## Claude Code

```bash
claude mcp add local-support-stack -- docker exec -i lss-mcp_support_server python /app/server.py
```

Then restart your Claude Code session. Use tools: `web_search`, `read_webpage`, `read_document`, `read_code_outline`, `run_command_compressed`, `compress_and_read_image`, `map_repository`, `focused_glob`, `search_codebase`, `safe_read_file`, `get_workspace_info`.

## Cursor IDE

1. Open Cursor Settings (Cmd+,)
2. Search "MCP Server"
3. Click "Add New Server"
4. Configuration:
   - **Name**: Local Support Stack
   - **Command**: `docker`
    - **Arguments**: `exec -i lss-mcp_support_server python /app/server.py`
5. Save and reload Cursor

## Windsurf

1. Open command palette (Cmd+Shift+P)
2. "Windsurf: Add MCP Server"
3. Enter:
   - Name: `local-support-stack`
   -     Command: `docker exec -i lss-mcp_support_server python /app/server.py`
4. Restart Windsurf

## Continue (VS Code Extension)

Add to VS Code settings.json or `.continue/config.json`:

```json
{
  "mcpServers": {
    "local-support-stack": {
      "command": "docker",
        "args": ["exec", "-i", "lss-mcp_support_server", "python", "/app/server.py"]
    }
  }
}
```

## Zed Editor

1. Open Settings (Cmd+,)
2. Search "MCP"
3. Add to `mcp_servers`:
   ```json
   {
     "local-support-stack": {
       "command": "docker",
      "args": ["exec", "-i", "lss-mcp_support_server", "python", "/app/server.py"]
     }
   }
   ```
4. Restart Zed

## Hermes Agent

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  lss-mcp:
    command: "docker"
    args: ["exec", "-i", "lss-mcp_support_server", "python", "/app/server.py"]
    timeout: 120
```

Restart Hermes. All tools auto-register as `mcp_lss-mcp_web_search`, `mcp_lss-mcp_read_webpage`, etc. -- available as first-class tools.

## Generic MCP Clients

For any MCP-compatible client, use this connection command:

```
docker exec -i lss-mcp_support_server python /app/server.py
```

Ensure the client uses stdio transport.

## Understanding Workspace Paths

LSS-MCP maps a host directory (e.g., `/Users/minh/selfhost/`) to `/workspace` inside the container. All file tools accept paths relative to `/workspace`.

To help the AI understand your workspace layout, use the `get_workspace_info` tool:

```
get_workspace_info()
```

This returns:
- `workspace_root`: Container workspace path
- `workspace_host_path`: Host directory mounted
- `workspace_project`: Active project restriction (if any)
- `subdirectories`: List of projects available under workspace

Example usage:

```
get_workspace_info()  # See available projects
read_document("lss-mcp/workspace/test.md")  # Access file in lss-mcp subdirectory
```

If you're working in `/Users/minh/selfhost/project1/`, prefix paths with `project1/`.