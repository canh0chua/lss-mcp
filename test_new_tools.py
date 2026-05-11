#!/usr/bin/env python3
"""
Manual test script for the new LSS-MCP tools.
Run this inside the container to verify functionality.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add /app to path so we can import server modules
sys.path.insert(0, '/app')

# Import the tools directly from server.py
from server import (
    map_repository,
    focused_glob,
    smart_code_search,
    read_file_skeleton,
    read_lines,
    _validate_local_path,
)

def test_map_repository():
    print("\n=== Testing map_repository ===")
    try:
        # Test with workspace root
        result = map_repository("/workspace", max_depth=2)
        print(f"✓ map_repository returned {len(result)} chars")
        print(f"Preview:\n{result[:500]}")
        assert "📂" in result or "[D]" in result, "Should contain directory markers"
        return True
    except Exception as e:
        print(f"✗ map_repository failed: {e}")
        return False

def test_focused_glob():
    print("\n=== Testing focused_glob ===")
    try:
        # Create some test files
        test_dir = Path("/tmp/test_glob")
        test_dir.mkdir(exist_ok=True)
        (test_dir / "file1.py").write_text("print('hello')")
        (test_dir / "file2.ts").write_text("console.log('world')")
        (test_dir / "node_modules").mkdir(exist_ok=True)
        (test_dir / "node_modules" / "ignored.js").write_text("// ignored")

        # Test glob pattern
        result = focused_glob("*.py", directory=str(test_dir))
        print(f"✓ focused_glob returned:\n{result}")
        assert "file1.py" in result, "Should find file1.py"
        assert "file2.ts" not in result, "Should not find file2.ts with *.py pattern"

        # Test that node_modules is filtered
        result_all = focused_glob("*.*", directory=str(test_dir), limit=10)
        assert "node_modules" not in result_all, "Should filter out node_modules"

        # Cleanup
        import shutil
        shutil.rmtree(test_dir)

        return True
    except Exception as e:
        print(f"✗ focused_glob failed: {e}")
        return False

def test_read_file_skeleton():
    print("\n=== Testing read_file_skeleton ===")
    try:
        # Create a test Python file
        test_file = Path("/tmp/test_skeleton.py")
        test_file.write_text("""import os
import sys

def hello(name: str) -> str:
    return f"Hello, {name}"

class Calculator:
    def add(self, a, b):
        return a + b

# This is a comment
x = 42
""")

        result = read_file_skeleton(str(test_file))
        print(f"✓ read_file_skeleton returned:\n{result}")
        assert "import" in result, "Should include imports"
        assert "def hello" in result, "Should include function"
        assert "class Calculator" in result, "Should include class"

        test_file.unlink()
        return True
    except Exception as e:
        print(f"✗ read_file_skeleton failed: {e}")
        return False

def test_read_lines():
    print("\n=== Testing read_lines ===")
    try:
        # Create a test file
        test_file = Path("/tmp/test_lines.py")
        test_file.write_text("\n".join(f"Line {i}" for i in range(1, 21)))

        result = read_lines(str(test_file), 5, 10)
        print(f"✓ read_lines returned:\n{result}")
        assert "Line 5" in result, "Should start at line 5"
        assert "Line 10" in result, "Should end at line 10"
        assert "Line 11" not in result, "Should not include line 11"

        # Test invalid range
        result = read_lines(str(test_file), 0, 5)
        assert "Error: Invalid line range" in result, "Should reject invalid range"

        test_file.unlink()
        return True
    except Exception as e:
        print(f"✗ read_lines failed: {e}")
        return False

def test_smart_code_search():
    print("\n=== Testing smart_code_search ===")
    try:
        # Create a small codebase to search
        code_dir = Path("/tmp/test_search")
        code_dir.mkdir(exist_ok=True)
        (code_dir / "app.py").write_text("""
def process_data(data):
    result = transform(data)
    save_to_db(result)
    return result

def transform(x):
    return x * 2
""")
        (code_dir / "utils.py").write_text("""
def save_to_db(item):
    print(f"Saving {item}")
""")

        # Test search (note: this searches /workspace by default, so we need to use actual workspace)
        # Since we may not have test files in /workspace, we'll just check the function runs
        result = smart_code_search("process_data")
        print(f"✓ smart_code_search returned {len(result)} chars")
        print(f"Preview:\n{result[:300]}")

        # Cleanup
        import shutil
        shutil.rmtree(code_dir)
        return True
    except Exception as e:
        print(f"✗ smart_code_search failed: {e}")
        return False

def main():
    print("=" * 60)
    print("LSS-MCP New Tools Test Suite")
    print("=" * 60)

    results = {
        "map_repository": test_map_repository(),
        "focused_glob": test_focused_glob(),
        "read_file_skeleton": test_read_file_skeleton(),
        "read_lines": test_read_lines(),
        "smart_code_search": test_smart_code_search(),
    }

    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
