#!/usr/bin/env python3
"""
Add, remove, or list games in ~/.config/steam-tracker/watchlist.json

Usage:
    manage_watchlist.py add <app_id> <name...>
    manage_watchlist.py remove <app_id>
    manage_watchlist.py list
"""

import json
import os
import sys

CONFIG_DIR = os.path.expanduser("~/.config/steam-tracker")
WATCHLIST_PATH = os.path.join(CONFIG_DIR, "watchlist.json")


def load():
    if not os.path.exists(WATCHLIST_PATH):
        return {"games": []}
    with open(WATCHLIST_PATH, "r") as f:
        return json.load(f)


def save(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp_path = WATCHLIST_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, WATCHLIST_PATH)


def cmd_add(app_id, name):
    data = load()
    app_id = int(app_id)

    if any(g["app_id"] == app_id for g in data["games"]):
        print(f"{name} is already on the watchlist.")
        return

    data["games"].append({"app_id": app_id, "name": name})
    save(data)
    print(f"Added {name} (app_id {app_id}).")


def cmd_remove(app_id):
    data = load()
    app_id = int(app_id)
    before = len(data["games"])
    data["games"] = [g for g in data["games"] if g["app_id"] != app_id]

    if len(data["games"]) == before:
        print(f"No watchlist entry with app_id {app_id}.")
        return

    save(data)
    print(f"Removed app_id {app_id}.")


def cmd_list():
    data = load()
    for g in data["games"]:
        print(f"{g['app_id']}\t{g['name']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    action = sys.argv[1]

    if action == "add" and len(sys.argv) >= 4:
        cmd_add(sys.argv[2], " ".join(sys.argv[3:]))
    elif action == "remove" and len(sys.argv) >= 3:
        cmd_remove(sys.argv[2])
    elif action == "list":
        cmd_list()
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
