from __future__ import annotations


def truncate_text(value: str, max_length: int) -> str:
    text = value.strip()
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return f"{text[: max_length - 3].rstrip()}..."
