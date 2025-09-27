import ast
from pathlib import Path
import argparse
import sys

def find_cast_calls_in_file(path: Path):
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "cast":
                    # try to extract a useful source snippet
                    snippet = ast.get_source_segment(src, node) or src.splitlines()[node.lineno - 1].strip()
                    yield node.lineno, node.col_offset, snippet

def iter_py(root: Path):
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts or p.match("*/.venv/*") or ".git" in p.parts:
            continue
        yield p

def main():
    ap = argparse.ArgumentParser(description="Find function calls with keyword arg named 'cast'")
    ap.add_argument("root", nargs="?", default=".", help="Repository root to search (default: .)")
    args = ap.parse_args()

    root = Path(args.root)
    any_found = False
    for py in iter_py(root):
        for lineno, col, snippet in find_cast_calls_in_file(py):
            any_found = True
            print(f"{py}:{lineno}:{col}: {snippet}")
    if not any_found:
        print("No cast= callsites found.", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()