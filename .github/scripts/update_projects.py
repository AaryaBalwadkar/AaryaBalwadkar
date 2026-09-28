"""
Fetches the user's public repositories via the GitHub API, picks the top
projects (featured first, then most recently pushed), and rewrites the
All Projects section of README.md between the
<!--START_SECTION:projects--> / <!--END_SECTION:projects--> markers.

Run by .github/workflows/projects.yml on a daily schedule.

Env (all optional, sane defaults for local runs):
  GITHUB_USERNAME / GH_USERNAME / USERNAME  (default: AaryaBalwadkar)
  GITHUB_TOKEN / GH_TOKEN  (optional, raises rate limit when set)
"""

import os
import re
import sys
from datetime import datetime, timezone

import requests

USERNAME = (
    os.environ.get("GITHUB_USERNAME")
    or os.environ.get("GH_USERNAME")
    or "AaryaBalwadkar"
)
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
README_PATH = "README.md"
MAX_PROJECTS = 8

# Never show these in the auto table (profile repo + retired builds).
EXCLUDE_REPOS = {USERNAME.lower(), "voxtiva"}

# Always pin these first (if they exist and are not forks/archived).
# NOTE: GitHub name is lowercase `agricnxedge-web` (local folder is agricnxedge-web-v2).
FEATURED_REPOS = [
    "crop-health-mlops",
    "agricnxedge-web",
    "agri-cnx-edge",
    "realtime-iot-telemetry",
    "shiksha-sankalp",
]

# Friendly fallback descriptions for repos with empty GitHub descriptions.
DESCRIPTION_OVERRIDES = {
    "agricnxedge-web": "Web frontend for Agri-CNX-Edge (v2) — crop-health dashboard + inference UI.",
    "my-git-practice": "Git practice playground — branching, merges and rebases.",
    "mywebsite": "Personal portfolio website.",
    "volstory": "Volunteer stories platform (TypeScript).",
}

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
            params={"per_page": 100, "page": page, "type": "owner", "sort": "pushed"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return repos


def pick_top_projects(repos):
    eligible = [
        r
        for r in repos
        if not r.get("fork")
        and not r.get("archived")
        and r.get("name", "").lower() not in EXCLUDE_REPOS
    ]
    by_name = {r["name"].lower(): r for r in eligible}

    picked = []
    for name in FEATURED_REPOS:
        repo = by_name.pop(name.lower(), None)
        if repo is not None:
            picked.append(repo)

    # Fill the rest by most recently pushed, then stars.
    rest = sorted(
        by_name.values(),
        key=lambda r: (r.get("pushed_at", ""), r.get("stargazers_count", 0)),
        reverse=True,
    )
    picked.extend(rest)
    return picked[:MAX_PROJECTS]


def format_date(iso_str):
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return "—"


def build_table(projects):
    if not projects:
        return "_No public repositories found._"

    header = "| Project | Description | Language | ⭐ Stars | Updated |\n"
    header += "|---|---|---|---|---|\n"
    rows = []
    for repo in projects:
        name = repo["name"]
        url = repo["html_url"]
        description = (repo.get("description") or DESCRIPTION_OVERRIDES.get(name.lower()) or "No description provided.").replace(
            "|", "-"
        ).strip()
        if len(description) > 100:
            description = description[:97].rstrip() + "..."
        language = repo.get("language") or "—"
        stars = repo.get("stargazers_count", 0)
        updated = format_date(repo.get("pushed_at"))
        rows.append(
            f"| [{name}]({url}) | {description} | {language} | {stars} | {updated} |"
        )

    updated_utc = datetime.now(timezone.utc).strftime("%b %d, %Y")
    footer = f"\n<sub>Auto-updated {updated_utc} · featured first, then most recently pushed</sub>"
    return header + "\n".join(rows) + footer


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
