"""
Lightweight SQL template renderer with parameter placeholders.

Usage: render_sql("SELECT * WHERE dt < '{cutoff_date}'", {"cutoff_date": "2025-05-01"})

Behavior:
- Replaces placeholders like {cutoff_date} with provided values.
- If any placeholders remain unresolved after rendering, raises ValueError to fail fast.
"""
from __future__ import annotations
from typing import Any, Dict
import re


class _SafeDict(dict):
    def __missing__(self, key):
        # Leave unresolved placeholders intact so we can detect them post-format
        return "{" + key + "}"


def render_sql(sql: str, params: Dict[str, Any] | None = None, *, strict: bool = True) -> str:
    """Render SQL template with params and optionally enforce all placeholders are resolved.

    Args:
        sql: SQL string with placeholders like {name}
        params: Mapping of placeholder names to values (converted to str via format)
        strict: When True (default), raise ValueError if any placeholders remain unresolved

    Returns:
        Rendered SQL string
    """
    params = params or {}
    rendered = sql.format_map(_SafeDict(params))

    if strict:
        # Detect unresolved placeholders of the form {identifier}
        unresolved = re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", rendered)
        if unresolved:
            missing = sorted(set(p.strip("{}") for p in unresolved))
            raise ValueError(
                "Unresolved SQL parameters: "
                + ", ".join(missing)
                + ". Provide them via environment variables or function arguments."
            )

    return rendered


__all__ = ["render_sql"]
