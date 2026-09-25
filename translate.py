#!/usr/bin/env python3
"""Centralized translation engine for all Spencer Fields Software projects.

NOT RUN AUTOMATICALLY — it calls the Anthropic API and therefore spends money.
Run it deliberately, and re-run only for locales that are missing or that
have gained keys.

Usage:
    python translate.py --project dawnlist --dry-run
    python translate.py --project dawnlist --source "App UI catalog" --only fr,de,es
    python translate.py --project dawnlist --fill
    python translate.py --project all --dry-run
    python translate.py --project easypost-mobile --force --only ar

Flags:
    --project    Which project to translate (or "all")
    --source     Which source within the project (optional, defaults to all)
    --only       Comma-separated locale codes to limit the run
    --fill       Top up existing catalogs with newly-added keys only
    --force      Overwrite existing translations
    --dry-run    Show what would be done without making API calls
    --output     Write output to a local staging directory instead of
                 directly into a cloned repo (default: output/)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from locales import (
    DEFAULT_LOCALE,
    LOCALE_NAMES,
    RTL_LOCALES,
    SUPPORTED_LOCALES,
)

PLACEHOLDER = re.compile(r"\{(\w+)\}")
MAX_TOKENS = 64000
PROJECTS_FILE = Path(__file__).resolve().parent / "projects.json"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

CATALOG_PROMPT = """\
Translate this software UI catalogue into {language} ({code}).

Rules:
- Return ONLY a JSON object with exactly the same keys. No commentary.
- Preserve every {{placeholder}} token exactly as written, including its name.
  A dropped or renamed placeholder crashes the app in front of the user.
- These are UI strings for {description} Keep them short enough to
  fit a button or a column header.
- Product names are never translated, but transliterate them if the target
  script is non-Latin.
- Use the register a professional desktop/mobile application would use
  in {language}.
{notes}
Catalogue:
{catalogue}"""

ARB_PROMPT = """\
Translate this Flutter ARB catalogue into {language} ({code}).

Rules:
- Return ONLY a JSON object with exactly the same message keys. No commentary.
- Do NOT include @-metadata keys (keys starting with @). Only the message keys.
- Preserve every {{placeholder}} token exactly as written, including its name.
  A dropped or renamed placeholder crashes the app in front of the user.
- These are UI strings for {description} Keep them short enough to
  fit a button or a column header.
- Product names are never translated, but transliterate them if the target
  script is non-Latin.
- Use the register a professional mobile application would use in {language}.
{notes}
Catalogue:
{catalogue}"""

LISTING_PROMPT = """\
Translate this app store listing into {language} ({code}).

Rules:
- Return ONLY a JSON object with exactly the same keys. No commentary.
- This is a store listing for {description}
- Use the register that app store listings use in {language}: professional,
  clear, and slightly promotional.
- Product names are never translated.
- Do not soften absolute claims: "never sends" must remain absolute.
- Preserve every {{placeholder}} token exactly as written.
{char_limits}
Listing:
{catalogue}"""

HTML_PROMPT = """\
Translate this HTML page into {language} ({code}).

Rules:
- Return the complete HTML document with all visible text translated.
- Set the <html lang="..."> attribute to "{code}".{rtl}
- Update <title>, <meta name="description">, og:title, og:description,
  og:locale to the translated values.
- Update <link rel="canonical"> to the locale-specific URL.
- Do NOT translate product names (Easy-Post Desktop, Wren, Dawnlist),
  URLs, or code/markup.
- Preserve all HTML structure, CSS, JavaScript, and SVG exactly.
- The language picker and hreflang links (between <!-- i18n:begin --> and
  <!-- i18n:end --> markers) should remain unchanged.
- Use the register a professional software company website would use
  in {language}.

HTML:
{catalogue}"""


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def make_client():
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit(
            "No API key: set ANTHROPIC_API_KEY environment variable.\n"
            "In GitHub Actions, store it as a repository secret."
        )
    return anthropic.Anthropic(api_key=key)


def placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text))


def verify_json(english: dict, translated: dict) -> list[str]:
    problems = []
    missing = set(english) - set(translated)
    if missing:
        problems.append(f"missing keys: {sorted(missing)}")
    extra = set(translated) - set(english)
    if extra:
        problems.append(f"invented keys: {sorted(extra)}")
    for key in set(english) & set(translated):
        want = placeholders(english[key])
        got = placeholders(translated[key])
        if want != got:
            problems.append(
                f"{key}: placeholders {sorted(want)} became {sorted(got)}")
    return problems


def verify_char_limits(translated: dict, limits: dict) -> list[str]:
    problems = []
    for field, max_len in limits.items():
        if field in translated and len(translated[field]) > max_len:
            problems.append(
                f"{field}: {len(translated[field])} chars exceeds "
                f"limit of {max_len}")
    return problems


def load_notes(notes_path: Path | None, keys: set) -> str:
    if not notes_path or not notes_path.exists():
        return ""
    notes = json.loads(notes_path.read_text(encoding="utf-8"))
    relevant = {k: v for k, v in notes.items()
                if k in keys and not k.startswith("_")}
    if not relevant:
        return ""
    lines = "\n".join(f"  {k}: {v}" for k, v in sorted(relevant.items()))
    return ("\nContext for particular keys — where the string appears, and "
            "what it must not be narrowed to:\n" + lines + "\n")


def load_english(path: Path, fmt: str) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if fmt == "arb":
        return {k: v for k, v in raw.items() if not k.startswith("@")}
    return raw


def translate_json(client, *, model: str, language: str, code: str,
                   keys: dict, description: str, kind: str,
                   notes_path: Path | None = None,
                   char_limits: dict | None = None,
                   ) -> tuple[dict | None, str]:
    if kind == "catalog":
        prompt_tpl = CATALOG_PROMPT
    else:
        prompt_tpl = LISTING_PROMPT

    notes = load_notes(notes_path, set(keys))
    limit_text = ""
    if char_limits:
        parts = [f"  {f}: max {n} characters" for f, n in char_limits.items()]
        limit_text = "\nCharacter limits (the store rejects longer):\n" + "\n".join(parts) + "\n"

    prompt = prompt_tpl.format(
        language=language, code=code, description=description,
        notes=notes, catalogue=json.dumps(keys, ensure_ascii=False, indent=2),
        char_limits=limit_text,
    )

    with client.messages.stream(
        model=model, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {k: {"type": "string"} for k in keys},
                "required": list(keys),
                "additionalProperties": False,
            },
        }},
    ) as stream:
        resp = stream.get_final_message()

    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        translated = json.loads(text)
    except json.JSONDecodeError as e:
        if getattr(resp, "stop_reason", None) == "max_tokens":
            return None, (f"response stopped at the {MAX_TOKENS}-token output "
                          "limit — raise MAX_TOKENS")
        return None, f"unparseable response ({e})"

    problems = verify_json(keys, translated)
    if char_limits:
        problems.extend(verify_char_limits(translated, char_limits))
    if problems:
        return None, "; ".join(problems)
    return translated, ""


def translate_arb(client, *, model: str, language: str, code: str,
                  keys: dict, description: str,
                  notes_path: Path | None = None,
                  ) -> tuple[dict | None, str]:
    notes = load_notes(notes_path, set(keys))
    prompt = ARB_PROMPT.format(
        language=language, code=code, description=description,
        notes=notes, catalogue=json.dumps(keys, ensure_ascii=False, indent=2),
    )

    with client.messages.stream(
        model=model, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {k: {"type": "string"} for k in keys},
                "required": list(keys),
                "additionalProperties": False,
            },
        }},
    ) as stream:
        resp = stream.get_final_message()

    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        translated = json.loads(text)
    except json.JSONDecodeError as e:
        if getattr(resp, "stop_reason", None) == "max_tokens":
            return None, (f"response stopped at the {MAX_TOKENS}-token output "
                          "limit — raise MAX_TOKENS")
        return None, f"unparseable response ({e})"

    problems = verify_json(keys, translated)
    if problems:
        return None, "; ".join(problems)
    return translated, ""


def translate_html(client, *, model: str, language: str, code: str,
                   html: str, description: str,
                   ) -> tuple[str | None, str]:
    rtl = '\n- Add dir="rtl" to the <html> tag.' if code in RTL_LOCALES else ""
    prompt = HTML_PROMPT.format(
        language=language, code=code, description=description,
        rtl=rtl, catalogue=html,
    )

    resp = client.messages.create(
        model=model, max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(b.text for b in resp.content if b.type == "text")
    if not text.strip().startswith("<!") and not text.strip().startswith("<html"):
        return None, "response does not look like HTML"
    return text, ""


# ---------------------------------------------------------------------------
# Project runner
# ---------------------------------------------------------------------------

def get_source_locales(source_cfg: dict) -> list[tuple[str, str]]:
    if "locales" in source_cfg:
        codes = set(source_cfg["locales"])
        return [(c, n) for c, n, _ in SUPPORTED_LOCALES
                if c in codes and c != DEFAULT_LOCALE]
    return [(c, n) for c, n, _ in SUPPORTED_LOCALES if c != DEFAULT_LOCALE]


def resolve_repo_path(repo: str) -> Path | None:
    owner, name = repo.split("/")
    script_dir = Path(__file__).resolve().parent
    candidates = [
        # GitHub Actions layout: repos/owner/name
        script_dir / "repos" / owner / name,
        # Cloud session layout: /home/user/owner/name
        Path("/home/user") / owner / name,
        Path("/home/user") / name,
        Path("/home/user") / owner / name.lower(),
        Path("/home/user") / name.lower(),
        Path.home() / owner / name,
        Path.home() / name,
        Path.home() / owner / name.lower(),
        Path.home() / name.lower(),
    ]
    for p in candidates:
        if p.exists() and (p / ".git").exists():
            return p
    return None


def run_source(client, project_cfg: dict, source_cfg: dict, *,
               wanted: set | None, force: bool, fill: bool,
               dry_run: bool, output_base: Path) -> int:
    fmt = project_cfg["format"]
    description = project_cfg["description"]
    repo = project_cfg["repo"]
    kind = source_cfg["kind"]
    model = source_cfg["model"]
    notes_path = None
    char_limits = source_cfg.get("char_limits")

    repo_path = resolve_repo_path(repo)
    if not repo_path:
        output_dir = output_base / repo.replace("/", "_") / source_cfg["output_dir"]
    else:
        output_dir = repo_path / source_cfg["output_dir"]

    if repo_path and source_cfg.get("notes"):
        notes_path = repo_path / source_cfg["notes"]

    if kind == "html_site":
        if not repo_path:
            print(f"  SKIP {source_cfg['name']}: repo not cloned locally")
            return 0
        english_path = repo_path / source_cfg["english"]
        if not english_path.exists():
            print(f"  SKIP {source_cfg['name']}: {english_path} not found")
            return 0
        english_html = english_path.read_text(encoding="utf-8")
        locales = get_source_locales(source_cfg)
        if wanted:
            locales = [(c, n) for c, n in locales if c in wanted]

        targets = []
        for code, name in locales:
            out_path = output_dir / source_cfg["pattern"].format(code=code)
            if out_path.exists() and not force:
                continue
            targets.append((code, name, out_path))

        print(f"  {source_cfg['name']}: {len(targets)} HTML pages to translate")
        if dry_run:
            for code, name, _ in targets:
                print(f"    would translate {code} ({name})")
            return 0
        if not targets:
            return 0

        failures = []
        for code, name, out_path in targets:
            translated, problem = translate_html(
                client, model=model, language=name, code=code,
                html=english_html, description=description)
            if translated is None:
                failures.append(f"{code}: {problem}")
                continue
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(translated, encoding="utf-8")
            print(f"    wrote {out_path.name} ({name})")

        for f in failures:
            print("    NOT written: " + f, file=sys.stderr)
        return 1 if failures else 0

    # JSON or ARB catalog/listing
    if repo_path:
        english_path = repo_path / source_cfg["english"]
    else:
        english_path = output_base / repo.replace("/", "_") / source_cfg["english"]

    if not english_path.exists():
        print(f"  SKIP {source_cfg['name']}: {english_path} not found")
        return 0

    english = load_english(english_path, fmt)
    locales = get_source_locales(source_cfg)
    if wanted:
        locales = [(c, n) for c, n in locales if c in wanted]

    if fill:
        return _fill(client, english, locales, model=model,
                     description=description, kind=kind, fmt=fmt,
                     output_dir=output_dir, pattern=source_cfg["pattern"],
                     notes_path=notes_path, char_limits=char_limits,
                     dry_run=dry_run, source_name=source_cfg["name"])

    targets = []
    for code, name in locales:
        out_path = output_dir / source_cfg["pattern"].format(code=code)
        if out_path.exists() and not force:
            continue
        targets.append((code, name))

    print(f"  {source_cfg['name']}: {len(english)} keys; "
          f"{len(targets)} locales to generate")
    if dry_run:
        for code, name in targets:
            print(f"    would generate {code} ({name})")
        return 0
    if not targets:
        return 0

    failures = []
    for code, name in targets:
        if fmt == "arb":
            translated, problem = translate_arb(
                client, model=model, language=name, code=code,
                keys=english, description=description,
                notes_path=notes_path)
        else:
            translated, problem = translate_json(
                client, model=model, language=name, code=code,
                keys=english, description=description, kind=kind,
                notes_path=notes_path, char_limits=char_limits)

        if translated is None:
            failures.append(f"{code}: {problem}")
            continue

        out_path = output_dir / source_cfg["pattern"].format(code=code)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if fmt == "arb":
            arb_out = {"@@locale": code}
            arb_out.update(translated)
            out_path.write_text(
                json.dumps(arb_out, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        else:
            out_path.write_text(
                json.dumps(translated, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        print(f"    wrote {source_cfg['pattern'].format(code=code)} ({name})")

    if failures:
        print("\n    NOT written:", file=sys.stderr)
        for f in failures:
            print("    " + f, file=sys.stderr)
        return 1
    return 0


def _fill(client, english: dict, locales: list, *, model: str,
          description: str, kind: str, fmt: str, output_dir: Path,
          pattern: str, notes_path: Path | None, char_limits: dict | None,
          dry_run: bool, source_name: str) -> int:
    behind = {}
    for code, name in locales:
        path = output_dir / pattern.format(code=code)
        if not path.exists():
            continue
        existing = load_english(path, fmt)
        missing = {k: v for k, v in english.items() if k not in existing}
        if missing:
            behind[code] = (name, existing, missing)

    print(f"  {source_name}: {len(behind)} catalogs behind the source")
    if dry_run:
        for code, (name, _e, missing) in behind.items():
            print(f"    {code} ({name}): {len(missing)} keys")
        return 0
    if not behind:
        return 0

    failures = []
    for code, (name, existing, missing) in behind.items():
        if fmt == "arb":
            translated, problem = translate_arb(
                client, model=model, language=name, code=code,
                keys=missing, description=description,
                notes_path=notes_path)
        else:
            translated, problem = translate_json(
                client, model=model, language=name, code=code,
                keys=missing, description=description, kind=kind,
                notes_path=notes_path, char_limits=char_limits)

        if translated is None:
            failures.append(f"{code}: {problem}")
            continue

        existing.update(translated)
        ordered = {k: existing[k] for k in english if k in existing}

        out_path = output_dir / pattern.format(code=code)
        if fmt == "arb":
            arb_out = {"@@locale": code}
            arb_out.update(ordered)
            out_path.write_text(
                json.dumps(arb_out, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        else:
            out_path.write_text(
                json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
        print(f"    filled {pattern.format(code=code)} (+{len(missing)})")

    for f in failures:
        print("    NOT filled: " + f, file=sys.stderr)
    return 1 if failures else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Translate all Spencer Fields Software projects")
    ap.add_argument("--project", required=True,
                    help='project key from projects.json, or "all"')
    ap.add_argument("--source", help="source name within the project")
    ap.add_argument("--only", help="comma-separated locale codes")
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing translations")
    ap.add_argument("--fill", action="store_true",
                    help="top up existing catalogs with newly-added keys")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be done; makes no API calls")
    ap.add_argument("--output", default="output",
                    help="staging directory for output (default: output/)")
    args = ap.parse_args()

    projects = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    wanted = {c.strip() for c in args.only.split(",")} if args.only else None
    output_base = Path(args.output)

    if args.project == "all":
        project_keys = [k for k in projects if not k.startswith("_")]
    else:
        if args.project not in projects:
            print(f"Unknown project: {args.project}", file=sys.stderr)
            print(f"Available: {', '.join(k for k in projects if not k.startswith('_'))}",
                  file=sys.stderr)
            return 1
        project_keys = [args.project]

    client = None
    if not args.dry_run:
        client = make_client()

    exit_code = 0
    for key in project_keys:
        cfg = projects[key]
        print(f"\n{'='*60}")
        print(f"Project: {key} ({cfg['repo']})")
        print(f"{'='*60}")

        for source in cfg["sources"]:
            if args.source and source["name"] != args.source:
                continue
            rc = run_source(client, cfg, source,
                            wanted=wanted, force=args.force,
                            fill=args.fill, dry_run=args.dry_run,
                            output_base=output_base)
            exit_code = max(exit_code, rc)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
