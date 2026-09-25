# Translation-Agents

Centralized translation orchestration for all Spencer Fields Software projects.

## What this repo does

This repo holds the translation engine that generates locale catalogs for:
- **Dawnlist** — JSON catalogs (50 languages), store listings, Mac App Store listings
- **EasyPost Desktop** — JSON catalogs (50 languages)
- **Easy-Post Mobile Companion** — Flutter ARB files (27 languages), App Store metadata
- **Wren** — Flutter ARB files (47 languages)
- **software-site** — Full HTML page translations (16 languages)

## How to run translations

```bash
# Dry run (free, no API calls):
python translate.py --project dawnlist --dry-run

# Translate specific locales:
python translate.py --project dawnlist --only fr,de,es

# Fill in newly-added keys only:
python translate.py --project dawnlist --fill

# Force retranslate everything:
python translate.py --project dawnlist --force

# Translate all projects:
python translate.py --project all --dry-run
```

## Key files

- `translate.py` — The main translation CLI
- `projects.json` — Project configurations (repos, formats, sources, models)
- `locales.py` — The shared 50-language locale set
- `tests/` — Validation tests (run with `pytest`)
- `.github/workflows/translate.yml` — GitHub Actions for cloud translation runs

## Architecture

- English is always the source of truth
- Translations use the Anthropic Claude API (sonnet-5 for UI catalogs, opus-5 for store listings)
- Every translation is verified: placeholder parity, key completeness, character limits
- `--fill` mode handles incremental translation of new keys without retranslating everything
- Output goes to cloned repos or a staging directory

## Environment

- Requires `ANTHROPIC_API_KEY` environment variable
- Python 3.12+
- Dependencies: `pip install -r requirements.txt`

## Tests

```bash
pytest tests/
```

Tests validate the locale set, verification logic, and project config without making API calls.
