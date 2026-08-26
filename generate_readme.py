import os
import html
import requests

GITHUB_USERNAME = os.environ["GITHUB_USERNAME"]
GITHUB_TOKEN = os.environ["GH_TOKEN"]
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
API = "https://api.github.com"

def get_user():
    r = requests.get(f"{API}/users/{GITHUB_USERNAME}", headers=HEADERS)
    r.raise_for_status()
    return r.json()

def get_all_repos():
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"{API}/user/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "affiliation": "owner,collaborator"},
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos

def get_stars_and_langs(repos):
    total_stars = 0
    lang_bytes = {}
    for repo in repos:
        total_stars += repo.get("stargazers_count", 0)
        r = requests.get(f"{API}/repos/{repo['full_name']}/languages", headers=HEADERS)
        if r.status_code == 200:
            for lang, count in r.json().items():
                lang_bytes[lang] = lang_bytes.get(lang, 0) + count
    return total_stars, lang_bytes

def get_commit_count(repos):
    total = 0
    for repo in repos:
        r = requests.get(
            f"{API}/repos/{repo['full_name']}/commits",
            headers=HEADERS,
            params={"author": GITHUB_USERNAME, "per_page": 1},
        )
        if r.status_code != 200:
            continue
        if "Link" in r.headers:
            last_page = r.headers["Link"].split("page=")[-1].split(">")[0]
            total += int(last_page)
        elif r.json():
            total += 1
    return total

def get_loc_additions_deletions(repos):
    additions, deletions = 0, 0
    for repo in repos:
        r = requests.get(f"{API}/repos/{repo['full_name']}/stats/contributors", headers=HEADERS)
        if r.status_code != 200:
            continue
        for contributor in r.json() or []:
            if contributor.get("author", {}).get("login") == GITHUB_USERNAME:
                for week in contributor.get("weeks", []):
                    additions += week.get("a", 0)
                    deletions += week.get("d", 0)
    return additions, deletions

def get_pr_and_contributed_repos(owned_repo_names):
    """Total PR count + distinct repos contributed to, via the Search API."""
    prs_total = 0
    contributed = set(owned_repo_names)
    page = 1
    while page <= 5:  
        r = requests.get(
            f"{API}/search/issues",
            headers=HEADERS,
            params={
                "q": f"type:pr author:{GITHUB_USERNAME}",
                "per_page": 100,
                "page": page,
            },
        )
        if r.status_code != 200:
            break
        data = r.json()
        prs_total = data.get("total_count", 0)
        items = data.get("items", [])
        for item in items:
            repo_url = item.get("repository_url", "")
            name = repo_url.split("/repos/")[-1]
            if name:
                contributed.add(name)
        if len(items) < 100:
            break
        page += 1
    return prs_total, len(contributed)


def top_languages(lang_bytes, n=3):
    ranked = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)
    return ", ".join(lang for lang, _ in ranked[:n])

FONT = "'Cascadia Code','Fira Code','SFMono-Regular',Consolas,monospace"
FONT_SIZE = 14
LINE_HEIGHT = 20
LABEL_PALETTE = ["#79c0ff", "#7ee787", "#ffa657", "#d2a8ff", "#f2cc60", "#a5d6ff", "#ff9bce"]


def esc(s):
    return html.escape(str(s), quote=False)


def art_lines_svg(art_text, x, y_start):
    out = []
    for i, line in enumerate(art_text.splitlines()):
        y = y_start + i * LINE_HEIGHT
        out.append(f'<text x="{x}" y="{y}" fill="#c9d1d9" xml:space="preserve">{esc(line)}</text>')
    return out

ROW_WIDTHS = []  

def stat_row_svg(x, y, label, value, label_color, value_color="#e6edf3", dots_color="#484f58", width=44):
    prefix = f"{label}: "
    dots_needed = max(3, width - len(prefix))
    dots = "." * dots_needed
    ROW_WIDTHS.append(len(prefix) + dots_needed + 1 + len(str(value)))
    parts = [
        f'<tspan fill="{label_color}">{esc(prefix)}</tspan>',
        f'<tspan fill="{dots_color}">{esc(dots)} </tspan>',
        f'<tspan fill="{value_color}">{esc(value)}</tspan>',
    ]
    return f'<text x="{x}" y="{y}" xml:space="preserve">{"".join(parts)}</text>'


def header_row_svg(x, y, title, color, width=52):
    dashes = "-" * max(3, width - len(title) - 1)
    text = f"{title} {dashes}"
    ROW_WIDTHS.append(len(text))
    return f'<text x="{x}" y="{y}" fill="{color}" font-weight="bold" xml:space="preserve">{esc(text)}</text>'


def build_svg(stats, ascii_art):
    ROW_WIDTHS.clear()
    art_x, art_y0 = 24, 34
    art_lines = ascii_art.splitlines()
    n_art_lines = len(art_lines)
    art_width_ch = max(len(l) for l in art_lines)
    stats_x = art_x + int(art_width_ch * FONT_SIZE * 0.62) + 40

    rows = []
    y = art_y0

    def col():
        c = LABEL_PALETTE[col.i % len(LABEL_PALETTE)]
        col.i += 1
        return c
    col.i = 0

    rows.append(header_row_svg(stats_x, y, GITHUB_USERNAME, "#f2cc60"))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "OS", "Windows", col()))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Languages.Programming", stats["prog_langs"], col()))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Languages.Computer", stats["computer_langs"], col()))
    y += LINE_HEIGHT * 2

    rows.append(header_row_svg(stats_x, y, "Contact", "#f2cc60"))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Email.Personal", stats["email_personal"], col()))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Email.Work", stats["email_work"], col()))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "LinkedIn", stats["linkedin"], col()))
    y += LINE_HEIGHT * 2

    rows.append(header_row_svg(stats_x, y, "GitHub Stats", "#f2cc60"))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Repos", stats["repos_value"], col(), value_color="#7ee787"))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Stars", str(stats["stars"]), col(), value_color="#f2cc60"))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Commits", "{:,}".format(stats["commits"]), col(), value_color="#79c0ff"))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Pull Requests", "{:,}".format(stats["prs"]), col(), value_color="#ff9bce"))
    y += LINE_HEIGHT
    rows.append(stat_row_svg(stats_x, y, "Followers", stats["followers_value"], col(), value_color="#a5d6ff"))
    y += LINE_HEIGHT

    prefix = "Lines of Code: "
    dots = "." * max(3, 44 - len(prefix))
    loc_value = "{:,}++, {:,}--".format(stats["additions"], stats["deletions"])
    ROW_WIDTHS.append(len(prefix) + len(dots) + 1 + len(loc_value))
    loc_line = (
        f'<text x="{stats_x}" y="{y}" xml:space="preserve">'
        f'<tspan fill="{col()}">{esc(prefix)}</tspan>'
        f'<tspan fill="#484f58">{esc(dots)} </tspan>'
        f'<tspan fill="#3fb950">{esc("{:,}".format(stats["additions"]))}++</tspan>'
        f'<tspan fill="#8b949e">, </tspan>'
        f'<tspan fill="#f85149">{esc("{:,}".format(stats["deletions"]))}--</tspan>'
        f"</text>"
    )
    rows.append(loc_line)
    y += LINE_HEIGHT

    art_svg = art_lines_svg(ascii_art, art_x, art_y0)

    height = max(art_y0 + n_art_lines * LINE_HEIGHT, y) + 24
    max_row_chars = max(ROW_WIDTHS) if ROW_WIDTHS else 44
    width = stats_x + int(max_row_chars * FONT_SIZE * 0.62) + 40

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="12" fill="#0d1117"/>
  <g font-family="{FONT}" font-size="{FONT_SIZE}px">
    {chr(10).join(art_svg)}
    {chr(10).join(rows)}
  </g>
</svg>'''
    return svg

def main():
    user = get_user()
    repos = get_all_repos()
    owned_repo_names = [r["full_name"] for r in repos]
    stars, lang_bytes = get_stars_and_langs(repos)
    commits = get_commit_count(repos)
    additions, deletions = get_loc_additions_deletions(repos)
    prs, contributed_count = get_pr_and_contributed_repos(owned_repo_names)

    with open("ascii_art.txt") as f:
        ascii_art = f.read()

    stats = {
        "prog_langs": "Python, JavaScript, C++, C",
        "computer_langs": "HTML, CSS, SQL",
        "email_personal": "sanjanabaidcode@gmail.com",
        "email_work": "sanjana.vikram.24033@iitgoa.ac.in",
        "linkedin": "sanjana-baid-bb600132b",
        "repos_value": f"{len(repos)} {{Contributed: {contributed_count}}}",
        "stars": stars,
        "commits": commits,
        "prs": prs,
        "followers_value": f"{user.get('followers', 0)} | Following: {user.get('following', 0)}",
        "additions": additions,
        "deletions": deletions,
    }

    os.makedirs("assets", exist_ok=True)
    svg = build_svg(stats, ascii_art)
    with open("assets/dark_mode.svg", "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
