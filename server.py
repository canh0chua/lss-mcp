import os
import tempfile
import ast
from pathlib import Path
import subprocess
import io
import base64
import json
import sqlite3
import shlex
import threading
import ipaddress
import requests
import re
import pathspec
import glob
from functools import lru_cache
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP
from crawl4ai import AsyncWebCrawler
from docling.document_converter import DocumentConverter

mcp = FastMCP("Local_AI_Support_Stack")

# ---------------------------------------------------------------------------
# Security helpers
# ---------------------------------------------------------------------------

# Allowed root directory for all local file access.
# Set WORKSPACE env var to override; falls back to ~/workspace for cross-platform local dev.
_WORKSPACE = os.path.realpath(os.environ.get("WORKSPACE", str(Path.home() / "workspace")))

# Sensitive file patterns that should never be read or indexed.
_SENSITIVE_PATTERNS = (
    ".env", ".pem", ".key", ".p12", ".pfx", ".crt", ".cer",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    ".netrc", ".pgp", ".gpg", "credentials", "secret",
)

# Extension allowlist for FTS indexing (text-based source files only).
_INDEXABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".zsh", ".fish",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".json", ".xml", ".html", ".css", ".scss", ".md", ".txt",
    ".sql", ".graphql", ".proto", ".tf", ".hcl",
}

# Maximum input lengths for tool parameters.
_MAX_QUERY_LEN = 500
_MAX_PATH_LEN = 1000
_MAX_CMD_LEN = 2000
_MAX_URL_LEN = 2000

# Private/loopback IP ranges blocked for SSRF protection.
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / AWS metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _validate_local_path(path: str) -> str:
    """
    Resolve *path* and assert it lives inside _WORKSPACE.
    Returns the resolved absolute path on success.
    Raises ValueError with a safe message on failure.
    """
    if len(path) > _MAX_PATH_LEN:
        raise ValueError("Path exceeds maximum allowed length.")
    resolved = os.path.realpath(path)
    if not resolved.startswith(_WORKSPACE + os.sep) and resolved != _WORKSPACE:
        raise ValueError(
            f"Access denied: path is outside the allowed workspace ({_WORKSPACE})."
        )
    return resolved


def _is_sensitive_file(path: str) -> bool:
    """Return True if the filename matches a known-sensitive pattern."""
    name = os.path.basename(path).lower()
    return any(pat in name for pat in _SENSITIVE_PATTERNS)


def _validate_url(url: str, *, require_public: bool = True) -> str:
    """
    Validate *url* is a well-formed http/https URL.
    If *require_public* is True, reject URLs that resolve to private/loopback IPs.
    Returns the validated URL on success, raises ValueError on failure.
    """
    if len(url) > _MAX_URL_LEN:
        raise ValueError("URL exceeds maximum allowed length.")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme '{parsed.scheme}'. Only http/https are allowed.")
    if not parsed.netloc:
        raise ValueError("URL is missing a host.")
    if require_public:
        hostname = parsed.hostname or ""
        try:
            addr = ipaddress.ip_address(hostname)
            for net in _PRIVATE_NETWORKS:
                if addr in net:
                    raise ValueError(f"Access denied: URL resolves to a private/internal address.")
        except ValueError as exc:
            # Re-raise our own errors; ignore non-IP hostnames (DNS not resolved here).
            if "Access denied" in str(exc) or "Unsupported" in str(exc) or "missing" in str(exc):
                raise
    return url


def _validate_searxng_url(url: str) -> str:
    """Validate the SearXNG base URL (localhost is explicitly allowed)."""
    if len(url) > _MAX_URL_LEN:
        raise ValueError("SEARXNG_URL exceeds maximum allowed length.")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"SEARXNG_URL has unsupported scheme '{parsed.scheme}'.")
    if not parsed.netloc:
        raise ValueError("SEARXNG_URL is missing a host.")
    return url


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def web_search(query: str) -> str:
    """Search the web for real-time information. Returns a compact JSON array to save tokens."""
    if len(query) > _MAX_QUERY_LEN:
        return f"Error: query exceeds maximum length of {_MAX_QUERY_LEN} characters."
    try:
        raw_url = os.getenv("SEARXNG_URL", "http://localhost:8080")
        searxng_url = _validate_searxng_url(raw_url)
    except ValueError as e:
        return f"Configuration error: {e}"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1"
        }
        response = requests.get(
            f"{searxng_url}/search",
            params={"q": query, "format": "json"},
            headers=headers,
            timeout=10
        )
        results = response.json().get("results", [])[:5]
        # Use .get() with safe defaults to avoid KeyError on malformed results.
        clean_results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in results
        ]
        return json.dumps(clean_results)
    except Exception as e:
        return f"Search failed. Ensure SearXNG is running. Error: {str(e)}"


@mcp.tool()
async def read_webpage(url: str) -> str:
    """Fetch a URL, execute JavaScript, strip HTML bloat, and return pure Markdown."""
    if len(url) > _MAX_URL_LEN:
        return f"Error: URL exceeds maximum length of {_MAX_URL_LEN} characters."
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)
            if not result.success:
                return f"Failed to crawl URL. Error: {result.error_message}"
            return result.markdown
    except Exception as e:
        return f"Failed to fetch webpage: {str(e)}"


@mcp.tool()
def read_document(path_or_url: str) -> str:
    """
    Parse documents into Markdown using Docling.
    Supports both local files and remote URLs with automatic format detection.

    Supported formats:
    - PDF (including scanned with OCR)
    - Microsoft Office: Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
    - Images: PNG, JPEG, TIFF, BMP, GIF, WEBP (with OCR)
    - Web: HTML, XML
    - Text: Markdown (.md), CSV (.csv), plain text (.txt)
    - Documents: LaTeX, RTF, ODT
    - Audio/Video: WAV, MP3, M4A, AAC, OGG, FLAC, MP4, AVI, MOV (requires `docling[asr]`)

    Local paths are restricted to the workspace directory.
    Remote URLs must point to public hosts (private/internal IPs are blocked).

    Returns Markdown output. Caching is enabled for recently converted documents.
    """
    if len(path_or_url) > _MAX_URL_LEN:
        return f"Error: path/URL exceeds maximum allowed length."

    parsed = urlparse(path_or_url)
    is_url = parsed.scheme in ("http", "https")

    try:
        if is_url:
            # Validate URL for SSRF before processing.
            try:
                _validate_url(path_or_url, require_public=True)
            except ValueError as e:
                return f"Error: {e}"
            source = path_or_url
        else:
            # Local file — enforce workspace boundary.
            try:
                resolved = _validate_local_path(path_or_url)
            except ValueError as e:
                return f"Error: {e}"
            if _is_sensitive_file(resolved):
                return "Error: Access denied — sensitive file type."
            if not os.path.exists(resolved):
                return f"Error: Local file '{resolved}' not found."
            source = resolved

        # Convert with caching
        return _convert_source_cached(source)

    except ImportError as e:
        missing = str(e)
        if "asr" in missing or "whisper" in missing or "soundfile" in missing:
            return ("Error: Audio/Video support requires optional dependencies. "
                    "Install with: pip install 'docling[asr]'")
        return f"Error: Missing dependency: {e}"
    except Exception as e:
        return f"Failed to parse document: {str(e)}"


@lru_cache(maxsize=20)
def _convert_source_cached(source: str) -> str:
    """Convert a document source (file path or URL) to Markdown with caching."""
    converter = _get_converter()
    result = converter.convert(source)

    # Error handling for different docling versions
    has_error = False
    error_message = ""
    if hasattr(result, "status"):
        if hasattr(result.status, "is_error"):
            has_error = result.status.is_error
        elif hasattr(result.status, "error"):
            has_error = result.status.error
    if hasattr(result, "errors") and result.errors:
        has_error = True
        error_message = str(result.errors)

    if has_error:
        raise RuntimeError(f"Docling conversion error: {error_message}")

    return result.document.export_to_markdown()


@lru_cache(maxsize=1)
def _get_converter() -> DocumentConverter:
    """Return a cached DocumentConverter instance."""
    return DocumentConverter()


@mcp.tool()
def read_code_outline(file_path: str) -> str:
    """Returns ONLY the function and class signatures of a Python file. Use this BEFORE reading full files to save tokens."""
    if len(file_path) > _MAX_PATH_LEN:
        return f"Error: path exceeds maximum allowed length."
    try:
        resolved = _validate_local_path(file_path)
    except ValueError as e:
        return f"Error: {e}"

    if _is_sensitive_file(resolved):
        return "Error: Access denied — sensitive file type."

    try:
        with open(resolved, "r") as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception as e:
        return f"Failed to parse outline: {str(e)}"

    # Use a NodeVisitor to preserve class context for methods.
    class OutlineVisitor(ast.NodeVisitor):
        def __init__(self):
            self.outline = []
            self._class_stack = []

        def visit_ClassDef(self, node):
            self.outline.append(f"Class: {node.name}")
            self._class_stack.append(node.name)
            self.generic_visit(node)
            self._class_stack.pop()

        def visit_FunctionDef(self, node):
            args = [a.arg for a in node.args.args]
            if self._class_stack:
                self.outline.append(
                    f"  Method: {self._class_stack[-1]}.{node.name}({', '.join(args)})"
                )
            else:
                self.outline.append(f"Function: {node.name}({', '.join(args)})")
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

    visitor = OutlineVisitor()
    visitor.visit(tree)
    return "\n".join(visitor.outline) if visitor.outline else "No classes or functions found."


@mcp.tool()
def run_command_compressed(command: str) -> str:
    """
    Runs a terminal command but truncates successful output to save tokens.
    The command is executed without a shell (shell=False) for security.
    Use standard shell syntax (pipes, redirects) is NOT supported.
    Preserves errors.
    """
    if len(command) > _MAX_CMD_LEN:
        return f"Error: command exceeds maximum length of {_MAX_CMD_LEN} characters."
    try:
        # Split safely — no shell=True to prevent injection.
        args = shlex.split(command)
    except ValueError as e:
        return f"Error: could not parse command: {e}"

    try:
        result = subprocess.run(
            args,
            shell=False,
            text=True,
            capture_output=True,
            timeout=60,
        )

        if result.returncode != 0:
            return f"FAILED. Error Trace:\n{result.stderr[-2000:]}"

        output = result.stdout.strip()
        if len(output) > 500:
            return f"SUCCESS. (Output truncated to save tokens): {output[:500]}..."
        return f"SUCCESS: {output}"

    except subprocess.TimeoutExpired:
        return "Error: command timed out after 60 seconds."
    except Exception as e:
        return f"Execution failed: {str(e)}"


@mcp.tool()
def compress_and_read_image(image_path: str) -> str:
    """Resizes and compresses large UI screenshots before analysis to save vision tokens."""
    if len(image_path) > _MAX_PATH_LEN:
        return f"Error: path exceeds maximum allowed length."
    try:
        resolved = _validate_local_path(image_path)
    except ValueError as e:
        return f"Error: {e}"

    if _is_sensitive_file(resolved):
        return "Error: Access denied — sensitive file type."

    try:
        from PIL import Image
        with Image.open(resolved) as img:
            img = img.convert("RGB")
            img.thumbnail((800, 800))

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=60)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        return f"Image compression failed: {str(e)}"


@mcp.tool()
def map_repository(directory: str = None, max_depth: int = 3) -> str:
    if directory is None:
        directory = _WORKSPACE
    """Always use this instead of 'ls' or 'tree' to understand the project structure."""
    if len(directory) > _MAX_PATH_LEN:
        return f"Error: directory path exceeds maximum allowed length."
    try:
        resolved = _validate_local_path(directory)
    except ValueError as e:
        return f"Error: {e}"

    try:
        # Respect .gitignore if it exists
        gitignore_path = os.path.join(resolved, '.gitignore')
        ignore_spec = None
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', f)

        repo_map = []
        file_count = 0
        MAX_FILES = 2000  # Hard cap

        for root, dirs, files in os.walk(resolved):
            # Calculate current depth
            depth = root.replace(resolved, '').count(os.sep)
            if depth >= max_depth:
                dirs[:] = []  # Stop walking deeper
                continue

            # Filter out junk directories immediately
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", "__pycache__", "dist", "build"}]

            # Format output tightly
            indent = '  ' * depth
            folder_name = os.path.basename(root) or "ROOT"
            repo_map.append(f"{indent}📂 {folder_name}/")

            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), resolved)
                if ignore_spec and ignore_spec.match_file(rel_path):
                    continue

                # Skip heavy binary/lock files
                if file.endswith(('.lock', '.png', '.sqlite', '.min.js', '.pdf', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2')):
                    continue

                repo_map.append(f"{indent}  📄 {file}")
                file_count += 1
                if file_count >= MAX_FILES:
                    repo_map.append("... (truncated)")
                    output = "\n".join(repo_map)
                    return output[:8000] + "\n... (truncated for size)"

        # Join and truncate to ~2000 tokens
        final_output = "\n".join(repo_map)
        if len(final_output) > 8000:
            return final_output[:8000] + "\n... (truncated for size)"
        return final_output
    except Exception as e:
        return f"Mapping failed: {str(e)}"


@mcp.tool()
def smart_code_search(keyword: str, file_pattern: str = "*.*") -> str:
    """Use this instead of 'grep'. Searches code and returns the top matches with surrounding context lines."""
    if len(keyword) > _MAX_QUERY_LEN:
        return f"Error: query exceeds maximum length of {_MAX_QUERY_LEN} characters."
    try:
        # Use ripgrep if available (faster), fallback to grep
        import shutil
        rg_path = shutil.which('rg')
        workspace = _WORKSPACE
        # Ensure workspace has trailing slash for replacement
        workspace_prefix = workspace if workspace.endswith(os.sep) else workspace + os.sep

        if rg_path:
            # -C 2: 2 lines of context, -n: show line numbers, --no-heading: cleaner output
            cmd = f'rg -C 2 -n --no-heading --type-add "search:*" --include "{file_pattern}" "{keyword}" "{workspace}" | head -n 100'
        else:
            cmd = f'grep -rn -C 2 --include="{file_pattern}" "{keyword}" "{workspace}" 2>/dev/null | head -n 100'

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if not result.stdout:
            return f"No matches found for '{keyword}'."

        output_lines = result.stdout.strip().split('\n')

        # Compress the output format to save tokens
        compressed_results = []
        for line in output_lines:
            if line == "--":  # Grep's context separator
                compressed_results.append("---")
            else:
                # Remove the workspace prefix for brevity
                compressed_results.append(line.replace(workspace_prefix, ''))

        # Hard limit the return payload to ~2000 tokens
        final_text = "\n".join(compressed_results)
        if len(final_text) > 8000:
            final_text = final_text[:8000] + "\n... (truncated)"

        return f"Found matches (showing top results):\n{final_text}"

    except Exception as e:
        return f"Search failed: {str(e)}"


@mcp.tool()
def read_file_skeleton(file_path: str) -> str:
    """Always use this BEFORE reading a full file. Returns only the imports, functions, classes, and types."""
    if len(file_path) > _MAX_PATH_LEN:
        return f"Error: path exceeds maximum allowed length."
    try:
        resolved = _validate_local_path(file_path)
    except ValueError as e:
        return f"Error: {e}"

    if _is_sensitive_file(resolved):
        return "Error: Access denied — sensitive file type."

    try:
        with open(resolved, 'r') as f:
            lines = f.readlines()

        skeleton = []
        # Basic regex to catch Python, JS/TS, and Go signatures
        patterns = [
            r"^(def |class |import |from |@)",  # Python + decorators
            r"^(export |function |class |const .*=.*=>|type |interface |var |let |static )",  # JS/TS
            r"^(func |type |package |import |struct )"  # Go
        ]
        combined_pattern = re.compile("|".join(patterns))

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if combined_pattern.match(stripped):
                # Include the line number so the LLM knows exactly where to look later
                skeleton.append(f"Line {i+1}: {line.rstrip()}")

        if not skeleton:
            return "No obvious functions/classes/imports found. The file might be purely data or UI markup."

        # Limit skeleton to ~500 tokens to prevent abuse
        skeleton_text = "\n".join(skeleton)
        if len(skeleton_text) > 2000:
            skeleton_text = skeleton_text[:2000] + "\n... (truncated)"

        return "File Skeleton:\n" + skeleton_text
    except Exception as e:
        return f"Failed to read skeleton: {str(e)}"


@mcp.tool()
def focused_glob(pattern: str, directory: str = None, limit: int = 50) -> str:
    if directory is None:
        directory = _WORKSPACE
    """Finds files matching a pattern. Automatically filters junk and caps results to save tokens."""
    try:
        if len(directory) > _MAX_PATH_LEN:
            return f"Error: directory path exceeds maximum allowed length."
        try:
            resolved = _validate_local_path(directory)
        except ValueError as e:
            return f"Error: {e}"

        # Load .gitignore rules
        gitignore_path = os.path.join(resolved, '.gitignore')
        spec = None
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                spec = pathspec.PathSpec.from_lines('gitwildmatch', f)

        # Recursive globbing - handle patterns with ** correctly
        full_pattern = os.path.join(resolved, pattern)
        raw_matches = glob.glob(full_pattern, recursive=True)

        filtered_matches = []
        for match in raw_matches:
            rel_path = os.path.relpath(match, resolved)

            # Filter by .gitignore
            if spec and spec.match_file(rel_path):
                continue

            # Filter common junk directories
            parts = rel_path.split(os.sep)
            if any(part in parts for part in {'.git', 'node_modules', 'dist', 'build', 'venv', '__pycache__'}):
                continue

            # Skip directories
            if os.path.isdir(match):
                continue

            filtered_matches.append(rel_path)
            if len(filtered_matches) >= limit:
                break

        if not filtered_matches:
            return "No matches found (ignoring hidden/junk folders)."

        result = "\n".join(filtered_matches)
        if len(raw_matches) > limit:
            result += f"\n\n... and {len(raw_matches) - limit} more files omitted. Be more specific with your pattern."

        return f"Matches found:\n{result}"
    except Exception as e:
        return f"Glob failed: {str(e)}"


@mcp.tool()
def read_lines(file_path: str, start_line: int, end_line: int) -> str:
    """Reads a specific range of lines from a file. Use this after read_file_skeleton to extract only the code you need."""
    if len(file_path) > _MAX_PATH_LEN:
        return f"Error: path exceeds maximum allowed length."
    try:
        resolved = _validate_local_path(file_path)
    except ValueError as e:
        return f"Error: {e}"

    if _is_sensitive_file(resolved):
        return "Error: Access denied — sensitive file type."

    try:
        if not os.path.exists(resolved):
            return f"Error: File {resolved} not found."

        if start_line < 1 or end_line < start_line:
            return "Error: Invalid line range."

        with open(resolved, 'r', encoding='utf-8', errors='ignore') as f:
            output = []
            for i, line in enumerate(f, 1):
                if i >= start_line and i <= end_line:
                    output.append(f"{i}: {line.rstrip()}")
                if i > end_line:
                    break

        if not output:
            return f"No lines found in range {start_line}-{end_line}."

        content = "\n".join(output)
        return f"File: {resolved} (Lines {start_line}-{end_line})\n---\n{content}"
    except Exception as e:
        return f"Failed to read lines: {str(e)}"


# ---------------------------------------------------------------------------
# FTS5 full-text search
# ---------------------------------------------------------------------------

def _init_fts_db(db_path: str = "/tmp/code_fts.db") -> str:
    """
    Initialize SQLite FTS5 database and index the workspace.
    - Clears stale rows before re-indexing to prevent duplicates on restart.
    - Only indexes files with allowlisted extensions.
    - Skips sensitive files.
    """
    workspace = _WORKSPACE
    workspace_prefix = workspace if workspace.endswith(os.sep) else workspace + os.sep
    ignore_dirs = {".git", "node_modules", "venv", "__pycache__", ".venv"}

    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS code_fts
        USING fts5(
            path,
            content,
            line_num,
            tokenize='porter unicode61'
        )
    """)

    # Clear stale data before re-indexing to avoid duplicates on restart.
    cursor.execute("DELETE FROM code_fts")

    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            # Only index allowlisted file extensions.
            _, ext = os.path.splitext(file)
            if ext.lower() not in _INDEXABLE_EXTENSIONS:
                continue
            # Skip sensitive files.
            if _is_sensitive_file(file):
                continue

            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        content = line.strip()
                        if content:
                            cursor.execute(
                                "INSERT INTO code_fts (path, content, line_num) VALUES (?, ?, ?)",
                                (filepath.replace(workspace, "").lstrip("/") or filepath, content, i)
                            )
            except (OSError, IOError, UnicodeDecodeError):
                continue

    conn.commit()
    conn.close()
    return db_path


# Run DB initialization in a background thread so it doesn't block startup.
FTS_DB: str | None = None
_fts_lock = threading.Lock()


def _fts_init_worker():
    global FTS_DB
    try:
        db = _init_fts_db()
        with _fts_lock:
            FTS_DB = db
    except Exception as e:
        print(f"Warning: FTS5 initialization failed: {e}")


threading.Thread(target=_fts_init_worker, daemon=True).start()


@mcp.tool()
def search_codebase(query: str, limit: int = 5) -> str:
    """
    Full-text search through codebase using SQLite FTS5 (BM25 ranking).
    Returns top matches with file paths and line numbers.
    Much more precise than grep and token-efficient.
    """
    if len(query) > _MAX_QUERY_LEN:
        return f"Error: query exceeds maximum length of {_MAX_QUERY_LEN} characters."

    with _fts_lock:
        db = FTS_DB

    if not db:
        return "FTS5 search not available. Database may still be initializing — try again shortly."

    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT path, line_num, content
            FROM code_fts
            WHERE code_fts MATCH ?
            ORDER BY bm25(code_fts)
            LIMIT ?
        """, (query, limit))

        results = cursor.fetchall()
        conn.close()

        if not results:
            return f"No matches found for '{query}'"

        formatted = [f"{path}:{line_num}: {content}" for path, line_num, content in results]
        return "\n".join(formatted)
    except Exception as e:
        return f"Search failed: {str(e)}"


@mcp.tool()
def safe_read_file(file_path: str, force: bool = False) -> str:
    """
    Always use this to read code. It prevents accidentally reading massive files.
    Checks file size first to avoid token bloat from large legacy files.
    Only files within the configured workspace directory are accessible.
    """
    if len(file_path) > _MAX_PATH_LEN:
        return f"Error: path exceeds maximum allowed length."
    try:
        resolved = _validate_local_path(file_path)
    except ValueError as e:
        return f"Error: {e}"

    if _is_sensitive_file(resolved):
        return "Error: Access denied — sensitive file type."

    try:
        if not os.path.exists(resolved):
            return f"Error: File '{resolved}' does not exist."

        size_bytes = os.path.getsize(resolved)
        # 30 KB is roughly 8,000 tokens. Adjust threshold as needed.
        if size_bytes > 30000 and not force:
            return (
                f"BLOCKED: {resolved} is too large ({size_bytes / 1000:.1f} KB). "
                f"To save tokens, do not read this entire file. "
                f"Use search_codebase() to find the specific lines you need, "
                f"or call this tool again with force=True if absolutely necessary."
            )

        with open(resolved, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


if __name__ == "__main__":
    mcp.run()
