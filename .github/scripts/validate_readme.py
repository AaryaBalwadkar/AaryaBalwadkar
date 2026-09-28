"""CI check: README markers exist, retired projects stay out, key links resolve."""

import re
import sys
import urllib.request

README_PATH = "README.md"

REQUIRED_MARKERS = [
    "<!--START_SECTION:projects-->",
    "<!--END_SECTION:projects-->",
    "<!--START_SECTION:activity-->",
    "<!--END_SECTION:activity-->",
]

# Links that must always resolve (200). Keep this list tiny to avoid flaky CI.
# NOTE: LinkedIn returns HTTP 999 to bots, so it is format-checked only.
REQUIRED_URLS = [
    "https://github.com/AaryaBalwadkar/agricnxedge-web",
    "https://github.com/AaryaBalwadkar/Agri-CNX-Edge",
    "https://github.com/AaryaBalwadkar/realtime-iot-telemetry",
    "https://github.com/AaryaBalwadkar/crop-health-mlops",
]

LINKEDIN_URL = "https://www.linkedin.com/in/aaryabalwadkar"

BANNED_PATTERNS = [
    r"github\.com/AaryaBalwadkar/Voxtiva",
    r"danielcranney/readme-generator.*socials/gmail",
    r"danielcranney/readme-generator.*socials/linkedin",
]


def main():
    with open(README_PATH, encoding="utf-8") as f:
        content = f.read()

    errors = []
    for marker in REQUIRED_MARKERS:
        if marker not in content:
            errors.append(f"missing marker: {marker}")

    for pattern in BANNED_PATTERNS:
        if re.search(pattern, content):
            errors.append(f"banned pattern still present: {pattern}")

    for url in REQUIRED_URLS:
        req = urllib.request.Request(url, headers={"User-Agent": "readme-validator"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    errors.append(f"{url} returned HTTP {resp.status}")
        except Exception as exc:  # noqa: BLE001 - report as validation error
            errors.append(f"{url} unreachable: {exc}")

    if LINKEDIN_URL not in content:
        errors.append("LinkedIn connect link missing")

    if errors:
        print("README validation failed:")
        for error in errors:
            print(f" - {error}")
        sys.exit(1)
    print("README validation passed.")


if __name__ == "__main__":
    main()
