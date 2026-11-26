"""Writes README.md. Every card is a <picture> with light/dark and desktop/phone sources."""
from html import escape


def pic(name, alt, width="100%", phone=True, height=None):
    a = escape(alt)
    size = f'height="{height}"' if height else f'width="{width}"'
    src = []
    if phone:
        src.append(f'<source media="(prefers-color-scheme: dark) and (max-width: 600px)" srcset="assets/{name}-phone-dark.svg">')
        src.append(f'<source media="(max-width: 600px)" srcset="assets/{name}-phone-light.svg">')
    src.append(f'<source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">')
    return f'<picture>{"".join(src)}<img src="assets/{name}-light.svg" {size} alt="{a}"></picture>'


def link(href, inner):
    return f'<a href="{escape(href)}">{inner}</a>'


def render(profile, alts, badges):
    user = profile["user"]
    out = [pic("hero", alts["hero"]), ""]
    if badges:
        out.append('<p align="center">')
        out += [link(href, pic(f"badge-{kind}", label, phone=False, height=44)) for kind, label, href in badges]
        out += ["</p>", ""]
    out += [link(f"https://github.com/{user}?tab=repositories", pic("stats", alts["stats"])), ""]
    out += [pic("graph-6m", alts["graph-6m"]), ""]
    out += [f"<details><summary>{escape(alts['graph-12m'])}</summary>", "", pic("graph-12m", alts["graph-12m"]), "",
            "</details>", ""]
    out += [pic("line-30d", alts["line-30d"]), ""]
    out += [pic("whoami", alts["whoami"]), ""]
    projects = profile.get("projects", [])
    if projects:
        out += [pic("label-ship", alts["label-ship"]), ""]
        width = "100%" if len(projects) == 1 else "49%"
        out.append('<p align="center">')
        out += [link(p["url"], pic(f"project-{p['id']}", alts[f"project-{p['id']}"], width)) for p in projects]
        out += ["</p>", ""]
    out.append(f'<p align="center"><sub>{escape(profile.get("footer", ""))}</sub></p>')
    return "\n".join(out) + "\n"
