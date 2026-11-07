import ast
import re
import string
from pathlib import Path

import pytest

from zoho_sync import engine, i18n
from zoho_sync.zoho import DATA_CENTERS

ROOT = Path(__file__).resolve().parent.parent
CODE = [ROOT / "app.py", *sorted((ROOT / "zoho_sync").glob("*.py"))]
CJK = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")


def placeholders(text: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def literal_tr_keys():
    for path in CODE:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "tr" and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    yield path.name, arg.value


def dynamic_keys():
    yield from (f"doctype.{t.key}" for t in engine.DOC_TYPES)
    yield from (f"status.{s}" for s in engine.STATUSES)
    yield from (f"outcome.{o}" for o in (*engine.WRITTEN, engine.SKIPPED, engine.UNCHANGED, engine.FAILED))
    yield from (f"dc.{k}" for k in DATA_CENTERS)
    yield from (f"sync.conflict.{k}" for k in ("version", "overwrite", "skip"))
    yield from ("conn.missing.body", "conn.missing.body_code", "conn.connecting", "conn.connecting_browser")


def test_every_used_key_exists():
    missing = sorted({f"{f}: {k}" for f, k in literal_tr_keys() if k not in i18n.CATALOG}
                     | {k for k in dynamic_keys() if k not in i18n.CATALOG})
    assert not missing, missing


@pytest.mark.parametrize("key", sorted(i18n.CATALOG))
def test_all_languages_present_with_same_placeholders(key):
    row = i18n.CATALOG[key]
    assert len(row) == len(i18n.LANGUAGES) and all(row), key
    assert len({frozenset(placeholders(t)) for t in row}) == 1, key


def test_no_hardcoded_cjk_outside_catalog():
    offenders = []
    for path in CODE:
        if path.name == "i18n.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and CJK.search(node.value):
                if not (isinstance(getattr(node, "parent", None), ast.Expr)):  # ignore docstrings below
                    offenders.append(f"{path.name}:{node.lineno}: {node.value[:40]}")
    # docstrings/comments are allowed to mention Chinese terms; real UI strings are not
    docstring_lines = set()
    for path in CODE:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
                docstring_lines.add(f"{path.name}:{node.body[0].lineno}")
    offenders = [o for o in offenders if ":".join(o.split(":")[:2]) not in docstring_lines]
    assert not offenders, offenders


@pytest.mark.parametrize("tags,expected", [
    (["zh-Hant-HK", "en"], "zh-Hant"), (["zh-TW"], "zh-Hant"), (["zh-HK"], "zh-Hant"),
    (["zh-Hans-CN"], "zh-Hans"), (["zh-CN"], "zh-Hans"), (["ja-JP"], "ja"),
    (["fr-FR", "ja"], "ja"), (["de-DE"], "en"), ([], "en"),
])
def test_detect(tags, expected):
    assert i18n.detect(tags) == expected


def test_tr_switches_language_and_formats():
    try:
        i18n.set_language("ja")
        assert i18n.tr("sync.done", n=3) == "3 件のファイルを同期しました"
        i18n.set_language("zh-Hans")
        assert i18n.tr("doctype.invoices") == "发票"
        assert i18n.tr("status.unknown_code", default="unknown_code") == "unknown_code"
        i18n.set_language("xx")
        assert i18n.current() == "en"
    finally:
        i18n.set_language("en")
