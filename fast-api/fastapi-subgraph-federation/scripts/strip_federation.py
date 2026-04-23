#!/usr/bin/env python3
"""Strip Apollo Federation directives from a supergraph schema.

Produces a clean client-facing schema that standard GraphQL tools can parse.

Usage:
    python scripts/strip_federation.py router/supergraph.graphql > graphql/client-schema.graphql
"""
from __future__ import annotations

import re
import sys


# Federation-only type/scalar/enum/input names to remove entirely
_FEDERATION_NAMES = {
    "join__ContextArgument",
    "join__DirectiveArguments",
    "join__FieldSet",
    "join__FieldValue",
    "join__Graph",
    "link__Import",
    "link__Purpose",
}

# Regex: @join__xxx(...) or @link(...) annotations (possibly multi-arg, nested parens)
_DIRECTIVE_RE = re.compile(
    r'\s*@(?:join__\w+|link)\([^)]*\)', re.DOTALL
)


def _is_federation_directive_def(line: str) -> bool:
    """Return True if the line starts a directive definition we want to drop."""
    return line.startswith("directive @join__") or line.startswith("directive @link")


def _starts_federation_block(line: str) -> bool:
    """Return True if the line starts a type/scalar/enum/input block we want to drop."""
    for name in _FEDERATION_NAMES:
        if re.match(rf'^(type|input|enum|scalar)\s+{re.escape(name)}\b', line):
            return True
    return False


def strip(schema: str) -> str:
    lines = schema.splitlines()
    out: list[str] = []
    skip_until_close = False
    skip_directive = False

    for line in lines:
        stripped = line.strip()

        # Skip federation directive definitions (may span multiple lines)
        if skip_directive:
            if stripped.endswith(')') or 'on ' in stripped:
                skip_directive = False
            continue
        if _is_federation_directive_def(stripped):
            if 'on ' not in stripped:
                skip_directive = True
            continue

        # Skip entire federation type/enum/scalar/input blocks
        if skip_until_close:
            if stripped == '}':
                skip_until_close = False
            continue
        if _starts_federation_block(stripped):
            if '{' in stripped:
                skip_until_close = True
            continue
        # scalar on single line
        for name in _FEDERATION_NAMES:
            if stripped == f'scalar {name}':
                break
        else:
            # Strip inline @join__xxx(...) and @link(...) from the line
            cleaned = _DIRECTIVE_RE.sub('', line).rstrip()
            if cleaned.strip():
                out.append(cleaned)

    # Collapse multiple blank lines
    result: list[str] = []
    for line in out:
        if line.strip() == '' and result and result[-1].strip() == '':
            continue
        result.append(line)

    return '\n'.join(result) + '\n'


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <supergraph.graphql>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        schema = f.read()

    print(strip(schema), end='')


if __name__ == '__main__':
    main()
