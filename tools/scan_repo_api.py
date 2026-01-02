#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_EXCLUDES = {
    ".git", ".hg", ".svn",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "venv", ".venv", "env", ".env",
    "node_modules",
    "dist", "build", ".tox", ".eggs",
    ".idea", ".vscode", "_archive"
}


def safe_unparse(node: Optional[ast.AST]) -> Optional[str]:
    if node is None:
        return None
    try:
        return ast.unparse(node)  # Python 3.9+
    except Exception:
        return node.__class__.__name__


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def should_skip_path(path: Path, exclude_names: set[str]) -> bool:
    parts = set(path.parts)
    return any(part in exclude_names for part in parts)


def doc_summary(doc: Optional[str]) -> Optional[str]:
    if not doc:
        return None
    stripped = doc.strip()
    if not stripped:
        return None
    for line in stripped.splitlines():
        if line.strip():
            return line.strip()
    return None


def extract_returns_from_docstring(doc: Optional[str]) -> Optional[str]:
    if not doc:
        return None
    text = doc.strip()
    if not text:
        return None

    # Google style
    m = re.search(r"\nReturns:\s*\n(?P<body>(?:\s{2,}.*\n?)+)", "\n" + text, flags=re.IGNORECASE)
    if m:
        body = m.group("body").rstrip()
        return "\n".join(line.strip() for line in body.splitlines()).strip() or None

    # Numpy style
    m = re.search(
        r"\nReturns\s*\n[-=]{3,}\s*\n(?P<body>(?:.*\n?)+)",
        "\n" + text,
        flags=re.IGNORECASE,
    )
    if m:
        body = m.group("body")
        lines = body.splitlines()
        kept: List[str] = []
        for i, line in enumerate(lines):
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                if re.match(r"^[A-Za-z][A-Za-z0-9 _-]*\s*$", line.strip()) and re.match(r"^[-=]{3,}\s*$", nxt.strip()):
                    break
            kept.append(line)
        cleaned = "\n".join(l.strip() for l in kept).strip()
        return cleaned or None

    # ReST-ish
    m = re.search(r":return[s]?:\s*(?P<body>.+)", text, flags=re.IGNORECASE)
    if m:
        return m.group("body").strip() or None

    return None


@dataclass
class Context:
    file_path: str
    module: str


class APIScanner(ast.NodeVisitor):
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.items: List[Dict[str, Any]] = []

        # Track nesting:
        self.class_stack: List[str] = []
        self.func_stack: List[str] = []  # outer function names

    def _enclosing(self) -> List[str]:
        # e.g. ["MyClass", "outer_func", "inner_func_parent"]
        return self.class_stack + self.func_stack

    def _qualname(self, name: str) -> str:
        parts = self._enclosing() + [name]
        return ".".join(parts) if parts else name

    def _decorators(self, node: ast.AST) -> List[str]:
        decs: List[str] = []
        for d in getattr(node, "decorator_list", []) or []:
            s = safe_unparse(d)
            if s:
                decs.append(s)
        return decs

    def _args_to_params(self, args: ast.arguments) -> List[Dict[str, Any]]:
        params: List[Dict[str, Any]] = []

        def add_param(kind: str, a: ast.arg, default_node: Optional[ast.AST]) -> None:
            params.append({
                "name": a.arg,
                "kind": kind,
                "annotation": safe_unparse(a.annotation),
                "default": safe_unparse(default_node),
            })

        posonly = list(args.posonlyargs or [])
        normal = list(args.args or [])
        combined = posonly + normal

        defaults = list(args.defaults or [])
        padding = [None] * (len(combined) - len(defaults))
        combined_defaults: List[Optional[ast.AST]] = padding + defaults

        for a, d in zip(posonly, combined_defaults[:len(posonly)]):
            add_param("posonly", a, d)
        for a, d in zip(normal, combined_defaults[len(posonly):]):
            add_param("positional_or_keyword", a, d)

        if args.vararg is not None:
            add_param("vararg", args.vararg, None)

        for a, d in zip(args.kwonlyargs or [], args.kw_defaults or []):
            add_param("kwonly", a, d)

        if args.kwarg is not None:
            add_param("kwarg", args.kwarg, None)

        return params

    def _function_item(self, node: ast.AST, is_async: bool) -> Dict[str, Any]:
        assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        doc = ast.get_docstring(node)
        params = self._args_to_params(node.args)

        kind = "method" if self.class_stack else "function"
        if self.func_stack:
            # any function inside another function (even inside a method) is nested
            kind = "nested_function"

        return {
            "kind": kind,
            "async": is_async,
            "name": node.name,
            "qualname": self._qualname(node.name),
            "enclosing": self._enclosing(),
            "module": self.ctx.module,
            "file": self.ctx.file_path,
            "lineno": getattr(node, "lineno", None),
            "end_lineno": getattr(node, "end_lineno", None),
            "decorators": self._decorators(node),
            "parameters": params,
            "return_annotation": safe_unparse(node.returns),
            "doc": {
                "summary": doc_summary(doc),
                "returns": extract_returns_from_docstring(doc),
                "raw": doc,
            },
        }

    def _class_item(self, node: ast.ClassDef) -> Dict[str, Any]:
        doc = ast.get_docstring(node)
        bases = [safe_unparse(b) for b in node.bases] if node.bases else []
        keywords = []
        for kw in node.keywords or []:
            if kw.arg is None:
                keywords.append(safe_unparse(kw.value))
            else:
                keywords.append(f"{kw.arg}={safe_unparse(kw.value)}")

        return {
            "kind": "class",
            "name": node.name,
            "qualname": self._qualname(node.name),
            "enclosing": self._enclosing(),
            "module": self.ctx.module,
            "file": self.ctx.file_path,
            "lineno": getattr(node, "lineno", None),
            "end_lineno": getattr(node, "end_lineno", None),
            "decorators": self._decorators(node),
            "bases": [b for b in bases if b],
            "keywords": [k for k in keywords if k],
            "doc": {
                "summary": doc_summary(doc),
                "raw": doc,
            },
            "methods": [],
            "init_signature": None,
        }

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        cls = self._class_item(node)

        # Push class context
        self.class_stack.append(node.name)

        # Visit class body to collect methods + nested defs
        for stmt in node.body:
            self.visit(stmt)

        # Pop class context
        self.class_stack.pop()

        # Record class (methods are recorded separately as items too,
        # but we also keep a class-level "methods" list for convenience)
        # We'll rebuild the methods list from items belonging to this class scope.
        # For simplicity: keep methods list empty here; caller can group by qualname prefix if desired.
        self.items.append(cls)

    def _record_function_and_visit_body(self, node: ast.AST, is_async: bool) -> None:
        item = self._function_item(node, is_async=is_async)
        self.items.append(item)

        # Push function context so we catch nested defs inside it
        self.func_stack.append(item["name"])
        try:
            for stmt in getattr(node, "body", []) or []:
                self.visit(stmt)
        finally:
            self.func_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._record_function_and_visit_body(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._record_function_and_visit_body(node, is_async=True)


def module_from_path(repo_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(repo_root)
    parts = list(rel.parts)
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(p for p in parts if p)


def scan_file(repo_root: Path, py_path: Path) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    try:
        src = read_text(py_path)
        tree = ast.parse(src, filename=str(py_path))
        ctx = Context(
            file_path=str(py_path.relative_to(repo_root)),
            module=module_from_path(repo_root, py_path),
        )
        scanner = APIScanner(ctx)
        scanner.visit(tree)
        return scanner.items, None
    except SyntaxError as e:
        return [], f"SyntaxError: {e}"
    except Exception as e:
        return [], f"Error: {type(e).__name__}: {e}"


def iter_python_files(repo_root: Path, exclude_names: set[str]) -> List[Path]:
    py_files: List[Path] = []
    for root, dirs, files in os.walk(repo_root):
        root_path = Path(root)
        dirs[:] = [d for d in dirs if d not in exclude_names]
        if should_skip_path(root_path, exclude_names):
            continue
        for f in files:
            if f.endswith(".py"):
                p = root_path / f
                if not should_skip_path(p, exclude_names):
                    py_files.append(p)
    return py_files


def is_private_name(name: str) -> bool:
    return name.startswith("_") and name not in {"__init__", "__call__"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract functions/classes (including nested) from a Python repo into JSON.")
    parser.add_argument("--repo", type=str, default=".", help="Path to repository root (scan starts here)")
    parser.add_argument("--out", type=str, default="artifacts/api_index.json", help="Output JSON file path")
    parser.add_argument("--exclude", nargs="*", default=None, help="Directory names to exclude")
    parser.add_argument("--include-private", action="store_true", help="Include names starting with '_'")
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    out_path = Path(args.out).resolve()
    exclude_names = set(args.exclude) if args.exclude is not None else set(DEFAULT_EXCLUDES)

    py_files = iter_python_files(repo_root, exclude_names)

    all_items: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for py_path in py_files:
        items, err = scan_file(repo_root, py_path)
        if err:
            errors.append({"file": str(py_path.relative_to(repo_root)), "error": err})
            continue

        if not args.include_private:
            filtered: List[Dict[str, Any]] = []
            for it in items:
                name = it.get("name") or ""
                if isinstance(name, str) and is_private_name(name):
                    continue
                filtered.append(it)
            items = filtered

        all_items.extend(items)

    result = {
        "repo": str(repo_root),
        "scanned_files_count": len(py_files),
        "items_count": len(all_items),
        "generated_by": "scan_repo_api.py",
        "items": all_items,
        "errors": errors,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path} with {result['items_count']} items ({len(errors)} file errors).")


if __name__ == "__main__":
    main()
