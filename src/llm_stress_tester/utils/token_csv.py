"""Token CSV parser utility."""

from __future__ import annotations

import csv
import io

from llm_stress_tester.schemas import TokenEntry


def parse_token_csv(text: str) -> tuple[list[TokenEntry], list[str]]:
    """Parse token CSV from textarea.

    Expects optional header 'token,label'.
    Returns (tokens, errors).
    If no header provided, treats first column as token, labels auto-generated.
    """
    errors: list[str] = []
    tokens: list[TokenEntry] = []

    if not text.strip():
        return tokens, errors

    reader = csv.reader(io.StringIO(text.strip()))
    rows = list(reader)

    if not rows:
        return tokens, errors

    header = [h.strip().lower() for h in rows[0]]

    start_idx = 0
    if "token" in header and "label" in header:
        token_col = header.index("token")
        label_col = header.index("label") if header.index("label") != token_col else token_col + 1
        start_idx = 1
        has_header = True
    else:
        has_header = False
        token_col = 0
        label_col = 1 if len(rows[0]) >= 2 else 0

    for i, row in enumerate(rows[start_idx:], start=start_idx + 1):
        token = row[token_col].strip() if token_col < len(row) else ""

        if not token:
            errors.append(f"Row {i}: missing token value")
            continue

        if has_header and label_col < len(row):
            label = row[label_col].strip()
        elif has_header:
            label = f"user-{i}"
        else:
            label = f"token-{i}"

        tokens.append(TokenEntry(token=token, label=label))

    return tokens, errors
