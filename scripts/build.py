"""Fetches the numbers, draws every card into assets/, and writes README.md.

    python scripts/build.py            fetch, then draw (what the nightly Action runs)
    python scripts/build.py --offline  draw from scripts/state.json only
    python scripts/build.py --demo     draw from made-up numbers into demo/ (for trying the design; never committed)

Exit code 1 when a source failed and its saved copy is older than STALE_DAYS (the cards are still drawn from
the saved copy, so the profile never breaks; the red run makes GitHub email you).
"""
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import cards
import readme
from fetch import collect

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "scripts" / "state.json"
STALE_DAYS = 3
THEMES = ("light", "dark")


def streaks(days, today):
    """days: {iso: count} nonzero only. A day with nothing yet today does not break the current streak."""
    d = today if days.get(today.isoformat()) else today - timedelta(days=1)
    cur, start = 0, None
    while days.get(d.isoformat()):
        cur, start = cur + 1, d
        d -= timedelta(days=1)
    best = {"days": 0, "start": None, "end": None}
    run, run_start, prev = 0, None, None
    for k in sorted(days):
        dk = date.fromisoformat(k)
        if dk > today:
            break
        run, run_start = (run + 1, run_start) if prev and dk - prev == timedelta(days=1) else (1, dk)
        if run >= best["days"]:
            best = {"days": run, "start": run_start.isoformat(), "end": k}
        prev = dk
    return {"days": cur, "start": start.isoformat() if start else None}, best


def derive(profile, state):
    """state.json -> the numbers the cards draw."""
    last = state.get("last_year", {"total": 0, "days": {}})
    end = date.fromisoformat(max(last["days"])) if last["days"] else date.today()
    days = {}
    for y in state.get("years", {}).values():
        days.update(y["days"])
    for k, v in last["days"].items():
        if v:
            days[k] = v
        else:
            days.pop(k, None)
    cur, best = streaks(days, end)
    user = state.get("user", {})
    return {
        "user": profile["user"],
        "end": end.isoformat(),
        "days": days,
        "last_year": last["total"],
        "all_time": sum(days.values()),
        "since": (user.get("created") or end.isoformat())[:4],
        "current": cur,
        "longest": best,
        "repos": user.get("public_repos", 0),
        "stars": user.get("stars", 0),
    }


def demo_state(profile):
    """Made-up numbers, only to look at the design."""
    rnd = random.Random(7)
    today = date.today()
    days = {}
    for i in range(400):
        d = today - timedelta(days=i)
        busy = 0.75 if d.weekday() < 5 else 0.3
        days[d.isoformat()] = rnd.choice([1, 2, 3, 4, 6, 9, 14]) if rnd.random() < busy else 0
    for i in range(12):
        days[(today - timedelta(days=i)).isoformat()] = rnd.randint(2, 11)
    last = {k: v for k, v in days.items() if k > (today - timedelta(days=365)).isoformat()}
    return {"user": {"created": "2019-03-14", "public_repos": 6, "stars": 23},
            "last_year": {"total": sum(last.values()), "days": last},
            "years": {"2025": {"total": 0, "days": {k: v for k, v in days.items() if k.startswith("2025") and v}}},
            "projects": {"capx": {"npm_version": "0.3.1", "npm_downloads": 412, "stars": 9}}}


def draw(profile, state, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.svg"):
        old.unlink()
    d = derive(profile, state)
    alts = {}

    def save(name, fn):
        for theme in THEMES:
            for phone in (False, True):
                svg, alt = fn(theme, phone)
                (out_dir / f"{name}{'-phone' if phone else ''}-{theme}.svg").write_text(svg, encoding="utf-8")
                alts[name] = alt

    save("hero", lambda t, ph: cards.hero(profile, t, ph))
    save("stats", lambda t, ph: cards.stats(d, t, ph))
    save("graph-6m", lambda t, ph: cards.heatmap(d, 6, t, ph))
    save("graph-12m", lambda t, ph: cards.heatmap(d, 12, t, ph))
    save("line-30d", lambda t, ph: cards.line30(d, t, ph))
    save("whoami", lambda t, ph: cards.whoami(profile, t, ph))
    save("label-ship", lambda t, ph: cards.label("what I ship", t, ph))
    for p in profile.get("projects", []):
        facts = state.get("projects", {}).get(p["id"], {})
        save(f"project-{p['id']}", lambda t, ph, p=p, f=facts: cards.project(p, f, t, ph))
    badges = []
    for kind, link in profile.get("links", {}).items():
        if kind.startswith("_"):
            continue
        href = link.get("url") or (f"mailto:{link['address']}" if link.get("address") else "")
        if not href:
            print(f"  note: links.{kind} is empty in profile.json, its badge is hidden")
            continue
        for theme in THEMES:
            svg, alt = cards.badge(kind, link["label"], theme)
            (out_dir / f"badge-{kind}-{theme}.svg").write_text(svg, encoding="utf-8")
        badges.append((kind, link["label"], href))
    return d, alts, badges


def main(argv):
    profile = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    if "--demo" in argv:
        out = ROOT / "demo"
        profile["links"]["linkedin"]["url"] = "https://www.linkedin.com/in/example/"
        profile["links"]["email"]["address"] = "you@example.com"
        _, alts, badges = draw(profile, demo_state(profile), out / "assets")
        (out / "README.md").write_text(readme.render(profile, alts, badges), encoding="utf-8")
        print(f"demo written to {out}")
        return 0
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    failed = []
    if "--offline" not in argv:
        failed = collect(profile, state, date.today())
        for f in failed:
            print(f"  source failed: {f}")
    if not state.get("last_year"):
        print("no contribution data yet (first run failed?), nothing drawn")
        return 1
    _, alts, badges = draw(profile, state, ROOT / "assets")
    (ROOT / "README.md").write_text(readme.render(profile, alts, badges), encoding="utf-8")
    STATE.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    stale = [k for k, v in state.get("fetched", {}).items()
             if (date.today() - date.fromisoformat(v)).days > STALE_DAYS]
    if stale:
        print(f"stale sources (older than {STALE_DAYS} days): {', '.join(stale)}")
        return 1
    print("cards drawn")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
