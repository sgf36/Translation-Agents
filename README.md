# Translation-Agents

Centralized translation engine for all Spencer Fields Software projects. Generates locale catalogs using the Anthropic Claude API with placeholder validation, character-limit enforcement, and incremental fill support.

## Supported projects

| Project | Format | Languages | Model |
|---|---|---|---|
| Dawnlist | JSON catalogs + store listings | 50 | sonnet-5 / opus-5 |
| EasyPost Desktop | JSON catalogs | 50 | sonnet-5 |
| Easy-Post Mobile | Flutter ARB | 27 | sonnet-5 |
| Wren | Flutter ARB | 47 | sonnet-5 |
| software-site | Static HTML pages | 16 | opus-5 |

## Quick start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

# See what would be translated (free):
python translate.py --project dawnlist --dry-run

# Translate French and German for Dawnlist:
python translate.py --project dawnlist --only fr,de

# Fill in newly-added keys across all locales:
python translate.py --project dawnlist --fill

# Run from GitHub Actions:
# → Actions tab → "Translate" workflow → Run workflow
```

## GitHub Actions

The `Translate` workflow (`.github/workflows/translate.yml`) can be triggered manually from the Actions tab. It:

1. Clones the target repository
2. Runs the translation engine
3. Pushes translated files to a new branch on the target repo
4. Uploads output as a build artifact

**Required secrets:**
- `ANTHROPIC_API_KEY` — Your Anthropic API key
- `REPO_ACCESS_TOKEN` — A GitHub PAT with push access to the target repos

## Architecture

- **English is always the source of truth** — translations are generated from it, never the reverse.
- **Placeholder validation** — every `{placeholder}` in the English source must appear in the translation. A dropped placeholder crashes the app at runtime.
- **Character-limit enforcement** — store listings are checked against Apple/Microsoft character caps before writing.
- **Incremental fill** — `--fill` mode translates only keys that were added since the last run, without retranslating everything.
- **No overwrites by default** — existing translations are preserved unless `--force` is given.

## Tests

```bash
pytest tests/
```
