# Advanced Configuration

Advanced settings and customization options for LSS-MCP.

## Corporate Proxy / Custom CA Certificates

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
- 4get adapter's outbound search queries via `REQUESTS_CA_BUNDLE`
- All system-level TLS via `update-ca-certificates`

The `certs/` directory is gitignored — your certificates stay local.

## Search Backend (SearXNG-to-4get Adapter)

The search adapter runs inside the `mcp-server` container and translates SearXNG-compatible API requests to the 4get search backend. No separate SearXNG container is needed.

If SearXNG is needed as an emergency fallback, it is available commented out in `docker-compose.yml` on port 3005. To start it:
```bash
docker compose --profile fallback up -d searxng
```

After changes, restart: `docker compose restart mcp-server`

## Increasing Timeouts

Edit `server.py` to adjust timeout values (default 10s for search).

## Resource Limits

Add to `docker-compose.yml` under `mcp-server`:

```yaml
deploy:
  resources:
    limits:
      memory: 4G
```

## Logs

Logs are persisted to the `logs/` directory:
- `logs/mcp-server/` - MCP server container logs

View real-time logs:
```bash
docker logs -f lss-mcp_support_server
```