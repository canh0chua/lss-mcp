# Troubleshooting

Common issues and solutions for LSS-MCP.

## "Search failed" error

- Check SearXNG is running: `docker logs lss-mcp_searxng`
- Wait 30 seconds after first startup for SearXNG to initialize
- Port 8080 should be mapped: `docker ps` shows `0.0.0.0:8080->8080/tcp`

## "Failed to fetch webpage"

- Crawl4AI requires network access; ensure the container can reach the URL
- Check logs: `docker logs lss-mcp_support_server`

## "File not found"

- File must be inside the workspace directory
- Use absolute path (e.g., `/workspace/file.pdf`) or relative path (e.g., `file.pdf`) relative to workspace root
- Ensure `WORKSPACE_PROJECT` in `.env` matches your project folder name

## "Access denied" error

- This is expected behavior - LSS-MCP restricts file access to `/workspace/{WORKSPACE_PROJECT}` for security
- Update `WORKSPACE_PROJECT` in `.env` to point to the correct project folder
- Run `docker compose up -d` to apply changes

## "search_codebase" returns empty or FTS5 error

- FTS5 search index is built on first use - run a few searches to initialize
- Index is per-project and stored in container memory
- For large codebases, consider using `smart_code_search` instead

## Container keeps restarting

- Check logs: `docker logs lss-mcp_support_server`
- Ensure Docker has enough memory (recommend 4GB+)

## Slow builds

- Docker build downloads ~2GB of dependencies on first run
- Ensure stable internet connection
- Build can take 5-15 minutes depending on network

## Cleaning up

```bash
docker compose down
docker compose down -v  # Also remove volumes
```