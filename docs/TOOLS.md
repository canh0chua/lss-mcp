# Tool Reference

Detailed documentation for all LSS-MCP tools.

## web_search

Search the web using 4get (privacy-respecting proxy). Returns JSON results.

**Parameters:**
- `query` (string): Search query (max 500 characters)
- `type` (string): Search type: `web`, `image`, `video`, `news`, `music` (default: `web`)
- `limit` (int): Number of results to return (1-20, default: 10)
- `npt` (string): Next page token for pagination (from previous response, default: "")
- `scraper` (string): Backend scraper (e.g., `ddg`, `brave`, `yandex`, `google`, `qwant`, `startpage`, default: "")
- `nsfw` (bool): Include explicit content (web only, default: false)
- `country` (string): Two-letter country code (e.g., `us`, `ca`, `uk`, `de`, default: "")
- `lang` (string): Language code (e.g., `en`, `fr`, `de`, `es`, default: "")
- `time_min` (int): Unix timestamp for earliest result (date range filter, default: 0)
- `time_max` (int): Unix timestamp for latest result (date range filter, default: 0)

**Returns:** JSON string with results and optional pagination token.

Response format varies by `type`:

- **web**: `{ "results": [ { "title": "...", "url": "...", "snippet": "..." } ], "npt": "..." }`
- **image**: `{ "results": [ { "title": "...", "url": "..." (full size), "thumbnail": "..." } ], "npt": "..." }`
- **video**: `{ "results": [ { "title": "...", "url": "...", "description": "...", "duration": "...", "views": "..." } ], "npt": "..." }`
- **news**: `{ "results": [ { "title": "...", "url": "...", "description": "...", "date": "..." (Unix timestamp), "source": "..." } ], "npt": "..." }`
- **music**: `{ "results": [ { "title": "...", "artist": "...", "album": "...", "duration": "..." } ], "npt": "..." }`

**Example:**
```
web_search("hello world", type="web", limit=3, scraper="brave", country="us")
```

## read_webpage

Fetch a URL, execute JavaScript, strip HTML bloat, and return pure Markdown

**Parameters:**
- `url` (string): Full URL including https://

**Returns:** Clean Markdown content

**Example:**
```
read_webpage("https://example.com/article")
```

## read_document

Parse documents into optimized Markdown. Supports local files and URLs with caching.

**Parameters:**
- `path_or_url` (string): Absolute path to local file or https:// URL

**Returns:** Markdown with preserved tables, images, and formatting

**Supported formats:**
- PDF (text + scanned via pdf-inspector + pytesseract OCR)
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

## read_code_outline

Returns ONLY the function and class signatures of a Python file. Use this BEFORE reading full files to save tokens.

**Parameters:**
- `file_path` (string): Absolute or relative path to Python file (relative to workspace)

**Returns:** List of function and class signatures

**Example:**
```
read_code_outline("project/main.py")
```

## run_command_compressed

Runs a terminal command but truncates successful output to save tokens. Preserves errors.

**Parameters:**
- `command` (string): Shell command to execute

**Returns:** Success confirmation (truncated) or full error trace

**Example:**
```
run_command_compressed("pytest tests/")
```

## compress_and_read_image

Resizes and compresses large UI screenshots before analysis to save vision tokens.

**Parameters:**
- `image_path` (string): Absolute path to image file

**Returns:** Base64-encoded compressed JPEG data URL

**Example:**
```
compress_and_read_image("screenshots/ui.png")
```

## map_repository

Token-optimized repository mapper with .gitignore support and configurable depth. Use this instead of ls/tree.

**Parameters:**
- `directory` (string, optional): Root directory to scan (default: `/workspace`)
- `max_depth` (integer, optional): Maximum directory depth (default: 3)

**Returns:** Emoji-annotated tree (📂 for dirs, 📄 for files), respects `.gitignore`, filters junk, truncated to ~8000 chars

**Example:**
```
map_repository()  # defaults to workspace root
map_repository(max_depth=2)
```

## focused_glob

Finds files matching a pattern. Auto-filters .gitignore, common junk, and caps results to save tokens.

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

## smart_code_search

Grep replacement with context lines. Searches code and returns matches with surrounding lines.

**Parameters:**
- `keyword` (string): Search term
- `file_pattern` (string, optional): File type filter (default: `"*.*"` for all files)

**Returns:** Matches with 2 lines of context, line numbers, truncated to ~8000 chars

**Example:**
```
smart_code_search("def process_data")
smart_code_search("ReactDOM.render", file_pattern="*.js")
```

## read_file_skeleton

Extracts only imports, functions, classes, and types from a file. ALWAYS use BEFORE reading full files.

**Parameters:**
- `file_path` (string): Absolute path to file

**Returns:** Line-numbered skeleton with signatures, truncated to ~2000 chars

**Example:**
```
read_file_skeleton("app/main.py")
```

## read_lines

Reads a specific line range from a file. Use after read_file_skeleton to extract only the code you need.

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

## search_codebase

Full-text search using SQLite FTS5 with BM25 ranking. Returns the most relevant code snippets.

**Parameters:**
- `query` (string): Search query
- `limit` (integer, optional): Maximum number of results (default: 10)

**Returns:** Ranked results with file path, line number, and content

**Example:**
```
search_codebase("User.findByEmail")
search_codebase("class User", 10)
```

## safe_read_file

Protected file reading with size checks to prevent accidental massive file loads.

**Parameters:**
- `file_path` (string): Absolute path to file
- `force` (boolean, optional): Override size check if True (default: False)

**Returns:** File contents or size limit warning

**Example:**
```
safe_read_file("utils.js")
safe_read_file("large_file.py", force=True)
```

## get_workspace_info

Returns workspace configuration to help AI understand path mappings between host and container.

**Parameters:** None

**Returns:** Dictionary with:
- `workspace_root`: Container workspace path (e.g., "/workspace")
- `workspace_host_path`: Host directory mounted (e.g., "/Users/minh/selfhost/")
- `workspace_project`: Current WORKSPACE_PROJECT restriction (if any)
- `subdirectories`: List of immediate subdirectories under workspace_root

**Example:**
```
get_workspace_info()  # See available projects
```
Use this to discover which project directories are available and how to construct paths. For example, if you're working in `/Users/minh/selfhost/project1/`, access files using `project1/filename`. The `subdirectories` list shows all available projects.