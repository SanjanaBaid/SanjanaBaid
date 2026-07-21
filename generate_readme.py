import os
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
        r = requests.get(f"{API}/user/repos", headers=HEADERS,
                          params={"per_page": 100, "page": page, "affiliation": "owner,collaborator"})
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
        r = requests.get(f"{API}/repos/{repo['full_name']}/commits", headers=HEADERS,
                          params={"author": GITHUB_USERNAME, "per_page": 1})
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


def top_languages(lang_bytes, n=3):
    ranked = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)
    return ", ".join(lang for lang, _ in ranked[:n])


def build_readme(stats, ascii_art):
    fence = chr(96) * 3
    lines_stat = "{:,} (++), {:,} (--)".format(stats["additions"], stats["deletions"])

    lines = []
    lines.append(fence)
    lines.append(ascii_art)
    lines.append("")
    lines.append(GITHUB_USERNAME + " ---------------------------------------")
    lines.append("OS: .............................. Linux")
    lines.append("Languages.Programming: ........... " + stats["langs"])
    lines.append("")
    lines.append("Hobbies: .......................... YOUR_HOBBIES_HERE")
    lines.append("Contact: .......................... YOUR_CONTACT_HERE")
    lines.append("")
    lines.append("GitHub Stats -------------------------------------------")
    lines.append("Repos: ............................ " + str(stats["repo_count"]))
    lines.append("Stars: ............................. " + str(stats["stars"]))
    lines.append("Followers: .......................... " + str(stats["followers"]))
    lines.append("Commits: ........................... {:,}".format(stats["commits"]))
    lines.append("Lines of Code: ...................... " + lines_stat)
    lines.append(fence)
    lines.append("")

    return "\n".join(lines)


def main():
    user = get_user()
    repos = get_all_repos()
    stars, lang_bytes = get_stars_and_langs(repos)
    commits = get_commit_count(repos)
    additions, deletions = get_loc_additions_deletions(repos)

    with open("ascii_art.txt") as f:
        ascii_art = f.read()

    stats = {
        "repo_count": len(repos),
        "stars": stars,
        "followers": user.get("followers", 0),
        "commits": commits,
        "additions": additions,
        "deletions": deletions,
        "langs": top_languages(lang_bytes),
    }

    readme = build_readme(stats, ascii_art)
    with open("README.md", "w") as f:
        f.write(readme)


if __name__ == "__main__":
    main()
