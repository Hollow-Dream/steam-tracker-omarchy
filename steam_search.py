#!/usr/bin/env python3
"""
Search Steam by game name and print matches as
"app_id<TAB>name" lines — one per result. Used interactively by
steam-tracker-manage.sh, but works fine by itself:

    
"""

import json
import sys
import urllib.parse
import urllib.request

SEARCH_API = "https://store.steampowered.com/api/storesearch/"
USER_AGENT = "steam-tracker-omarchy/1.0"


def search(term, cc="us", limit=10):
    query = urllib.parse.urlencode({"term": term, "cc": cc, "l": "english"})
    url = f"{SEARCH_API}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"[error] search failed: {e}", file=sys.stderr)
        return []

    return data.get("items", [])[:limit]


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Usage: steam_search.py <search term>", file=sys.stderr)
        sys.exit(1)

    term = " ".join(sys.argv[1:])
    results = search(term)

    if not results:
        print("No matches found.", file=sys.stderr)
        sys.exit(1)

    for item in results:
        # Tab-separated so shell scripts can parse uber clean.
        print(f"{item['id']}\t{item['name']}")


if __name__ == "__main__":
    main()
