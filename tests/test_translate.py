"""Tests for the translation engine — no API calls required."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from translate import verify_json, verify_char_limits, load_notes, placeholders
from locales import SUPPORTED_LOCALES, LOCALE_CODES, DEFAULT_LOCALE, RTL_LOCALES


def test_locale_set_size():
    assert len(SUPPORTED_LOCALES) == 50


def test_locale_codes_unique():
    assert len(LOCALE_CODES) == len(set(LOCALE_CODES))


def test_default_locale_is_english():
    assert DEFAULT_LOCALE == "en"
    assert LOCALE_CODES[0] == "en"


def test_rtl_locales_are_in_set():
    codes = set(LOCALE_CODES)
    for rtl in RTL_LOCALES:
        assert rtl in codes, f"RTL locale {rtl} not in SUPPORTED_LOCALES"


def test_verify_json_passes_correct():
    en = {"greeting": "Hello {name}", "bye": "Goodbye"}
    tr = {"greeting": "Hola {name}", "bye": "Adiós"}
    assert verify_json(en, tr) == []


def test_verify_json_catches_missing_keys():
    en = {"a": "A", "b": "B"}
    tr = {"a": "AA"}
    problems = verify_json(en, tr)
    assert any("missing" in p for p in problems)


def test_verify_json_catches_extra_keys():
    en = {"a": "A"}
    tr = {"a": "AA", "b": "BB"}
    problems = verify_json(en, tr)
    assert any("invented" in p for p in problems)


def test_verify_json_catches_placeholder_drift():
    en = {"msg": "Hello {name}, you have {count} items"}
    tr = {"msg": "Hola {nombre}, tienes {count} cosas"}
    problems = verify_json(en, tr)
    assert any("placeholder" in p.lower() for p in problems)


def test_verify_char_limits():
    tr = {"subtitle": "This is way too long for a subtitle field in the store"}
    problems = verify_char_limits(tr, {"subtitle": 30})
    assert len(problems) == 1
    assert "subtitle" in problems[0]


def test_verify_char_limits_passes():
    tr = {"subtitle": "Short"}
    problems = verify_char_limits(tr, {"subtitle": 30})
    assert problems == []


def test_placeholders():
    assert placeholders("Hello {name}, {count} items") == {"name", "count"}
    assert placeholders("No placeholders here") == set()
    assert placeholders("{a} and {a}") == {"a"}


def test_projects_json_valid():
    projects = json.loads(
        (Path(__file__).resolve().parents[1] / "projects.json").read_text())
    assert "_readme" in projects
    for key, cfg in projects.items():
        if key.startswith("_"):
            continue
        assert "repo" in cfg, f"{key} missing repo"
        assert "format" in cfg, f"{key} missing format"
        assert cfg["format"] in ("json", "arb", "html"), f"{key} bad format"
        assert "sources" in cfg, f"{key} missing sources"
        for src in cfg["sources"]:
            assert "name" in src
            assert "kind" in src
            assert "english" in src
            assert "model" in src


def test_load_notes_empty():
    result = load_notes(None, {"key1"})
    assert result == ""


def test_load_notes_nonexistent():
    result = load_notes(Path("/nonexistent/file.json"), {"key1"})
    assert result == ""
