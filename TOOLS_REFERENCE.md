# LSS-MCP Tool Reference

## Overview

`server.py` implements a Model Context Protocol (MCP) server that offloads expensive data retrieval and processing operations to local open-source tools. Each tool is designed to minimize token usage while maximizing information quality and security.

---

## Tool Details

### 1. `web_search`

**Purpose:** Perform web searches using a local SearXNG instance instead of relying on the AI's built-in search capabilities or external API calls.

**Why needed:**
- External search APIs (like OpenAI's web search) charge per query and consume many tokens returning full result pages
- Local SearXNG returns only structured JSON with 5 results (title, URL, snippet)

**What it does:**
- accepts a query string
- sends request to `SEARXNG_URL` (default: http://localhost:8080)
- extracts top 5 results
- returns compact JSON array: `[{"title": "", "url": "", "snippet": ""}, ...]`
- includes headers to spoof localhost for SearXNG

**Token implications:**
- ~150-300 tokens per call (tiny JSON)
- vs ~2,000-10,000 tokens if AI fetched web content directly through API
- **saves ~90%** on search operations

**Security:**
- validates URL scheme (http/https only)
- blocks private/internal IPs unless explicitly localhost for SearXNG
- limits query length to 500 chars

---

### 2. `read_webpage`

**Purpose:** Fetch and parse web pages with JavaScript execution support, returning clean Markdown without HTML bloat.

**Why needed:**
- Modern websites use JavaScript to render content; simple HTTP fetches miss dynamically loaded data
- Full HTML contains massive amounts of boilerplate, scripts, styles that waste tokens
- Using external scraping services (like OpenAI's data processing) is expensive and limited

**What it does:**
- uses `crawl4ai`'s `AsyncWebCrawler` to fetch the URL
- executes JavaScript, waits for page load
- strips HTML, converts to clean Markdown
- preserves structure while removing noise

**Token implications:**
- Returns ~1-5KB of clean Markdown for typical articles
- Direct HTML+JS could be 20-100KB of unprocessed content
- **saves ~70-90%** vs raw HTML
- Avoids separate AI step to parse/clean HTML

**Security:**
- URL validated for SSRF (blocks private IP ranges)
- max URL length: 2000 chars
- async crawler with 10s timeout
- no persistent state between requests

---

### 3. `read_document`

**Purpose:** Parse documents (PDF, Office, images, HTML, CSV, audio/video, and more) into clean, LLM-optimized Markdown with caching. Supports both local files and URLs.

**Why needed:**
- Binary document formats cannot be directly consumed by AI; they require specialized parsers
- External API parsers (e.g., GPT's file upload) cost extra tokens and have size limits
- Docling preserves tables, formatting, and structure better than naive text extraction
- Caching reduces repeated processing of same documents

**What it does:**
- accepts either local workspace path or `https://` URL
- for URLs: validates SSRF, auto-detects format via docling (no need to derive extension)
- for local files: enforces workspace boundary, blocks sensitive files (.env, .key, etc.)
- uses `docling.document_converter.DocumentConverter` with auto-detected formats
- caches conversion results (LRU cache of 20 sources)
- exports to Markdown with preserved formatting

**Supported formats:**
- PDF (including scanned with OCR)
- Office: DOCX, PPTX, XLSX
- Images: PNG, JPEG, TIFF, BMP, GIF, WEBP
- Web: HTML, XML
- Text: Markdown, CSV, plain text
- Documents: LaTeX, RTF, ODT
- Audio/Video: WAV, MP3, M4A, AAC, OGG, FLAC, MP4, AVI, MOV (requires `docling[asr]`)

**Token implications:**
- Returns only the meaningful content in structured Markdown
- Avoids sending raw binary/hex or poorly formatted plain text
- ~50-80% token reduction vs base64-encoded raw file contents
- Caching reduces repeated conversions for same source
- No document size limits beyond temporary storage constraints

**Security:**
- SSRF validation on URLs (private IPs blocked)
- workspace path confinement via `_validate_local_path()`
- sensitive file pattern blocking (.pem, .key, credentials, etc.)
- temp files always cleaned up

**Error handling:**
- Detects missing optional dependencies (e.g., audio support requires `docling[asr]`)
- Provides clear installation instructions for missing extras

---

### 4. `read_code_outline`

**Purpose:** Return only function and class signatures from a Python file using AST parsing, without reading the full file.

**Why needed:**
- Full Python files can be thousands of lines; reading them wastes tokens before the AI knows if they're relevant
- AI needs to explore codebases; seeing just the structure first is far more token-efficient
- Allows the AI to decide which files to read fully based on signatures

**What it does:**
- parses Python file with `ast.parse()`
- walks AST with `OutlineVisitor`
- collects `ClassDef` and `FunctionDef`/`AsyncFunctionDef` nodes
- outputs indented list: `Class: ClassName`, `Method: Class.method(args)`, `Function: func(args)`

**Token implications:**
- 100-500 tokens for typical files vs 5,000-20,000 tokens for full file
- **saves 90-95%** when exploring code structure
- Enables targeted file reading only when necessary

**Security:**
- path validation and sensitive file blocking
- fails gracefully on parse errors

---

### 5. `run_command_compressed`

**Purpose:** Execute shell commands with truncated output to prevent token bloat from large successful outputs while preserving full error traces.

**Why needed:**
- Commands like `git status`, `ls -la`, or `pytest` can produce massive output
- AI assistants often run exploratory commands; success output doesn't need to be fully preserved
- But errors require full context for debugging

**What it does:**
- splits command safely with `shlex.split()` (no shell=True to prevent injection)
- runs with `subprocess.run(..., capture_output=True, timeout=60)`
- if returncode != 0: returns full `stderr` (last 2000 chars)
- if success: returns only first 500 chars of stdout, adds "... (truncated to save tokens)"

**Token implications:**
- typical command output: 5-50 KB → truncated to ~500 chars (0.5 KB)
- **saves 90-99%** on command execution tokens
- errors still fully preserved for troubleshooting

**Security:**
- no shell execution (prevents command injection)
- max command length: 2000 chars
- timeout prevents hanging
- workspace confinement via path validation if command accesses files

---

### 6. `compress_and_read_image`

**Purpose:** Downscale and compress images (e.g., UI screenshots) before sending to vision models to reduce vision token costs.

**Why needed:**
- Vision models charge per image token; high-resolution screenshots can cost $0.01-$0.10 each
- Most detail is preserved at lower resolutions for UI/terminal analysis
- Compression maintains readability while drastically reducing tokens

**What it does:**
- opens image with PIL/Pillow
- converts to RGB
- resizes with `thumbnail((800, 800))` (maintains aspect ratio, max 800x800)
- saves as JPEG with quality=60%
- returns base64 data URL: `data:image/jpeg;base64,...`

**Token implications:**
- 1920x1080 PNG: ~1.5 MB uncompressed → ~80 KB compressed JPEG
- Vision token calculation: tokens ∝ image area
- ~800x800 image uses ~1700 vision tokens; original would use ~5000-10000 tokens
- **saves 80-90%** per vision request

**Security:**
- path validation and sensitive file blocking
- catches all PIL exceptions

---

### 7. `map_repository`

**Purpose:** Generate a compact, hierarchical tree view of repository structure with `.gitignore` support and configurable depth.

**Why needed:**
- AI needs to understand project layout; listing full directory contents can be huge
- `find` or `ls -R` output for large repos can be 100KB+ of tokens
- A compressed tree format shows structure without overwhelming context
- Respects `.gitignore` to avoid showing ignored files
- Depth control prevents deep diving into unwanted areas

**What it does:**
- walks workspace directory up to `max_depth` (default 3)
- respects `.gitignore` rules if present
- filters `.git`, `node_modules`, `venv`, `__pycache__`, `dist`, `build`, binary files
- produces emoji-annotated indented lines:
  ```
  📂 src/
    📄 main.py
    📂 components/
      📄 Button.tsx
  ```
- hard caps at 2000 files
- truncates output to ~8000 chars

**Token implications:**
- Typical repo: full `ls -R` output = 10-50 KB; map = 1-2 KB
- **saves 80-95%** on initial exploration
- Prevents AI from accidentally consuming tokens on massive file listings

**Security:**
- path confinement to workspace
- ignores common dependency/virtual environment directories
- file count cap prevents DoS on huge directories

---

### 7b. `focused_glob`

**Purpose:** Find files matching a glob pattern with automatic junk filtering and result caps.

**Why needed:**
- Native `glob.glob()` returns everything including `node_modules`, `.git`, build artifacts
- AI only needs first few matches to confirm pattern correctness
- Unfiltered results can be hundreds of files, wasting tokens

**What it does:**
- uses Python's `glob.glob()` with recursive=True
- applies `.gitignore` rules (if present)
- filters common junk directories: `.git`, `node_modules`, `dist`, `build`, `venv`, `__pycache__`
- returns only files (not directories)
- caps results at `limit` (default 50)

**Token implications:**
- Unfiltered glob could return 1000+ entries; this returns max 50
- **saves 90-99%** on file discovery
- Clear feedback when results are truncated encourages more specific patterns

**Security:**
- workspace path validation
- filters sensitive patterns via existing rules

---

### 7c. `smart_code_search`

**Purpose:** Grep replacement that returns matches with context lines and strict token limits.

**Why needed:**
- Raw grep returns exact matched lines with no context, forcing AI to read full files anyway
- Grep can return hundreds of matches, overwhelming the context window
- Needs context to be useful but must cap total output

**What it does:**
- tries to use `ripgrep (rg)` if available (faster), falls back to `grep`
- uses `-C 2` to include 2 lines of context before/after
- uses `--no-heading` for clean output
- strips `/workspace/` prefix from paths
- caps output at ~8000 chars (about 2000 tokens)

**Token implications:**
- Raw grep on large codebase: could be 10,000+ tokens
- This tool: max 2000 tokens with useful context
- **saves 80-90%** while providing actionable snippets

**Security:**
- command injection safe (uses subprocess with shell=True but with controlled input; could be hardened further)
- respects workspace boundary by searching only `/workspace`
- query length limit: 500 chars

---

### 7d. `read_file_skeleton`

**Purpose:** Extract only imports, functions, classes, and types from code files. Use BEFORE reading full files.

**Why needed:**
- Full files can be thousands of lines; AI needs to know structure first
- Different languages have different syntax; uses regex patterns for Python, JS/TS, Go
- Gives line numbers so AI can request specific sections later

**What it does:**
- reads entire file into memory (subject to safe_read_file limits)
- applies multi-language regex patterns to detect:
  - Python: `def`, `class`, `import`, `from`, decorators (`@`)
  - JS/TS: `export`, `function`, `class`, arrow functions (`const x = =>`), `type`, `interface`, `var`, `let`, `static`
  - Go: `func`, `type`, `package`, `import`, `struct`
- returns each matching line with its line number
- truncates skeleton to ~2000 chars

**Token implications:**
- Typical 2000-line file full read: ~8000 tokens
- Skeleton: 200-500 tokens
- **saves 90-95%** during code exploration phase

**Security:**
- path validation, sensitive file blocking
- safe file size inherited (reads up to 30KB by default; for larger files, safe_read_file will warn)

---

### 7e. `read_lines`

**Purpose:** Read a specific line range from a file. Use after `read_file_skeleton` to extract only the needed code.

**Why needed:**
- Once AI knows the line numbers of a function, reading the entire file is wasteful
- Enables surgical extraction of just the relevant section
- Efficiently supports edit workflows (read-targeted-lines, modify, write-back)

**What it does:**
- validates path and sensitivity
- checks line range validity
- streams file line-by-line, collecting only lines in the requested range
- returns numbered lines with filename and range in header
- respects UTF-8 with error ignoring

**Token implications:**
- Reading 50 targeted lines: ~200 tokens vs full 2000-line file: ~8000 tokens
- **saves 90%+** for targeted reads

**Security:**
- workspace confinement
- sensitive file blocking
- line number validation prevents nonsensical ranges

---

---

### 8. `search_codebase`

**Purpose:** Perform full-text search through the codebase using SQLite FTS5 (BM25 ranking) for precise, token-efficient code lookup.

**Why needed:**
- `grep`-style searches in raw files would require AI to read many files to find matches
- Alternatively, AI could request entire file contents; that's massively wasteful
- FTS5 indexes all indexable files in background, allowing targeted snippet retrieval

**What it does:**
- background thread initializes SQLite FTS5 database at `/tmp/code_fts.db`
- indexes all files with allowlisted extensions (`.py`, `.js`, `.ts`, `.go`, etc.)
- skips sensitive files
- each line becomes a separate FTS entry with path and line number
- on query: `SELECT ... MATCH ? ORDER BY bm25(...) LIMIT n`
- returns formatted lines: `path:line_num: content`

**Token implications:**
- Search query: ~10-50 tokens
- Results: ~50-200 tokens per match (exact snippet with line number)
- vs reading entire files: 1000-10000 tokens per file
- **saves 95-99%** for code search operations

**Security:**
- indexing only allowlisted extensions (prevents indexing binaries/large assets)
- sensitive file patterns blocked
- database stored in `/tmp` (ephemeral)
- query length limit (500 chars)

---

### 9. `safe_read_file`

**Purpose:** Read file contents with a size check to prevent accidental huge file loads (e.g., minified JS, generated code, large data files).

**Why needed:**
- AI agents may naively request files like `bundle.js` (1MB+), `node_modules` contents, or `.min.js`
- One such file can blow the context window instantly
- Default block at 30 KB forces AI to use smarter approaches (search, outline, or explicit `force=True`)

**What it does:**
- validates path, checks sensitive patterns
- checks file size with `os.path.getsize()`
- if >30,000 bytes and `force=False`: returns error message with suggestions
- if under threshold or `force=True`: reads and returns full content

**Token implications:**
- Prevents catastrophic token consumption from single large files
- 30 KB ≈ 8000 tokens (safe threshold)
- Forces AI to use `search_codebase()` or `read_code_outline()` first
- Can still read large files intentionally when needed

**Security:**
- workspace confinement
- sensitive file blocking
- prevents accidental memory/context explosion

---

## Design Principles

1. **Token First** Every tool returns compact, structured data tailored for LLM consumption.
2. **Local Offload** Expensive operations (search, parsing, crawling) happen locally; only distilled results sent to AI.
3. **Fail Safe** Errors preserved fully; successful output truncated when safe.
4. **Security Boundaries** Workspace confinement, SSRF protection, sensitive file blocking, no shell injection.
5. **Progressive Disclosure** Outline before full file, map before deep search, limits before raw reads.

---

## Cost Savings Summary

| Operation | Without LSS-MCP | With LSS-MCP | Savings |
|-----------|------------------|--------------|---------|
| Web search (per query) | ~10,000 tokens | ~500 tokens | 95% |
| Web page fetch | ~5,000-20,000 (raw HTML) | ~1,000-3,000 (Markdown) | 80% |
| Document parse | ~base64 file + processing | ~1,500-5,000 tokens (Markdown) | 85%+ |
| Code exploration | Full files (5,000-50,000) | Outline (200-500) + targeted reads | 90%+ |
| Repo overview | `ls -R` (10-50 KB) | Tree map (1-2 KB) | 95% |
| Code search | Read many files | Snippet only (200-500 per result) | 98% |
| Command output | Unfiltered (could be MBs) | Truncated success (500 chars) | 99% |
| Vision analysis | Full resolution (5000-10000 tokens) | 800px compressed (1500-2500 tokens) | 70-80% |

**Overall impact:** For an AI coding assistant performing daily development tasks (searches, file browsing, document parsing, command execution), token costs typically drop by **80-90%** when using the Local Support Stack vs cloud APIs for these operations.