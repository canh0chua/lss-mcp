# LSS-MCP Testing Guide (Optional)

**⚠️ Token Cost Warning:** Running these tests consumes API tokens. Testing is recommended for initial verification but can be skipped to save costs. Only run tests if you want to confirm all tools are working properly.

After completing the setup and configuring your AI assistant with the MCP server, use this guide (optionally) to verify everything is working correctly.

## Prerequisites

1. Docker containers are running:
   ```bash
   docker ps --filter "name=mcp_"
   ```
   You should see both `lss-mcp_searxng` and `lss-mcp_support_server` with healthy status.

2. Your AI assistant has the MCP server configured (see README.md for agent-specific instructions).

   3. The assistant has access to the following tools:
      - `web_search`
      - `read_webpage`
      - `read_document`
      - `read_code_outline`
      - `run_command_compressed`
      - `compress_and_read_image`
      - `map_repository`
      - `focused_glob`
      - `search_codebase`
      - `safe_read_file`

## Quick Verification

Ask your AI assistant to run these simple tests:

### 1. Web Search Test

```
Use the web_search tool to search for "Python 3.13 release date"
```

Expected result: A JSON array with up to 5 search results containing `title`, `url`, and `snippet` fields.

### 2. Webpage Reading Test

```
Use the read_webpage tool to fetch "https://example.com"
```

Expected result: Clean Markdown content from the example.com homepage.

### 3. Local Document Test

First, place a test file in the `workspace/` directory:

```bash
echo "# Test Document\n\nThis is a **markdown** test file." > workspace/test.md
```

Then ask:

```
Use the read_document tool to read "/workspace/test.md"
```

Expected result: The Markdown content of the file.

## Comprehensive Testing

### Test File Setup

Create sample files in the `workspace/` directory:

```bash
# Create a sample PDF (requires a simple method)
# You can use any PDF file you have, or create from markdown:
mkdir -p workspace
echo "# Sample PDF\n\nThis document tests PDF parsing." > workspace/sample.md
# Convert to PDF using LibreOffice or other tool if available
# For testing, any PDF file will work:
cp /path/to/any.pdf workspace/test.pdf 2>/dev/null || echo "Place any PDF file at workspace/test.pdf"

# Create a sample code file
cat > workspace/sample_code.py << 'EOF'
def hello_world():
    """A simple function."""
    print("Hello, World!")

class TestClass:
    def method_one(self):
        return "method one"
EOF
```

### Full Tool Test Sequence

Run these commands through your AI assistant:

1. **Search for recent news:**
   ```
   web_search("latest OpenAI GPT-4 announcements")
   ```

2. **Fetch a JavaScript-heavy site:**
   ```
   read_webpage("https://news.ycombinator.com")
   ```

3. **Parse a local PDF** (if you placed one):
   ```
   read_document("/workspace/test.pdf")
   ```

4. **Outline a Python file:**
   ```
   read_code_outline("/workspace/sample_code.py")
   ```

5. **Search the codebase:**
   ```
   search_codebase("hello_world")
   ```

  6. **Map repository:**
     ```
     map_repository("/workspace")
     ```

  7. **Find files with focused glob:**
     ```
     focused_glob("**/*.py", "/workspace")
     ```

  8. **Search code with context:**
     ```
     smart_code_search("def main")
     ```

  9. **Read file skeleton:**
     ```
     read_file_skeleton("/workspace/sample_code.py")
     ```

 10. **Read specific lines:**
     ```
     read_lines("/workspace/sample_code.py", 1, 10)
     ```

 7. **Run a safe command:**
    ```
    run_command_compressed("ls -la /workspace")
    ```

 8. **Read a large file safely:**
    ```
    safe_read_file("/workspace/sample_code.py")
    ```

 9. **Test image compression** (if you have an image file):
    ```
    compress_and_read_image("/workspace/test-image.png")
    ```

## Troubleshooting

### "SearXNG healthcheck failed"

- Wait 30-60 seconds after first startup for SearXNG to initialize
- Check logs: `docker logs lss-mcp_searxng`
- Verify health endpoint: `curl http://localhost:8080/healthz` from host

### "Search failed" error

- Ensure SearXNG is running: `docker ps | grep lss-mcp_searxng`
- Check that the container is healthy: `docker inspect lss-mcp_searxng | grep -A 5 Health`
- Restart if needed: `docker compose restart searxng`

### "Failed to fetch webpage"

- Crawl4AI needs network access; verify container can reach the URL
- Check mcp-server logs: `docker logs lss-mcp_support_server`
- The container uses `network_mode: service:searxng`, so it shares network namespace

### "File not found"

- Files must be inside the mounted `workspace/` directory
- Use absolute paths starting with `/workspace/`
- Verify mount is working: `docker exec lss-mcp_support_server ls /workspace`

### Container not starting

- Check resource requirements (recommend 4GB+ memory)
- View logs: `docker logs lss-mcp_support_server`
- Rebuild: `docker compose up -d --build`

## Expected Performance

- `web_search`: ~1-3 seconds (returns compact JSON)
- `read_webpage`: 2-10 seconds depending on page complexity
- `read_document`: 1-5 seconds for typical documents
- `read_code_outline`: <1 second for typical Python files
- `run_command_compressed`: varies by command (max 60s timeout)
- `compress_and_read_image`: 1-3 seconds for typical images
- `get_repo_map`: <1 second for small repos, up to a few seconds for larger ones
- `search_codebase`: <1 second after initial indexing
- `safe_read_file`: <1 second for files up to 30KB

## Success Criteria

All tests should return valid data without errors:
- ✅ Web search returns JSON array with results
- ✅ Webpage reading returns readable Markdown
- ✅ Local document parsing works for your file types
- ✅ Code outline shows function/class signatures
- ✅ Codebase search returns matching snippets
- ✅ Commands execute and return truncated output on success
- ✅ Image compression returns base64-encoded JPEG
- ✅ Repo map shows directory structure
- ✅ Large files are blocked unless forced

If any tool fails, refer to the Troubleshooting section or check the logs for detailed error messages.
