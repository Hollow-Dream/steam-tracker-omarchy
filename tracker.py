#!/usr/bin/env python3
"""
Steam Sale Tracker for Waybar in Omarchy

Runs as a one-shot job under a systemd user timer.

Flow:
  1. Read watchlist.json which is the list of Steam app IDs 
  2. Use Steam's API to get the price of the IDs
  3. Compare against the last-known price in cache.json
  4. Write cache.json (used by the Waybar module) and exit


   
Config lives in ~/.config/steam-tracker/
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

CONFIG_DIR = os.path.expanduser("~/.config/steam-tracker")
WATCHLIST_PATH = os.path.join(CONFIG_DIR, "watchlist.json")
CACHE_PATH = os.path.join(CONFIG_DIR, "cache.json")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")

STEAM_API = "https://store.steampowered.com/api/appdetails"
USER_AGENT = "steam-tracker-omarchy/1.0"


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r") as f:
        return json.load(f)


def save_json(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)  


def fetch_price(app_id, cc="us"):
    """Hits the Steam Store API for a single app. Returns dict or None."""
    url = f"{STEAM_API}?appids={app_id}&cc={cc}&filters=price_overview"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"[warn] failed to fetch app {app_id}: {e}", file=sys.stderr)
        return None

    entry = data.get(str(app_id), {})
    if not entry.get("success"):
        return None

    overview = entry.get("data", {}).get("price_overview")
    if not overview:
        return None  # If the game is free or does not have a price overview, we skip it.

    return {
        "current_cents": overview["final"],
        "original_cents": overview["initial"],
        "discount_pct": overview["discount_percent"],
        "currency": overview["currency"],
    }


def send_discord_alert(webhook_url, name, old_price, new_price):
    payload = {
        "content": (
            f"🔻 **{name}** dropped: "
            f"${old_price / 100:.2f} → ${new_price['current_cents'] / 100:.2f} "
            f"({new_price['discount_pct']}% off)"
        )
    }
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.URLError as e:
        print(f"[warn] discord webhook failed: {e}", file=sys.stderr)


def main():
    os.makedirs(CONFIG_DIR, exist_ok=True)

    watchlist = load_json(WATCHLIST_PATH, {"games": []})
    cache = load_json(CACHE_PATH, {"games": {}})
    settings = load_json(SETTINGS_PATH, {"discord_webhook_url": "", "region": "us"})

    games = watchlist.get("games", [])
    region = settings.get("region", "us")
    webhook = settings.get("discord_webhook_url", "")

    # Drop cached games that are no longer on the watchlist
    # so removed games can't keep showing up as "on sale" forever.

    current_app_ids = {str(g["app_id"]) for g in games}
    cache["games"] = {
        app_id: entry
        for app_id, entry in cache["games"].items()
        if app_id in current_app_ids
    }

    drops = []
    now = datetime.now(timezone.utc).isoformat()

    for game in games:
        app_id = game["app_id"]
        name = game.get("name", str(app_id))
        price = fetch_price(app_id, cc=region)

        if price is None:
            continue

        prev = cache["games"].get(str(app_id))
        cache["games"][str(app_id)] = {
            "name": name,
            **price,
            "checked_at": now,
        }

        if prev and price["current_cents"] < prev["current_cents"]:
            drops.append((name, prev["current_cents"], price))
            if webhook:
                send_discord_alert(webhook, name, prev["current_cents"], price)

    # Generate summary and details for Waybar module

    on_sale = [
        g for g in cache["games"].values() if g.get("discount_pct", 0) > 0
    ]

    cache["summary"] = (
        f"{len(on_sale)} on sale" if on_sale else "no sales"
    )
    cache["details"] = (
        "\n".join(
            f"{g['name']}: {g['discount_pct']}% off "
            f"(${g['current_cents']/100:.2f}, was ${g['original_cents']/100:.2f})"
            for g in sorted(on_sale, key=lambda g: -g["discount_pct"])
        )
        if on_sale
        else "Nothing on the watchlist is currently discounted"
    )

    # Kept separately so can see "did anything change since the last check" apart from "what's on sale right now."
    
    cache["new_drops"] = len(drops)
    cache["last_run"] = now

    save_json(CACHE_PATH, cache)

    if drops:
        print(f"{len(drops)} price drop(s) found.")
    else:
        print("No changes.")


if __name__ == "__main__":
    main()