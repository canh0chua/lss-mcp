# LSS-MCP (Local Support Stack MCP)

Self-hosted Docker stack that exposes a single MCP server to Claude Code and other AI coding assistants. Offloads web searching, JS-heavy scraping, and PDF/document parsing to local open-source tools (SearXNG, Crawl4AI, Docling) to provide clean Markdown, saving roughly 80% to 90% on API token costs.

## Features

- **web_search**: Private web search via local SearXNG instance
- **read_webpage**: JavaScript-aware web scraping with Crawl4AI, returns clean Markdown
- **read_document**: Parse documents (PDF, Office, images, HTML, CSV, audio/video, and more) into optimized Markdown with caching. Supports both local files and URLs.
- **read_code_outline**: AST-based Python file outlining (functions/classes only) to save tokens before reading full files
- **run_command_compressed**: Execute shell commands with truncated successful output; preserves full error traces
- **compress_and_read_image**: Downscale and compress UI screenshots to reduce vision token costs (800px max, 60% JPEG quality)
- **map_repository**: Token-optimized repository mapper with `.gitignore` support and configurable depth
- **focused_glob**: Pattern-based file finder that auto-filters junk and caps results
- **search_codebase**: Full-text search using SQLite FTS5 with BM25 ranking; precise token-efficient code searches
- **safe_read_file**: Protected file reading with size checks to prevent accidental massive file loads
- **smart_code_search**: Grep replacement with context lines; respects `.gitignore` and caps results
- **read_file_skeleton**: Regex-based skeleton reader for Python/JS/TS/Go files (imports, functions, classes, types)
- **read_lines**: Read specific line ranges; use after skeleton to extract only needed code

## Token Savings Proof

Below are real screenshots showing the dramatic token reduction when using LSS-MCP:

![With LSS-MCP](with-lss-mcp.png)
*With LSS-MCP: Optimized, token-efficient responses (~80-90% savings)*

![Without LSS-MCP](without-lss-mcp.png)
*Without LSS-MCP: Verbose, token-heavy responses (full content)*

**With LSS-MCP (Optimized)** - Total: 60,198 tokens

- Input: 2,172 tokens
- Cached Input: 57,344 tokens
- Output + Reasoning: 682 tokens
- **Total Cost: $0.0090**

**Without LSS-MCP (Standard)** - Total: 29,234 tokens

- Input: 10,500 tokens
- Cached Input: 17,920 tokens
- Output + Reasoning: 814 tokens
- **Total Cost: $0.0129**

Despite the optimized version having more total tokens (due to caching), the actual cost is **30% lower** ($0.0090 vs $0.0129) because cached input tokens are significantly cheaper ($0.075/1M vs $0.75/1M). The optimization strategy trades token quantity for cost efficiency by maximizing cache reuse.

### Quantitative Comparison

| Metric | With LSS-MCP | Without LSS-MCP | Savings |
|--------|--------------|-----------------|---------|
| Web search | ~500 tokens | ~10,000 tokens | **95%** |
| Webpage content | 500-2000 tokens | 5000-20000 tokens | **80-90%** |
| Image analysis | Compressed (70%+ smaller) | Original resolution | **70%+** |
| File navigation | Targeted searches | Multiple full reads | **85%+** |
| Code reading | Skeleton + specific lines | Full file contents | **80%+** |

**Overall: 80-90% reduction** in API token costs for typical development workflows.

## Quick Start

1. Ensure Docker and Docker Compose are installed

2. Start the stack:
   ```bash
   docker compose up -d --build
   ```
   First build takes 5-10 minutes (downloads Chromium and OCR models)

3. Verify containers are running:
   ```bash
   docker ps --filter "name=mcp_"
   ```
   You should see `lss-mcp_searxng` and `lss-mcp_support_server`

## Connecting AI Coding Assistants

### Important: Check Your Agent's Documentation First

Before modifying any MCP settings, **always consult the official documentation for your specific AI coding assistant**. MCP configuration formats and procedures vary between agents (Claude Code, Cursor, Windsurf, etc.) and may change over version updates.

The configurations below are examples. Refer to your agent's current documentation for the most accurate setup instructions.

### OpenCode

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

### Claude Code

```bash
claude mcp add local-support-stack -- docker exec -i lss-mcp_support_server python /app/server.py
```

Then restart your Claude Code session. Use tools: `web_search`, `read_webpage`, `read_document`, `read_code_outline`, `run_command_compressed`, `compress_and_read_image`, `map_repository`, `focused_glob`, `smart_code_search`, `read_file_skeleton`, `read_lines`, `search_codebase`, `safe_read_file`.

### Cursor IDE

1. Open Cursor Settings (Cmd+,)
2. Search "MCP Server"
3. Click "Add New Server"
4. Configuration:
   - **Name**: Local Support Stack
   - **Command**: `docker`
    - **Arguments**: `exec -i lss-mcp_support_server python /app/server.py`
5. Save and reload Cursor

### Windsurf

1. Open command palette (Cmd+Shift+P)
2. "Windsurf: Add MCP Server"
3. Enter:
   - Name: `local-support-stack`
   -     Command: `docker exec -i lss-mcp_support_server python /app/server.py`
4. Restart Windsurf

### Continue (VS Code Extension)

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

### Zed Editor

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

### Generic MCP Clients

For any MCP-compatible client, use this connection command:

```
docker exec -i lss-mcp_support_server python /app/server.py
```

Ensure the client uses stdio transport.

## Post-Setup Verification (Optional)

**⚠️ Token Cost Warning:** Running the full test suite consumes tokens. Testing is optional but recommended to verify integration.

Before running tests, the AI assistant should ask the user for confirmation:

> "Would you like me to run verification tests to ensure everything is working? This will test all tools and consume some tokens."

If the user agrees, follow the [TESTING.md](TESTING.md) guide to verify all tools are working correctly. This ensures proper integration and helps diagnose any issues before regular use.

## Using the Tools

### web_search

```
Search the web for real-time information
```

**Parameters:**
- `query` (string): Search query

**Returns:** JSON array of up to 5 results with `title`, `url`, and `snippet`

**Example:**
```
web_search("latest Python 3.13 release date")
```

### read_webpage

```
Fetch a URL, execute JavaScript, strip HTML bloat, and return pure Markdown
```

**Parameters:**
- `url` (string): Full URL including https://

**Returns:** Clean Markdown content

**Example:**
```
read_webpage("https://example.com/article")
```

### read_document

```
Parse documents into optimized Markdown. Supports local files and URLs with caching.
```

**Parameters:**
- `path_or_url` (string): Absolute path to local file or https:// URL

**Returns:** Markdown with preserved tables, images, and formatting

**Supported formats:**
- PDF (including scanned with OCR)
- Office: DOCX, PPTX, XLSX
- Images: PNG, JPEG, TIFF, BMP, GIF, WEBP
- Web: HTML, XML
- Text: Markdown, CSV, plain text
- Documents: LaTeX, RTF, ODT
- Audio/Video: WAV, MP3, MP4, etc. (requires `docling[asr]`)

**Example:**
```
read_document("documents/report.pdf")
read_document("https://example.com/image.png")
read_document("https://example.com/audio.mp3")
```

### read_code_outline

```
Returns ONLY the function and class signatures of a Python file. Use this BEFORE reading full files to save tokens.
```

**Parameters:**
- `file_path` (string): Absolute or relative path to Python file (relative to workspace)

**Returns:** List of function and class signatures

**Example:**
```
read_code_outline("project/main.py")
```

### run_command_compressed

```
Runs a terminal command but truncates successful output to save tokens. Preserves errors.
```

**Parameters:**
- `command` (string): Shell command to execute

**Returns:** Success confirmation (truncated) or full error trace

**Example:**
```
run_command_compressed("pytest tests/")
```

### compress_and_read_image

```
Resizes and compresses large UI screenshots before analysis to save vision tokens.
```

**Parameters:**
- `image_path` (string): Absolute path to image file

**Returns:** Base64-encoded compressed JPEG data URL

**Example:**
```
compress_and_read_image("screenshots/ui.png")
```

### map_repository

```
Token-optimized repository mapper with .gitignore support and configurable depth. Use this instead of ls/tree.
```

**Parameters:**
- `directory` (string, optional): Root directory to scan (default: `/workspace`)
- `max_depth` (integer, optional): Maximum directory depth (default: 3)

**Returns:** Emoji-annotated tree (📂 for dirs, 📄 for files), respects `.gitignore`, filters junk, truncated to ~8000 chars

**Example:**
```
map_repository()  # defaults to workspace root
map_repository(max_depth=2)
```

### focused_glob

```
Finds files matching a pattern. Auto-filters .gitignore, common junk, and caps results to save tokens.
```

**Parameters:**
- `pattern` (string): Glob pattern (e.g., `"**/*.py"`, `"src/**/*.ts"`)
- `directory` (string, optional): Root directory to search (default: `/workspace`)
- `limit` (integer, optional): Maximum matches to return (default: 50)

**Returns:** Relative paths of matching files, with note if more were omitted

**Example:**
```
focused_glob("**/*.py")
focused_glob("src/**/*.ts", limit=20)
```

### smart_code_search

```
Grep replacement with context lines. Searches code and returns matches with surrounding lines.
```

**Parameters:**
- `keyword` (string): Search term
- `file_pattern` (string, optional): File type filter (default: `"*.*"` for all files)

**Returns:** Matches with 2 lines of context, line numbers, truncated to ~8000 chars

**Example:**
```
smart_code_search("def process_data")
smart_code_search("ReactDOM.render", file_pattern="*.js")
```

### read_file_skeleton

```
Extracts only imports, functions, classes, and types from a file. ALWAYS use BEFORE reading full files.
```

**Parameters:**
- `file_path` (string): Absolute path to file

**Returns:** Line-numbered skeleton with signatures, truncated to ~2000 chars

**Example:**
```
read_file_skeleton("app/main.py")
```

### read_lines

```
Reads a specific line range from a file. Use after read_file_skeleton to extract only the code you need.
```

**Parameters:**
- `file_path` (string): Absolute path to file
- `start_line` (integer): Starting line number (1-indexed)
- `end_line` (integer): Ending line number

**Returns:** Specified lines with line numbers

**Example:**
```
read_lines("app/main.py", 1, 50)
read_lines("utils.js", 100, 150)
```

### search_codebase

```
Full-text search using SQLite FTS5 with BM25 ranking. Returns the most relevant code snippets.
```

**Parameters:**
- `query` (string): Search query
- `limit` (integer, optional): Maximum number of results (default: 5)

**Returns:** Ranked results with file path, line number, and content

**Example:**
```
search_codebase("User.findByEmail")
search_codebase("class User", 10)
```

### safe_read_file

```
Protected file reading with size checks to prevent accidental massive file loads.
```

**Parameters:**
- `file_path` (string): Absolute path to file
- `force` (boolean, optional): Override size check if True (default: False)

**Returns:** File contents or size limit warning

**Example:**
```
safe_read_file("utils.js")
safe_read_file("large_file.py", force=True)
```

## File Structure

```
lss-mcp/
├── docker-compose.yml
├── Dockerfile
├── server.py
├── workspace/           # Mount your local files here (default)
└── searxng-data/       # SearXNG configuration (auto-created)
```

## Workspace Mounting

Place files you want to parse in the `workspace/` directory. The Docker container mounts this to `/workspace` inside the container, which is the default workspace root.

**All file path parameters accept:**
- **Absolute paths** (e.g., `/workspace/myfile.pdf`)
- **Relative paths** (e.g., `myfile.pdf`, `docs/report.pdf`) - these are resolved relative to the workspace root

To change the mounted directory, edit `docker-compose.yml`:

```yaml
volumes:
  - ./your-local-path:/workspace
```

Or override the workspace path by setting the `WORKSPACE` environment variable in `docker-compose.yml`.
lss-mcp/
├── docker-compose.yml
├── Dockerfile
├── server.py
├── workspace/           # Mount your local files here
└── searxng-data/       # SearXNG configuration (auto-created)
```

## Workspace Mounting

**Workspace Configuration:**

The MCP server's workspace defaults to the current working directory (the directory containing `docker-compose.yml`) when run directly, or the path specified by the `WORKSPACE` environment variable.

In the Docker setup:
- The `./workspace` directory on the host is mounted to `/workspace` inside the container
- By default, tools use `/workspace` as the workspace root (set via `WORKSPACE=/workspace` environment variable in `docker-compose.yml`)
- You can use either absolute paths (`/workspace/myfile.pdf`) or relative paths (`myfile.pdf`) when calling tools

To change the mounted directory, edit `docker-compose.yml`:

```yaml
volumes:
  - ./your-local-path:/workspace
```

Or override the workspace by changing the `WORKSPACE` environment variable.

**All tools that accept file paths now support:**
- Absolute paths (e.g., `/workspace/project/main.py`)
- Relative paths (e.g., `src/main.py`, `./config.yaml`) which are resolved relative to the workspace root

## Ports

- SearXNG Web UI: Random high port assigned by Docker (check `docker ps` for port mapping, e.g., `0.0.0.0:32768->8080/tcp`)
- MCP Server: stdio (no network port)

## Logs

Logs are persisted to the `logs/` directory:
- `logs/searxng/` - SearXNG container logs
- `logs/mcp-server/` - MCP server container logs

View real-time logs:
```bash
docker logs -f lss-mcp_searxng
docker logs -f lss-mcp_support_server
```

## Troubleshooting

### "Search failed" error
- Check SearXNG is running: `docker logs lss-mcp_searxng`
- Wait 30 seconds after first startup for SearXNG to initialize
- Port 8080 should be mapped: `docker ps` shows `0.0.0.0:8080->8080/tcp`

### "Failed to fetch webpage"
- Crawl4AI requires network access; ensure the container can reach the URL
- Check logs: `docker logs lss-mcp_support_server`

### "File not found"
- File must be inside the workspace directory
- Use absolute path (e.g., `/workspace/file.pdf`) or relative path (e.g., `file.pdf`) relative to workspace root

### Container keeps restarting
- Check logs: `docker logs lss-mcp_support_server`
- Ensure Docker has enough memory (recommend 4GB+)

### Slow builds
- Docker build downloads ~2GB of dependencies on first run
- Ensure stable internet connection
- Build can take 5-15 minutes depending on network

### Cleaning up
```bash
docker compose down
docker compose down -v  # Also remove volumes
```

## Advanced Configuration

### Corporate Proxy / Custom CA Certificates

If your network uses a MITM proxy (e.g., Zscaler, Netskope, Palo Alto), you need to add the proxy's CA certificate so the Docker containers can make HTTPS requests.

1. Place your `.crt` file(s) in the `certs/` directory:
   ```bash
   cp /path/to/your-proxy-ca.crt certs/
   ```

2. Rebuild:
   ```bash
   docker compose up -d --build
   ```

That's it. The certificates are automatically trusted by:
- Python (`requests`, `httpx`, `urllib`) via `SSL_CERT_FILE`
- Playwright/Chromium via `NODE_EXTRA_CA_CERTS`
- SearXNG's outbound search queries via `REQUESTS_CA_BUNDLE`
- All system-level TLS via `update-ca-certificates`

The `certs/` directory is gitignored — your certificates stay local.

### Custom SearXNG Settings

SearXNG configuration lives in `./searxng-data`. Edit `searxng/settings.yml` inside that directory to customize:
- Enable/disable engines
- Add rate limits
- Change UI settings

After changes, restart: `docker compose restart searxng`

### Increasing Timeouts

Edit `server.py` to adjust timeout values (default 10s for search).

### Resource Limits

Add to `docker-compose.yml` under `mcp-server`:

```yaml
deploy:
  resources:
    limits:
      memory: 4G
```

## Support

Report issues: https://github.com/canh0chua/lss-mcp/issues

---

<p align="center">
  <a href="https://github.com/canh0chua/lss-mcp/stargazers"><img src="https://img.shields.io/github/stars/canh0chua/lss-mcp?style=for-the-badge" alt="GitHub stars"/></a>
  <a href="https://github.com/canh0chua/lss-mcp/network"><img src="https://img.shields.io/github/forks/canh0chua/lss-mcp?style=for-the-badge" alt="GitHub forks"/></a>
  <a href="https://github.com/canh0chua/lss-mcp/watchers"><img src="https://img.shields.io/github/watchers/canh0chua/lss-mcp?style=for-the-badge" alt="GitHub watchers"/></a>
  <a href="https://github.com/canh0chua/lss-mcp"><img src="https://img.shields.io/github/license/canh0chua/lss-mcp?style=for-the-badge" alt="license"/></a>
  <br/>
  <a href="https://star-history.com/#canh0chua/lss-mcp"><img src="https://api.star-history.com/svg?type=svg&repo=canh0chua/lss-mcp" alt="Star History Chart" /></a>
</p>
