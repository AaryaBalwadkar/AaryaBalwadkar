"""
Fetches the user's public repositories via the GitHub API, picks the top
projects (by stars, then most recently pushed), and rewrites the
Pinned Projects Showcase section of README.md between the
<!--START_SECTION:projects--> / <!--END_SECTION:projects--> markers.

Run by .github/workflows/projects.yml on a daily schedule.
"""

import os
import re
import sys
from datetime import datetime

import requests

USERNAME = os.environ.get("GH_USERNAME", "AaryaBalwadkar")
TOKEN = os.environ.get("GH_TOKEN")
README_PATH = "README.md"
MAX_PROJECTS = 6
# Repos to always skip (e.g. the profile README repo itself)
EXCLUDE_REPOS = {USERNAME.lower()}

START_MARKER = "<!--START_SECTION:projects-->"
END_MARKER = "<!--END_SECTION:projects-->"


def fetch_repos():
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "type": "owner"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1

    return repos


def pick_top_projects(repos):
    filtered = [
        r
        for r in repos
        if not r.get("fork")
        and not r.get("archived")
        and r["name"].lower() not in EXCLUDE_REPOS
    ]
    filtered.sort(
        key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at", "")),
        reverse=True,
    )
    return filtered[:MAX_PROJECTS]


def format_date(iso_str):
    if not iso_str:
        return "—"
    return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%b %d, %Y")


def build_table(projects):
    if not projects:
        return "_No public repositories found._"

    header = "| Project | Description | Language | ⭐ Stars | Last Updated |\n"
    header += "|---|---|---|---|---|\n"
    rows = []
    for repo in projects:
        name = repo["name"]
        url = repo["html_url"]
        description = (repo.get("description") or "No description provided.").replace(
            "|", "-"
        )
        language = repo.get("language") or "—"
        stars = repo.get("stargazers_count", 0)
        updated = format_date(repo.get("pushed_at"))
        rows.append(f"| [{name}]({url}) | {description} | {language} | {stars} | {updated} |")

    return header + "\n".join(rows)


def update_readme(table_markdown):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )
    replacement = f"{START_MARKER}\n{table_markdown}\n{END_MARKER}"

    if not pattern.search(content):
        print(
            f"Could not find {START_MARKER} / {END_MARKER} markers in {README_PATH}.",
            file=sys.stderr,
        )
        sys.exit(1)

    new_content = pattern.sub(replacement, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    repos = fetch_repos()
    top_projects = pick_top_projects(repos)
    table_markdown = build_table(top_projects)
    update_readme(table_markdown)
    print(f"Updated {README_PATH} with {len(top_projects)} project(s).")


if __name__ == "__main__":
    main()
