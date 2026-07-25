# LSS-MCP `web_search` Tool

The `web_search` tool provides full-text search capabilities via the 4get privacy-respecting proxy. It supports multiple search types, backend scrapers, filters, and pagination.

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | (required) | Search query (max 500 characters) |
| `type` | string | `"web"` | Search type: `web`, `image`, `video`, `news`, `music` |
| `limit` | int | `5` | Number of results to return (1-20) |
| `npt` | string | `""` | Next page token for pagination (from previous response) |
| `scraper` | string | `""` | Backend scraper: `ddg`, `brave`, `yandex`, `google`, `qwant`, `startpage`, etc. |
| `nsfw` | bool | `false` | Include explicit content (web only) |
| `country` | string | `""` | Two-letter country code (e.g., `us`, `ca`, `uk`, `de`) |
| `lang` | string | `""` | Language code (e.g., `en`, `fr`, `de`, `es`) |
| `time_min` | int | `0` | Unix timestamp for earliest result (date range filter) |
| `time_max` | int | `0` | Unix timestamp for latest result (date range filter) |

## Response Format

All responses are JSON strings with the following structure:

```json
{
  "results": [
    { "title": "...", "url": "...", "snippet": "..." }
  ],
  "npt": "ddg15.abc123..."   // optional pagination token
}
```

Field variations by `type`:

- **web**: `title`, `url`, `snippet`
- **image**: `title`, `url` (full size), `thumbnail`
- **video**: `title`, `url`, `description`, `duration`, `views`
- **news**: `title`, `url`, `description`, `date` (Unix timestamp), `source`
- **music**: `title`, `artist`, `album`, `duration`

The `npt` field appears when more results are available. Use it as the `npt` parameter to fetch the next page.

## Examples

### Basic web search
```python
web_search("hello world")
```

### Image search with limit
```python
web_search("cute cats", type="image", limit=10)
```

### Use a specific scraper
```python
web_search("python tutorial", scraper="brave")
```

### Filter by country and language
```python
web_search("news", type="news", country="us", lang="en")
```

### Paginate through results
```python
# First page
page1 = json.loads(web_search("machine learning", limit=5))
npt = page1.get("npt")

# Next page (if npt exists)
if npt:
    page2 = json.loads(web_search("machine learning", limit=5, npt=npt))
```

### Date range filtering (e.g., last 30 days)
```python
import time
thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
web_search("AI developments", time_min=thirty_days_ago)
```

### Combine filters
```python
web_search("landscape photography", type="image", scraper="yandex", nsfw=False, limit=5)
```

## Notes

- Empty queries are rejected by 4get and will return an error.
- Invalid `type` values return an error message.
- The `nsfw` parameter only affects web search; other types ignore it.
- Scraper availability depends on the 4get instance configuration.
- Rate limits are enforced by the 4get server; respect the terms of use.

## Migration from Old Versions

Previously, LSS-MCP used `web_search` (SearXNG) and `web_search_crw` (CRW). Both have been replaced by this single unified tool using 4get. All MCP clients should update to use the new parameter signature.

Old code:
```python
# Before
web_search("query")  # returned only web results from SearXNG
```

New code:
```python
# After (equivalent)
web_search("query", type="web")
```
