"""Tests for token CSV parser."""

from llm_stress_tester.schemas import TokenEntry
from llm_stress_tester.utils.token_csv import parse_token_csv


def test_parse_empty_csv():
    tokens, errors = parse_token_csv("")
    assert tokens == []
    assert errors == []


def test_parse_csv_with_header():
    text = "token,label\nsk-1,user-a\nsk-2,user-b"
    tokens, errors = parse_token_csv(text)
    assert len(tokens) == 2
    assert tokens[0] == TokenEntry(token="sk-1", label="user-a")
    assert tokens[1] == TokenEntry(token="sk-2", label="user-b")
    assert errors == []


def test_parse_csv_no_header():
    text = "sk-1\nsk-2,alternate"
    tokens, errors = parse_token_csv(text)
    assert len(tokens) == 2
    assert tokens[0].token == "sk-1"
    assert tokens[0].label == "token-1"
    assert tokens[1].token == "sk-2"
    # No "token" header means col 2 not parsed as label
    assert tokens[1].label == "token-2"


def test_parse_csv_invalid_row():
    text = "token,label\nsk-1,user-a\n,missing"
    tokens, errors = parse_token_csv(text)
    assert len(tokens) == 1
    assert len(errors) == 1
    assert "missing" in errors[0].lower()
