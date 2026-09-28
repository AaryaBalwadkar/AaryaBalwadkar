"""
Builds the Recent Activity section of README.md from the user's public
GitHub events (no third-party Action required).

Run by .github/workflows/activity.yml on a daily schedule.

Env:
  GITHUB_USERNAME / GH_USERNAME (default: AaryaBalwadkar)
  GITHUB_TOKEN / GH_TOKEN (optional, higher rate limit)
"""

import os
import re
import sys
from datetime import datetime

import requests

USERNAME = (
    os.environ.get("GITHUB_USERNAME")
    or os.environ.get("GH_USERNAME")
    or "AaryaBalwadkar"
)
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
README_PATH = "README.md"
MAX_EVENTS = 5

START_MARKER = "<!--START_SECTION:activity-->"
END_MARKER = "<!--END_SECTION:activity-->"

EVENT_TEMPLATES = {
    "PushEvent": "🔨 Pushed {count} commit(s) to [{repo}](https://github.com/{repo})",
    "CreateEvent": "🎉 Created {ref_type} `{ref}` in [{repo}](https://github.com/{repo})",
    "PullRequestEvent": "🔀 {action} PR #{number} in [{repo}](https://github.com/{repo})",
    "IssuesEvent": "❗ {action} issue #{number} in [{repo}](https://github.com/{repo})",
    "ForkEvent": "🍴 Forked [{repo}](https://github.com/{repo})",
    "WatchEvent": "⭐ Starred [{repo}](https://github.com/{repo})",
    "ReleaseEvent": "🚀 Released [{tag}](https://github.com/{repo}/releases) in [{repo}](https://github.com/{repo})",
    "PublicEvent": "📢 Open-sourced [{repo}](https://github.com/{repo})",
}


def fetch_events():
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    resp = requests.get(
        f"https://api.github.com/users/{USERNAME}/events/public",
        headers=headers,
        params={"per_page": 30},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def format_event(event):
    etype = event.get("type", "")
    repo = (event.get("repo") or {}).get("name", USERNAME)
    payload = event.get("payload") or {}
    created = event.get("created_at", "")
    try:
        date = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%b %d")
    except ValueError:
        date = ""

    template = EVENT_TEMPLATES.get(etype)
    if template is None:
        return None
    try:
        if etype == "PushEvent":
            count = len(payload.get("commits", [])) or payload.get("size", 1)
            text = template.format(count=count, repo=repo)
        elif etype == "CreateEvent":
            text = template.format(
                ref_type=payload.get("ref_type", ""),
                ref=payload.get("ref") or payload.get("master_branch", "main"),
                repo=repo,
            )
        elif etype in ("PullRequestEvent", "IssuesEvent"):
            text = template.format(
                action=(payload.get("action", "") or "").capitalize(),
                number=(payload.get("pull_request") or payload.get("issue") or {}).get(
                    "number", ""
                ),
                repo=repo,
            )
        elif etype == "ReleaseEvent":
            text = template.format(
                tag=(payload.get("release") or {}).get("tag_name", "release"),
                repo=repo,
            )
        else:
            text = template.format(repo=repo)
    except (KeyError, IndexError):
        return None
    return f"- {text} <sub>· {date}</sub>" if date else f"- {text}"


def build_section(events):
    lines = []
    for event in events:
        formatted = format_event(event)
        if formatted and formatted not in lines:
            lines.append(formatted)
        if len(lines) >= MAX_EVENTS:
            break
    if not lines:
        return "_No recent public activity found._"
    return "\n".join(lines)


def update_readme(section_markdown):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )
    replacement = f"{START_MARKER}\n{section_markdown}\n{END_MARKER}"
    if not pattern.search(content):
        print(
            f"Could not find {START_MARKER} / {END_MARKER} markers in {README_PATH}.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(pattern.sub(replacement, content))


def main():
    events = fetch_events()
    section = build_section(events)
    update_readme(section)
    print(f"Updated {README_PATH} activity section.")


if __name__ == "__main__":
    main()
