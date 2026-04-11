"""Answer parsing utilities for extracting prompt candidates from AgentResult."""

import json
import re


def parse_candidates(answer: str, num_candidates: int) -> list[str]:
    """Parse an agent answer string into a list of prompt candidates.

    Tries formats in order: JSON array, numbered list, delimiter-based, fallback.
    Raises RuntimeError if no candidates can be extracted.
    """
    if not answer or not answer.strip():
        raise RuntimeError("Agent returned an empty answer — no candidates to parse.")

    text = answer.strip()

    # 1. JSON array
    candidates = _try_json_array(text)
    if candidates:
        return candidates

    # 2. Numbered list (1. ..., 2. ..., etc.)
    candidates = _try_numbered_list(text)
    if candidates:
        return candidates

    # 3. Delimiter-based (--- or ===)
    candidates = _try_delimiter(text)
    if candidates:
        return candidates

    # 4. Fallback: entire answer as single candidate
    return [text]


def _try_json_array(text: str) -> list[str] | None:
    """Try to parse as a JSON array of strings."""
    # Find the first [ and last ] to handle surrounding text
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, list):
            candidates = [str(c).strip() for c in parsed if str(c).strip()]
            return candidates if candidates else None
    except (json.JSONDecodeError, ValueError):
        pass
    return None


_NUMBERED_RE = re.compile(r"^\d+[\.\)]\s+", re.MULTILINE)


def _try_numbered_list(text: str) -> list[str] | None:
    """Try to parse as a numbered list (1. ..., 2. ..., etc.)."""
    matches = list(_NUMBERED_RE.finditer(text))
    if len(matches) < 2:
        return None

    candidates: list[str] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        candidate = text[start:end].strip()
        if candidate:
            candidates.append(candidate)

    return candidates if candidates else None


def _try_delimiter(text: str) -> list[str] | None:
    """Try to split on --- or === delimiters."""
    for delim in ("---", "==="):
        if delim in text:
            parts = [p.strip() for p in text.split(delim) if p.strip()]
            if len(parts) >= 2:
                return parts
    return None
