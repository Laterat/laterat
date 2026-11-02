"""Generates stats.svg, langs.svg and activity.svg for the profile README.
Runs in GitHub Actions with GH_TOKEN (the built-in GITHUB_TOKEN). No dependencies."""
import json, os, sys, urllib.request
from html import escape

USER = os.environ.get("GH_USER", "Laterat")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT_DIR", "assets")
DEMO = os.environ.get("DEMO") == "1"

BG, BORDER, TITLE, TEXT, MUTED, ACCENT = "#1a120b", "#4a2c17", "#e8a33d", "#f1e4cf", "#c8a27a", "#c8553d"
HEAT = ["#2b1d12", "#4a2c17", "#8a4b25", "#c8553d", "#e8a33d"]
FONT = "ui-monospace, 'Fira Code', Menlo, Consolas, 'DejaVu Sans Mono', monospace"
LANG_COLORS = ["#e8a33d", "#c8553d", "#d98b4a", "#a8683a", "#8a4b25", "#c8a27a", "#6b3a1a"]


def api(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "profile-cards"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rest(path):
    return api(f"https://api.github.com{path}")


def graphql(query):
    return api("https://api.github.com/graphql", json.dumps({"query": query}).encode())["data"]


def card(w, h, title, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
        f'<rect x="0.5" y="0.5" rx="8" width="{w-1}" height="{h-1}" fill="{BG}" stroke="{BORDER}"/>'
        f'<text x="24" y="34" font-family="{FONT}" font-size="16" font-weight="700" fill="{TITLE}">{escape(title)}</text>'
        f"{body}</svg>"
    )


def text(x, y, s, size=13, fill=TEXT, anchor="start", weight="400"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{escape(str(s))}</text>')


# ---------- data ----------
if DEMO:
    profile = {"followers": 17, "public_repos": 38}
    repos = []
    langs = {"TypeScript": 520000, "PHP": 310000, "C++": 190000, "Java": 150000, "JavaScript": 90000, "HTML": 60000, "CSS": 40000}
    stars = 5
    contrib = {"commits": 412, "prs": 9, "issues": 2, "total": 438, "days": []}
    import random, datetime
    random.seed(4)
    start = datetime.date.today() - datetime.timedelta(days=370)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)
    d = start
    weeks = []
    while d <= datetime.date.today():
        wk = []
        for _ in range(7):
            wk.append(random.choice([0, 0, 0, 1, 2, 4, 7, 11]) if d <= datetime.date.today() else None)
            d += datetime.timedelta(days=1)
        weeks.append(wk)
    contrib["weeks"] = weeks
else:
    profile = rest(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = rest(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    stars = sum(r["stargazers_count"] for r in repos)
    langs = {}
    for r in repos:
        if r["fork"]:
            continue
        try:
            for k, v in rest(f"/repos/{USER}/{r['name']}/languages").items():
                langs[k] = langs.get(k, 0) + v
        except Exception as e:
            print("skip", r["name"], e, file=sys.stderr)
    contrib = None
    if TOKEN:
        q = """{ user(login:"%s"){ contributionsCollection{
              totalCommitContributions totalPullRequestContributions totalIssueContributions
              restrictedContributionsCount
              contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount date weekday } } } } } }""" % USER
        cc = graphql(q)["user"]["contributionsCollection"]
        weeks = []
        for w in cc["contributionCalendar"]["weeks"]:
            col = [None] * 7
            for d in w["contributionDays"]:
                col[d["weekday"]] = d["contributionCount"]
            weeks.append(col)
        contrib = {"commits": cc["totalCommitContributions"], "prs": cc["totalPullRequestContributions"],
                   "issues": cc["totalIssueContributions"], "total": cc["contributionCalendar"]["totalContributions"],
                   "weeks": weeks}

os.makedirs(OUT, exist_ok=True)

# ---------- stats.svg ----------
rows = [("Public repos", profile["public_repos"]), ("Stars earned", stars), ("Followers", profile["followers"])]
if contrib:
    rows += [("Commits (last year)", contrib["commits"]), ("Pull requests", contrib["prs"]), ("Issues opened", contrib["issues"])]
body = ""
for i, (k, v) in enumerate(rows):
    y = 66 + i * 24
    body += f'<circle cx="30" cy="{y-4}" r="3.5" fill="{ACCENT}"/>' + text(44, y, k) + text(300, y, v, fill=TITLE, anchor="end", weight="700")
open(f"{OUT}/stats.svg", "w", encoding="utf-8").write(card(330, 66 + len(rows) * 24 + 4, f"{USER}'s GitHub stats", body))

# ---------- langs.svg ----------
total = sum(langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
body = ""
bar_w = 260
x = 24
for i, (k, v) in enumerate(top):
    w = max(2, bar_w * v / total)
    body += f'<rect x="{x:.1f}" y="48" width="{w:.1f}" height="8" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>'
    x += w
body += f'<rect x="{x:.1f}" y="48" width="{max(0, 24 + bar_w - x):.1f}" height="8" fill="#3a2616"/>'
body = f'<clipPath id="c"><rect x="24" y="48" width="{bar_w}" height="8" rx="4"/></clipPath><g clip-path="url(#c)">{body}</g>'
for i, (k, v) in enumerate(top):
    col, row = i % 2, i // 2
    cx, cy = 24 + col * 150, 84 + row * 24
    body += f'<circle cx="{cx+5}" cy="{cy-4}" r="5" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>'
    body += text(cx + 16, cy, k, size=12) + text(cx + 128, cy, f"{100*v/total:.1f}%", size=11, fill=MUTED, anchor="end")
h = 84 + ((len(top) + 1) // 2) * 24 + 4
open(f"{OUT}/langs.svg", "w", encoding="utf-8").write(card(310, max(h, 66 + 6 * 24 + 4 if contrib else h), "Top languages", body))

# ---------- activity.svg ----------
if contrib:
    weeks = contrib["weeks"]
    cell, gap, left, top_y = 11, 3, 24, 56
    W = left * 2 + len(weeks) * (cell + gap)
    mx = max([c for wk in weeks for c in wk if c is not None] + [1])
    body = text(24, 34 + 0, "", size=1)
    for wi, wk in enumerate(weeks):
        for di, c in enumerate(wk):
            if c is None:
                continue
            lvl = 0 if c == 0 else min(4, 1 + int(3 * (c - 1) / max(mx - 1, 1)))
            body += f'<rect x="{left + wi*(cell+gap)}" y="{top_y + di*(cell+gap)}" width="{cell}" height="{cell}" rx="2" fill="{HEAT[lvl]}"/>'
    H = top_y + 7 * (cell + gap) + 30
    body += text(left, H - 10, f"{contrib['total']} contributions in the last year", size=12, fill=MUTED)
    lx = W - left - 5 * (cell + gap) - 70
    body += text(lx, H - 10, "Less", size=11, fill=MUTED, anchor="end")
    for i, c in enumerate(HEAT):
        body += f'<rect x="{lx + 8 + i*(cell+gap)}" y="{H-20}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>'
    body += text(lx + 8 + 5 * (cell + gap) + 4, H - 10, "More", size=11, fill=MUTED)
    open(f"{OUT}/activity.svg", "w", encoding="utf-8").write(card(W, H, "Contribution activity", body))
print("done", {k: v for k, v in rows})
