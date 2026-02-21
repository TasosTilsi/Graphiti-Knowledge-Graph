"""TOON encoding utilities for MCP server responses.

TOON (Token-Oriented Object Notation) provides ~40% token reduction vs JSON for
uniform arrays of objects (search results, entity lists).

IMPORTANT: All logging in this module goes to stderr only. The MCP stdio transport
uses stdout for JSON-RPC messages — any stdout writes corrupt the protocol.

See: https://github.com/toon-format/toon
"""
import json
import re

from toon import encode

__all__ = ["encode_response", "trim_to_token_budget"]


def encode_response(data: list[dict] | dict | str) -> str:
    """Encode a CLI response for MCP tool return.

    Applies TOON encoding only when it saves tokens: uniform arrays of 3+ items.
    For single dicts, short lists, or plain strings, returns JSON (TOON header
    overhead exceeds savings for tiny responses — Pitfall 6 in research).

    Args:
        data: A list of dicts (search results, entity lists), a single dict
              (one entity), or a plain string (status messages, errors).

    Returns:
        TOON-encoded string for 3+ item lists, JSON string otherwise.
    """
    if isinstance(data, list) and len(data) >= 3:
        # TOON header overhead pays off at 3+ items per research Pitfall 6
        return encode(data)
    # Single dict, short list (<3 items), or plain string: return JSON
    return json.dumps(data, indent=2)


def trim_to_token_budget(text: str, token_budget: int) -> str:
    """Trim TOON-encoded text to fit within an approximate token budget.

    Uses 4 chars-per-token approximation (sufficient for budget enforcement;
    Anthropic does not ship a local tokenizer for Claude 3+).

    Strategy:
    - Preserve TOON header lines (lines starting with '[' or containing '{')
    - Remove data rows from the front (oldest first, most recent preserved)
    - Update the TOON row count in the header after trimming

    Args:
        text: TOON-encoded or plain text string to trim.
        token_budget: Maximum allowed tokens (approximate).

    Returns:
        Trimmed text within the character budget, with updated TOON header count.
    """
    char_budget = token_budget * 4  # 4 chars/token approximation

    if len(text) <= char_budget:
        return text

    lines = text.split("\n")

    # Separate TOON header lines from data rows.
    # TOON header: first line(s) starting with '[' or containing '{'.
    header_lines: list[str] = []
    data_lines: list[str] = []
    in_header = True
    for line in lines:
        if in_header and (line.startswith("[") or "{" in line):
            header_lines.append(line)
        else:
            in_header = False
            data_lines.append(line)

    # Remove oldest data rows (from front) until within budget
    while data_lines and len("\n".join(header_lines + data_lines)) > char_budget:
        data_lines.pop(0)

    # Update the TOON row count in the header.
    # TOON header format: [N,]{field1,field2}: where N is the row count.
    # After trimming, update N to reflect the actual remaining rows.
    remaining_row_count = len(data_lines)
    updated_header: list[str] = []
    for line in header_lines:
        # Match [N,] or [N] pattern and update with new count
        updated_line = re.sub(r"\[(\d+),?\]", f"[{remaining_row_count},]", line)
        updated_header.append(updated_line)

    return "\n".join(updated_header + data_lines)
