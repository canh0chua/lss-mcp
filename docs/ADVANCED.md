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
- All system-level TLS via `update-ca-certificates`

The `certs/` directory is gitignored — your certificates stay local.

## Search Backend (CRW Scrapers)

The `web_search` tool uses direct CRW-based scrapers for full-text search capabilities. This architecture is lightweight and reliable, avoiding the CAPTCHA blocks and anti-bot failures that traditional search aggregators frequently encounter.

The search adapter runs inside the `mcp-server` container and executes queries directly through various backend engines (ddg, brave, yandex, google, qwant, startpage, etc.) via the CRW infrastructure.

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