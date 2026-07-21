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
        r = requests.get(f"{API}/repos/{repo['full_name']}/stats/contributors",
