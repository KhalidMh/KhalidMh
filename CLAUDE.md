# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The GitHub profile README repo for `KhalidMh`. `README.md` and everything in `assets/` are **generated**. Don't edit them by hand, because the next build overwrites them. Content goes in `profile.json`, and how the cards look lives in `scripts/`.

## Commands

```bash
pip install -r scripts/requirements.txt   # fonttools + brotli (for woff2 subsetting); otherwise stdlib only, Python 3.12 in CI

python scripts/build.py            # fetch live data, update scripts/state.json, redraw assets/ + README.md
python scripts/build.py --offline  # redraw from scripts/state.json only (no network)
python scripts/build.py --demo     # made-up numbers -> demo/ (gitignored); use this to iterate on card design
```

There is no test suite or linter. To check a change, run `--demo` and open the SVGs in `demo/assets/` or `demo/README.md`. `build.py` exits 1 when there's no contribution data, or when a source's last successful fetch (`state["fetched"]`) is more than `STALE_DAYS` (3) old.

## Pipeline

`build.py` runs the steps in order:

1. **`fetch.collect`** updates the `state` dict in place from public sources: the GitHub REST user/repos endpoints (repo count, stars on non-fork repos), the contribution calendar, and the npm registry/downloads plus repo stars for each project. When a source fails, its previous value in `state.json` is kept and the failure is reported. That way the cards always render.
   - The calendar is **scraped** from `github.com/users/<user>/contributions` HTML. `parse_calendar` checks that the heading total equals the sum of the day cells and raises `SourceError` if GitHub's markup changed. If scraping fails, it falls back to GraphQL, which needs `GITHUB_TOKEN`.
   - Per-year calendars back to the account creation year are cached in `state["years"]`. Only the current year is refetched.
2. **`build.derive`** merges `last_year` + `years` into one `{iso_date: count}` map and computes streaks. A day with zero contributions so far today does not break the current streak.
3. **`build.draw`** wipes `*.svg` in the output dir, then calls each `cards.*` function 4 times (light/dark × desktop/phone). Files are named `<name>[-phone]-<theme>.svg`. Badges have no phone variant.
4. **`readme.render`** wraps each card in a `<picture>` with `prefers-color-scheme` and `max-width: 600px` sources, using the alt text that the card functions return.

## Card rendering

- `svgkit.SVG` is a small SVG builder. Colors are passed as theme token names (`"teal"`, `"muted"`, `"panel"`…) and resolved through `THEMES`. Any value that isn't a token passes through as a raw color.
- Every SVG embeds JetBrains Mono (`scripts/fonts/`), **subset to the characters that SVG actually uses**, as base64 woff2. `SVG.text`/`spans` record the characters, so any text added through raw `s.add(...)` won't be in the font subset.
- Text layout assumes a monospace font. Width is `0.6 * size * len(text)` (`tw`, `fit`, `wrap`), so switching to a proportional font would break all layout math.
- Desktop cards are 880px wide and phone cards 440px (`cards.W`). Every card function returns `(svg, alt)` and takes `(…, theme, phone)`.
- Some strings are hardcoded in `cards.py` instead of read from `profile.json`: the hero window title `~/khalid/profile.cds` and the terminal prompt host `@casa`.

## profile.json

- Keys starting with `_` are comments. `build.draw` skips `_`-prefixed entries under `links`.
- A link with an empty `url`/`address` hides its badge. Email badges become `mailto:` links.
- Each entry in `projects` produces a `project-<id>` card. `npm` and `repo` are optional fetch targets. One project renders at full width, and more than one at 49% each.
- `hero_code` lines are highlighted by the small CDS tokenizer in `cards.highlight`.

## CI

`.github/workflows/refresh.yml` runs nightly at 03:23 UTC, on manual dispatch, and on any push to `main` that touches `profile.json`, `scripts/**`, or the workflow file. It runs `build.py` with the built-in `GITHUB_TOKEN` and commits `assets/`, `README.md` and `scripts/state.json` as `github-actions[bot]`, but only if `assets/` or `README.md` changed. As a result, **pushing to `main` creates a follow-up bot commit**, so pull before pushing again.
