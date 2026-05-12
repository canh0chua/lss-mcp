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
- SearXNG's outbound search queries via `REQUESTS_CA_BUNDLE`
- All system-level TLS via `update-ca-certificates`

The `certs/` directory is gitignored — your certificates stay local.

## Custom SearXNG Settings

SearXNG configuration lives in `./searxng-data`. Edit `searxng/settings.yml` inside that directory to customize:
- Enable/disable engines
- Add rate limits
- Change UI settings

After changes, restart: `docker compose restart searxng`

### Bot Detection

SearXNG includes bot detection that may block automated requests. Key configurations:

```yaml
# searxng-data/settings.yml
botdetection:
  # Trusted proxies (needed for Docker networking)
  trusted_proxies:
    - '172.16.0.0/12'   # Docker networks
    - '192.168.0.0/16'  # Private networks
    - '10.0.0.0/8'      # Private networks

  # IP lists (allow/block specific IPs)
  pass_ip:
    - '192.168.0.0/16'
  block_ip: []

  # Rate limiting (requires Valkey/Redis)
  ip_limit:
    link_token: false
```

**Note:** Rate limiting (`ip_limit`) requires a Valkey/Redis container. For local development, it's disabled by default.

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
- `logs/searxng/` - SearXNG container logs
- `logs/mcp-server/` - MCP server container logs

View real-time logs:
```bash
docker logs -f lss-mcp_searxng
docker logs -f lss-mcp_support_server
```