"""Reads the public numbers for the profile. No secret is needed.

Contribution calendar: the public page github.com/users/<user>/contributions (the same numbers your profile
shows), with the GraphQL API as a fallback when GITHUB_TOKEN is set. Repos and stars: the REST API.
Projects: npm registry (version, monthly downloads) and the repo's stars.
Each source that fails keeps its last good value from state.json; build.py reports it.
"""
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, timedelta
from html import unescape

UA = "Mozilla/5.0 (profile-readme-refresh; +https://github.com/KhalidMh/KhalidMh)"


class SourceError(Exception):
    pass


def http(url, data=None, headers=None, timeout=30):
    """GET (or POST when data is given). Returns text, or None on 404."""
    h = {"User-Agent": UA, **(headers or {})}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        h.setdefault("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=timeout) as r:
            return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise SourceError(f"{url}: HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SourceError(f"{url}: {e}")


# ------------------------------------------------------------------ contribution calendar
_ATTR = re.compile(r'([\w-]+)="([^"]*)"')
_TD = re.compile(r"<td\b([^>]*)>", re.S)
_TIP = re.compile(r"<tool-tip\b([^>]*)>(.*?)</tool-tip>", re.S)
_HEAD = re.compile(r'<h2[^>]*id="js-contribution-activity-description"[^>]*>(.*?)</h2>', re.S)


def parse_calendar(html):
    """Contributions page HTML -> (heading total, {iso date: count}). Raises SourceError when the markup
    changed: the heading total must equal the sum of the day cells."""
    m = _HEAD.search(html)
    head = " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split()) if m else ""
    hm = re.search(r"([\d,]+)\s+contributions?", head)
    if not hm:
        raise SourceError("calendar heading not found")
    total = int(hm.group(1).replace(",", ""))
    tips = {}
    for attrs, body in _TIP.findall(html):
        a = dict(_ATTR.findall(attrs))
        if "for" in a:
            tips[a["for"]] = " ".join(unescape(re.sub(r"<[^>]+>", "", body)).split())
    days = {}
    for attrs in _TD.findall(html):
        a = dict(_ATTR.findall(attrs))
        d = a.get("data-date")
        if not d:
            continue
        tip = tips.get(a.get("id", ""), "")
        t = re.match(r"(No|[\d,]+) contributions? on", tip)
        if not t:
            raise SourceError(f"unreadable day cell {d}: {tip!r}")
        days[d] = 0 if t.group(1) == "No" else int(t.group(1).replace(",", ""))
    if not days:
        raise SourceError("no day cells found")
    if sum(days.values()) != total:
        raise SourceError(f"heading says {total}, cells add up to {sum(days.values())}")
    return total, days


def calendar_html(user, year=None):
    url = f"https://github.com/users/{user}/contributions"
    if year:
        url += f"?from={year}-01-01&to={year}-12-31"
    html = http(url, headers={"Accept": "text/html"})
    if html is None:
        raise SourceError(f"{url}: not found")
    return parse_calendar(html)


_GQL = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to)
{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def calendar_graphql(user, start, end):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SourceError("GraphQL fallback needs GITHUB_TOKEN")
    body = json.dumps({"query": _GQL, "variables": {
        "login": user, "from": f"{start.isoformat()}T00:00:00Z", "to": f"{end.isoformat()}T23:59:59Z"}}).encode()
    txt = http("https://api.github.com/graphql", data=body, headers={"Content-Type": "application/json"})
    out = json.loads(txt or "{}")
    if out.get("errors") or not out.get("data", {}).get("user"):
        raise SourceError(f"GraphQL: {out.get('errors')}")
    cal = out["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = {d["date"]: d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]}
    return cal["totalContributions"], days


def fetch_calendar(user, created_year, today, cached_years):
    """-> (last_year {"total", "days"}, years {"YYYY": {"total", "days"(nonzero only)}})."""
    try:
        total, days = calendar_html(user)
    except SourceError as e:
        print(f"  html calendar failed ({e}), trying GraphQL")
        total, days = calendar_graphql(user, today - timedelta(days=365), today)
    last_year = {"total": total, "days": days}
    years = {}
    for y in range(created_year, today.year + 1):
        key = str(y)
        if y < today.year and key in cached_years:
            years[key] = cached_years[key]
            continue
        try:
            t, d = calendar_html(user, y)
        except SourceError:
            t, d = calendar_graphql(user, date(y, 1, 1), date(y, 12, 31))
        years[key] = {"total": t, "days": {k: v for k, v in d.items() if v and k.startswith(key)}}
    return last_year, years


# ------------------------------------------------------------------ repos, projects
def fetch_user(user):
    txt = http(f"https://api.github.com/users/{user}")
    if txt is None:
        raise SourceError(f"user {user} not found")
    u = json.loads(txt)
    stars, page = 0, 1
    while True:
        batch = json.loads(http(f"https://api.github.com/users/{user}/repos?type=owner&per_page=100&page={page}") or "[]")
        stars += sum(r.get("stargazers_count", 0) for r in batch if not r.get("fork"))
        if len(batch) < 100:
            break
        page += 1
    return {"created": u["created_at"][:10], "public_repos": u.get("public_repos", 0), "stars": stars}


def fetch_project(p):
    out = {"npm_version": None, "npm_downloads": None, "stars": None}
    if p.get("npm"):
        reg = http(f"https://registry.npmjs.org/{p['npm']}")
        if reg:
            meta = json.loads(reg)
            out["npm_version"] = meta.get("dist-tags", {}).get("latest")
            dl = http(f"https://api.npmjs.org/downloads/point/last-month/{p['npm']}")
            if dl:
                out["npm_downloads"] = json.loads(dl).get("downloads")
    if p.get("repo"):
        r = http(f"https://api.github.com/repos/{p['repo']}")
        if r:
            out["stars"] = json.loads(r).get("stargazers_count", 0)
    return out


def collect(profile, state, today):
    """Updates state in place. Returns the list of sources that failed this run."""
    failed = []
    user = profile["user"]
    try:
        state["user"] = fetch_user(user)
        state.setdefault("fetched", {})["user"] = today.isoformat()
    except SourceError as e:
        failed.append(f"user: {e}")
    created_year = int(state.get("user", {}).get("created", f"{today.year}")[:4])
    try:
        state["last_year"], state["years"] = fetch_calendar(user, created_year, today, state.get("years", {}))
        state.setdefault("fetched", {})["calendar"] = today.isoformat()
    except SourceError as e:
        failed.append(f"calendar: {e}")
    for p in profile.get("projects", []):
        try:
            state.setdefault("projects", {})[p["id"]] = fetch_project(p)
            state.setdefault("fetched", {})[f"project:{p['id']}"] = today.isoformat()
        except SourceError as e:
            failed.append(f"project {p['id']}: {e}")
    return failed
