# LSS-MCP Usage Skill

Teaches the AI assistant how to use LSS-MCP tools effectively, including workspace path mapping and best practices.

## When to Use

Invoke this skill when the user mentions "lss-mcp", "local support stack", "mcp server", or any LSS-MCP tool names. The agent should automatically apply these patterns throughout the session.

## Core Instruction

**ALWAYS** call `get_workspace_info()` at the start of any LSS-MCP interaction to understand the workspace structure. Store the results for the session and use them to construct correct file paths.

## Workspace Path Mapping

- The container's `/workspace` maps to the host directory specified by `WORKSPACE_PATH` in `.env` (typically `/Users/minh/selfhost/`)
- All file tool paths are **relative to `/workspace`** (container root), not the host root
- When user refers to a file in their project (e.g., `/Users/minh/selfhost/project1/main.py`), construct the path as `project1/main.py`
- If uncertain about the correct path, call `get_workspace_info()` and examine the `subdirectories` list to identify the project name
- The `workspace_host_path` field shows which host directory is mounted

## Tool Usage Best Practices

### File Reading (Token-Efficient Order)

1. **Explore first**: Use `map_repository(directory="project1", max_depth=2)` to understand project structure
2. **Find files**: Use `focused_glob("**/*.py", directory="project1")` to locate specific files
3. **Outline**: Use `read_code_outline("project1/main.py")` to see functions/classes only
4. **Extract**: Use `read_lines("project1/main.py", start_line, end_line)` to get specific sections
5. **Full read**: Use `safe_read_file("project1/main.py")` only when absolutely necessary

### Searching

- Use `search_codebase("query", limit=5)` for precise full-text search with BM25 ranking
- Use `smart_code_search("keyword", file_pattern="*.py")` when you need context lines
- Prefer `search_codebase` for token efficiency; use `smart_code_search` when context is critical

### Web & Documents

- `web_search("query")` returns compact JSON (5 results max)
- `read_webpage("https://...")` fetches and returns clean Markdown
- `read_document("path/to/file.pdf")` parses documents; use local paths with correct prefix
- `compress_and_read_image("path/to/image.png")` before any image analysis task

### Commands

- `run_command_compressed("command")` executes shell commands; successful output is truncated
- Errors are always preserved in full

## Error Recovery

If a file operation fails with "outside allowed workspace" or "file not found":
1. Pause and call `get_workspace_info()` to verify workspace mapping
2. Check if the path includes the correct project prefix
3. Verify the file exists using `focused_glob()` or `map_repository()`
4. Adjust the path accordingly and retry

## Session Initialization

When user says "use LSS-MCP" or similar:
1. Immediately call `get_workspace_info()` and store the mapping
2. Inform the user: "LSS-MCP is ready. Workspace root: /workspace (host: {workspace_host_path}). Available projects: {list subdirectories}."
3. Ask which project they're working on if not clear from context
4. Proceed with appropriate project-prefixed paths

## Example Workflow

User: "Read the main.py file in my project"
Agent:
1. Call `get_workspace_info()` → learns subdirectories = ["project1", "project2"]
2. Ask: "Which project? I see: project1, project2"
3. User: "project1"
4. Agent finds file: `focused_glob("main.py", directory="project1")` → returns `project1/src/main.py`
5. Agent reads: `read_code_outline("project1/src/main.py")`
6. Agent asks: "Which functions do you want to see?"
7. User: "The process_data function"
8. Agent finds line range from outline, then: `read_lines("project1/src/main.py", start, end)`

## Configuration Reminder

The LSS-MCP must be configured in your agent's MCP settings. Command:
```
docker exec -i lss-mcp_support_server python /app/server.py
```

See README.md and AGENTS.md for agent-specific configuration instructions.
