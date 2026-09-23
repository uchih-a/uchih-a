"""
generate_neofetch.py
Fetches live GitHub stats for a user and renders a neofetch-style
animated SVG (Ubuntu terminal theme) into dist/neofetch.svg.
Commit this file to your uchih-a/uchih-a repo root.
"""

import os, json, math, requests
from datetime import datetime, timezone

USER    = os.environ.get("GH_USER", "uchih-a")
TOKEN   = os.environ.get("GH_TOKEN", "")
HEADERS = {"Authorization": f"bearer {TOKEN}"} if TOKEN else {}

# ── 1. Fetch REST stats ──────────────────────────────────────────────────────
def rest(path):
    r = requests.get(f"https://api.github.com{path}", headers=HEADERS)
    return r.json()

user   = rest(f"/users/{USER}")
repos  = rest(f"/users/{USER}/repos?per_page=100&type=owner")
total_stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
total_forks = sum(r.get("forks_count",       0) for r in repos if not r.get("fork"))
repo_count  = len([r for r in repos if not r.get("fork")])

# ── 2. Fetch contribution count via GraphQL ──────────────────────────────────
GQL = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
    pullRequests(states: [OPEN, MERGED, CLOSED]) { totalCount }
    issues(states: [OPEN, CLOSED])               { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false) { totalCount }
  }
}
"""
gql_resp = requests.post(
    "https://api.github.com/graphql",
    json={"query": GQL, "variables": {"login": USER}},
    headers=HEADERS
).json()

gql_user   = gql_resp.get("data", {}).get("user", {})
cal        = gql_user.get("contributionsCollection", {}).get("contributionCalendar", {})
total_contrib = cal.get("totalContributions", 0)
pr_count   = gql_user.get("pullRequests", {}).get("totalCount", 0)
issue_count= gql_user.get("issues",       {}).get("totalCount", 0)

# contribution weeks → grid (53 cols × 7 rows)
weeks = cal.get("weeks", [])
grid  = []          # grid[col][row] = level 0-4
for w in weeks:
    days = w.get("contributionDays", [])
    col  = []
    for d in days:
        c = d.get("contributionCount", 0)
        if   c == 0: lvl = 0
        elif c <= 3: lvl = 1
        elif c <= 6: lvl = 2
        elif c <= 9: lvl = 3
        else:        lvl = 4
        col.append(lvl)
    while len(col) < 7:
        col.insert(0, 0)
    grid.append(col)
while len(grid) < 53:
    grid.append([0]*7)

# ── 3. Build SVG ─────────────────────────────────────────────────────────────
UBUNTU_BG      = "#300A24"
UBUNTU_TITLEBAR= "#2C001E"
UBUNTU_ORANGE  = "#E95420"
UBUNTU_PURPLE  = "#77216F"
UBUNTU_GREEN   = "#4EC94E"
UBUNTU_CYAN    = "#00BCD4"
UBUNTU_TEXT    = "#FFFFFF"
UBUNTU_MUTED   = "#AEA79F"

CELL_COLORS = ["#1a0010", "#5E2750", "#77216F", "#E95420", "#FF9800"]

# layout
W, H     = 860, 260
BAR_H    = 34
PAD      = 20
ASCII_W  = 160    # left column for octocat
FIELD_X  = ASCII_W + PAD + 10

# octocat lines (simplified, fits in ASCII_W)
OCTOCAT = [
    ("   /\\_____/\\",   UBUNTU_PURPLE),
    ("  /  o   o  \\",  UBUNTU_PURPLE),
    (" ( ==  ^  == )",  UBUNTU_TEXT),
    ("  )         (",   UBUNTU_TEXT),
    (" (     🐙    )",  UBUNTU_TEXT),
    ("( (  )   (  ) )", UBUNTU_ORANGE),
    ("(__(__)___(__)__)",UBUNTU_MUTED),
]

fields = [
    ("",        f"{USER}@github",                    UBUNTU_ORANGE, True),
    ("sep",     "─" * 36,                            "#444444",     False),
    ("Name",    user.get("name") or USER,            UBUNTU_TEXT,   False),
    ("Role",    "Data Scientist · ML Researcher",    UBUNTU_TEXT,   False),
    ("Location","Kenya 🌍",                          UBUNTU_TEXT,   False),
    ("Focus",   "CV · Sequence Modeling · BioInfo",  UBUNTU_TEXT,   False),
    ("sep",     "─" * 36,                            "#444444",     False),
    ("Repos",   str(repo_count),                     UBUNTU_CYAN,   False),
    ("Stars",   f"★ {total_stars}",                 "#FF9800",     False),
    ("Commits", f"↑ {total_contrib} (last year)",   UBUNTU_GREEN,  False),
    ("PRs",     str(pr_count),                       UBUNTU_TEXT,   False),
    ("Issues",  str(issue_count),                    UBUNTU_TEXT,   False),
    ("Forks",   str(total_forks),                    UBUNTU_TEXT,   False),
    ("sep",     "─" * 36,                            "#444444",     False),
    ("Stack",   "Python · SQL · JavaScript",         UBUNTU_TEXT,   False),
    ("ML",      "PyTorch · TensorFlow · Sklearn",    UBUNTU_TEXT,   False),
]

FONT   = "Ubuntu Mono, monospace"
FS     = 12.5
LINE_H = 18

def esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

lines = []

# ── outer terminal window ────────────────────────────────────────────────────
lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
lines.append(f'  <defs>')
lines.append(f'    <style>')
lines.append(f'      @import url("https://fonts.googleapis.com/css2?family=Ubuntu+Mono:wght@400;700&amp;display=swap");')
lines.append(f'    </style>')
lines.append(f'  </defs>')

# background
lines.append(f'  <rect width="{W}" height="{H}" rx="10" fill="{UBUNTU_TITLEBAR}"/>')

# title bar
lines.append(f'  <rect width="{W}" height="{BAR_H}" rx="10" fill="{UBUNTU_PURPLE}"/>')
lines.append(f'  <rect y="20" width="{W}" height="{BAR_H-20}" fill="{UBUNTU_PURPLE}"/>')
# dots
for i, col in enumerate(["#FF5F56","#FFBD2E","#27C93F"]):
    lines.append(f'  <circle cx="{14+i*18}" cy="17" r="6" fill="{col}"/>')
# title text
lines.append(f'  <text x="{W//2}" y="21" text-anchor="middle" font-family="{FONT}" font-size="12" fill="rgba(255,255,255,0.5)">bash — {USER}@ubuntu: ~</text>')

# body background
lines.append(f'  <rect y="{BAR_H}" width="{W}" height="{H-BAR_H}" fill="{UBUNTU_BG}"/>')

# ── octocat ──────────────────────────────────────────────────────────────────
for i, (txt, col) in enumerate(OCTOCAT):
    y = BAR_H + PAD + 4 + i * LINE_H
    lines.append(f'  <text x="{PAD}" y="{y}" font-family="{FONT}" font-size="{FS}" fill="{col}">{esc(txt)}</text>')

# ── fields ───────────────────────────────────────────────────────────────────
fy = BAR_H + PAD + 4
for (key, val, col, bold) in fields:
    fw = "bold" if bold else "normal"
    if key == "sep":
        lines.append(f'  <text x="{FIELD_X}" y="{fy}" font-family="{FONT}" font-size="{FS}" fill="{col}">{esc(val)}</text>')
    elif key == "":
        lines.append(f'  <text x="{FIELD_X}" y="{fy}" font-family="{FONT}" font-size="{FS+1}" font-weight="bold" fill="{col}">{esc(val)}</text>')
    else:
        lines.append(f'  <text x="{FIELD_X}" y="{fy}" font-family="{FONT}" font-size="{FS}" fill="{UBUNTU_ORANGE}" font-weight="bold">{esc(key)}</text>')
        lines.append(f'  <text x="{FIELD_X+85}" y="{fy}" font-family="{FONT}" font-size="{FS}" fill="{col}">{esc(val)}</text>')
    fy += LINE_H

# colour swatches
swatch_colors = [UBUNTU_BG, UBUNTU_PURPLE, "#5E2750", UBUNTU_ORANGE, "#FF9800", UBUNTU_GREEN, UBUNTU_CYAN, UBUNTU_TEXT]
sx = FIELD_X
for sc in swatch_colors:
    lines.append(f'  <rect x="{sx}" y="{fy+4}" width="16" height="16" rx="3" fill="{sc}" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>')
    sx += 21

lines.append('</svg>')

svg_content = "\n".join(lines)

os.makedirs("dist", exist_ok=True)
with open("dist/neofetch.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)

print(f"✓ neofetch.svg generated — {repo_count} repos, ★{total_stars}, {total_contrib} contributions")
