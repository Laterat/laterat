
"""
Generates stats.svg and langs.svg for the GitHub profile README.
Runs in GitHub Actions with GH_TOKEN (the built-in GITHUB_TOKEN).
No dependencies.
"""

import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "Laterat")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT_DIR", "assets")
DEMO = os.environ.get("DEMO") == "1"

BG = "#0d1117"
BORDER = "#30363d"
TITLE = "#3fb950"
TEXT = "#e6edf3"
MUTED = "#8b949e"
ACCENT = "#3fb950"

FONT = "ui-monospace, 'Fira Code', Menlo, Consolas, 'DejaVu Sans Mono', monospace"

LANG_COLORS = [
    "#3fb950",
    "#e6edf3",
    "#26a641",
    "#8b949e",
    "#7ee787",
    "#6e7681",
    "#0e8a3b"
]


# ---------- GitHub API ----------

def api(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "profile-cards"}
    )

    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")

    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rest(path):
    return api(f"https://api.github.com{path}")


# ---------- SVG helpers ----------

def card(w, h, title, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(title)}">'
        f'<rect x="0.5" y="0.5" rx="8" width="{w-1}" '
        f'height="{h-1}" fill="{BG}" stroke="{BORDER}"/>'
        f'<text x="24" y="34" font-family="{FONT}" '
        f'font-size="16" font-weight="700" fill="{TITLE}">'
        f'{escape(title)}</text>'
        f'{body}</svg>'
    )


def text(x, y, s, size=13, fill=TEXT, anchor="start", weight="400"):
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" '
        f'font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}">'
        f'{escape(str(s))}</text>'
    )


# ---------- Data ----------

if DEMO:
    profile = {
        "followers": 17,
        "public_repos": 38
    }

    repos = []

    langs = {
        "TypeScript": 520000,
        "PHP": 310000,
        "C++": 190000,
        "Java": 150000,
        "JavaScript": 90000,
        "HTML": 60000,
        "CSS": 40000
    }

    stars = 5

else:
    profile = rest(f"/users/{USER}")

    repos = []
    page = 1

    while True:
        batch = rest(
            f"/users/{USER}/repos?per_page=100&type=owner&page={page}"
        )

        repos += batch

        if len(batch) < 100:
            break

        page += 1

    stars = sum(
        repo["stargazers_count"]
        for repo in repos
    )

    langs = {}

    for repo in repos:
        if repo["fork"]:
            continue

        try:
            repo_langs = rest(
                f"/repos/{USER}/{repo['name']}/languages"
            )

            for language, size in repo_langs.items():
                langs[language] = langs.get(language, 0) + size

        except Exception as e:
            print(
                "skip",
                repo["name"],
                e,
                file=sys.stderr
            )


os.makedirs(OUT, exist_ok=True)


# ---------- stats.svg ----------

rows = [
    ("Public repos", profile["public_repos"]),
    ("Stars earned", stars),
    ("Followers", profile["followers"])
]

body = ""

for i, (key, value) in enumerate(rows):
    y = 66 + i * 24

    body += (
        f'<circle cx="30" cy="{y-4}" r="3.5" fill="{ACCENT}"/>'
    )

    body += text(44, y, key)

    body += text(
        300,
        y,
        value,
        fill=TITLE,
        anchor="end",
        weight="700"
    )

open(
    f"{OUT}/stats.svg",
    "w",
    encoding="utf-8"
).write(
    card(
        330,
        66 + len(rows) * 24 + 4,
        f"{USER}'s GitHub stats",
        body
    )
)


# ---------- langs.svg ----------

total = sum(langs.values()) or 1

top = sorted(
    langs.items(),
    key=lambda kv: -kv[1]
)[:6]

body = ""

bar_w = 260
x = 24

for i, (language, size) in enumerate(top):
    w = max(2, bar_w * size / total)

    body += (
        f'<rect x="{x:.1f}" y="48" '
        f'width="{w:.1f}" height="8" '
        f'fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>'
    )

    x += w

body += (
    f'<rect x="{x:.1f}" y="48" '
    f'width="{max(0, 24 + bar_w - x):.1f}" '
    f'height="8" fill="#21262d"/>'
)

body = (
    f'<clipPath id="c">'
    f'<rect x="24" y="48" width="{bar_w}" '
    f'height="8" rx="4"/>'
    f'</clipPath>'
    f'<g clip-path="url(#c)">{body}</g>'
)

for i, (language, size) in enumerate(top):
    col = i % 2
    row = i // 2

    cx = 24 + col * 150
    cy = 84 + row * 24

    body += (
        f'<circle cx="{cx+5}" cy="{cy-4}" '
        f'r="5" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>'
    )

    body += text(
        cx + 16,
        cy,
        language,
        size=12
    )

    body += text(
        cx + 128,
        cy,
        f"{100 * size / total:.1f}%",
        size=11,
        fill=MUTED,
        anchor="end"
    )

h = 84 + ((len(top) + 1) // 2) * 24 + 4

open(
    f"{OUT}/langs.svg",
    "w",
    encoding="utf-8"
).write(
    card(
        310,
        max(h, 66 + 6 * 24 + 4),
        "Top languages",
        body
    )
)


# ---------- Done ----------

print("Generated stats.svg and langs.svg successfully.")

print({
    "Public repos": profile["public_repos"],
    "Stars earned": stars,
    "Followers": profile["followers"]
})
