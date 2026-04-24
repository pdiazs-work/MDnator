"""
Heuristic plain-text → Markdown formatter.

Detects implicit structure (headings, lists, code blocks, paragraphs)
and emits well-formed Markdown that renders nicely in Obsidian or any
Markdown viewer.
"""

import re


def _looks_like_heading(line: str) -> bool:
    """Short line, title-case or ALL-CAPS, no sentence-ending punctuation mid-line."""
    stripped = line.strip()
    if not stripped or len(stripped) > 80:
        return False
    if stripped.endswith((".", ",", ";", "?")):
        return False
    words = stripped.split()
    if len(words) == 0 or len(words) > 12:
        return False
    # ALL CAPS heading
    if stripped.isupper() and len(words) >= 1:
        return True
    # Title Case (most words capitalised, >= 2 words)
    if (
        len(words) >= 2
        and sum(1 for w in words if w and w[0].isupper()) >= len(words) * 0.6
    ):
        return True
    return False


def _looks_like_list_item(line: str) -> bool:
    stripped = line.strip()
    return bool(
        re.match(r"^[-*•·▪▸►>]\s+\S", stripped) or re.match(r"^\d+[.)]\s+\S", stripped)
    )


def _normalize_list_item(line: str) -> str:
    stripped = line.strip()
    # Convert bullet variants to -
    m = re.match(r"^[-*•·▪▸►>]\s+(.*)", stripped)
    if m:
        return f"- {m.group(1)}"
    # Keep numbered lists as-is (normalise punctuation)
    m = re.match(r"^(\d+)[.)]\s+(.*)", stripped)
    if m:
        return f"{m.group(1)}. {m.group(2)}"
    return stripped


def _is_code_fence(line: str) -> bool:
    return bool(re.match(r"^\s{4,}\S", line) or re.match(r"^`{3,}", line.strip()))


def _heading_level(line: str, seen_headings: int) -> int:
    """Assign heading level based on order of appearance (H1 first, then H2, H3)."""
    if seen_headings == 0:
        return 1
    if seen_headings <= 3:
        return 2
    return 3


def format_plain_text(text: str) -> str:
    """Convert unstructured plain text to organised Markdown."""
    if not text or not text.strip():
        return ""

    lines = text.splitlines()
    output: list[str] = []
    seen_headings = 0
    in_code_block = False
    i = 0

    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        # --- Code block toggle ---
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            output.append(raw)
            i += 1
            continue

        if in_code_block:
            output.append(raw)
            i += 1
            continue

        # --- Empty line → paragraph break ---
        if not stripped:
            if output and output[-1] != "":
                output.append("")
            i += 1
            continue

        # --- Already has Markdown heading ---
        if re.match(r"^#{1,6}\s", stripped):
            output.append(stripped)
            seen_headings += 1
            i += 1
            continue

        # --- Heuristic heading ---
        if _looks_like_heading(stripped):
            level = _heading_level(stripped, seen_headings)
            if output and output[-1] != "":
                output.append("")
            output.append(f"{'#' * level} {stripped}")
            seen_headings += 1
            output.append("")
            i += 1
            continue

        # --- Indented code block (4+ spaces) ---
        if re.match(r"^\s{4,}\S", raw) and not _looks_like_list_item(raw):
            if not output or output[-1] != "```":
                if output and output[-1] != "":
                    output.append("")
                output.append("```")
            output.append(raw.rstrip())
            # Peek ahead — continue code block if next line is also indented
            if i + 1 < len(lines) and re.match(r"^\s{4,}", lines[i + 1]):
                i += 1
                continue
            output.append("```")
            output.append("")
            i += 1
            continue

        # --- List item ---
        if _looks_like_list_item(raw):
            output.append(_normalize_list_item(raw))
            i += 1
            continue

        # --- Regular paragraph text ---
        output.append(stripped)
        i += 1

    # Clean up: collapse multiple blank lines into one
    result_lines: list[str] = []
    prev_blank = False
    for line in output:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue
        result_lines.append(line)
        prev_blank = is_blank

    # Strip leading/trailing blanks
    while result_lines and result_lines[0] == "":
        result_lines.pop(0)
    while result_lines and result_lines[-1] == "":
        result_lines.pop()

    return "\n".join(result_lines)
