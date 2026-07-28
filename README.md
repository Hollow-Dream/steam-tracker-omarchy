# Steam Sale Tracker — Omarchy Edition

A memory-light Steam wishlist price tracker built for Omarchy (Arch +
Hyprland + Waybar). No background daemon: a systemd user timer runs a
one-shot script every 30 minutes, writes a tiny JSON cache, and Waybar
just reads that file. Nothing sits in RAM between checks.

## Screenshots

**The Waybar widget in action** — a 🎮 icon shows how many watched games are currently on sale:

![Waybar bar with the Steam Tracker widget](screenshots/waybar-bar.png)

**Hovering shows exactly what's discounted:**

![Tooltip showing a discounted game](screenshots/sale-notification.png)

**Clicking the widget opens a quick action menu:**

![Add / Remove / View list menu](screenshots/menu-actions.png)

**Adding a game — search Steam by name, no app_id required:**

![Searching Steam by name](screenshots/search-picker.png)

**Viewing your current watchlist:**

![Current watchlist](screenshots/watchlist-view.png)

## How it works

```
systemd timer (every 30 min)
        │
        ▼
   tracker.py  ──►  Steam Store API (price_overview)
        │
        ▼
  ~/.config/steam-tracker/cache.json  ◄── Waybar reads this
        │
        ▼
  Discord webhook (optional, only fires on an actual price drop)
```

## Managing games without touching JSON

Clicking the Waybar icon opens a small `rofi` menu with three options:
- **Add game** — type a name, pick from Steam's search results, it's
  added instantly (no need to know the app_id yourself anymore)
- **Remove game** — pick from your current watchlist to drop it
- **View list** — see everything currently tracked in a scrollable menu

Hovering over the widget shows a tooltip listing everything on your
watchlist that's currently discounted, so you don't have to click in
to check.

This is powered by `steam_search.py` (searches Steam by name) and
`manage_watchlist.py` (adds/removes entries in `watchlist.json`).
You can also run either directly from a terminal if you'd rather not
use the popup:
```bash
python3 ~/.config/steam-tracker/steam_search.py "witcher"
python3 ~/.config/steam-tracker/manage_watchlist.py add 292030 "The Witcher 3"
python3 ~/.config/steam-tracker/manage_watchlist.py remove 292030
python3 ~/.config/steam-tracker/manage_watchlist.py list
```

> Uses `rofi` in dmenu mode by default. If you use `wofi`, `walker`,
> or another launcher instead, swap the `rofi -dmenu` calls in
> `steam-tracker-manage.sh` for your launcher's dmenu-equivalent mode.

## Setup

1. **Install dependencies** (jq is used by the Waybar module, Python 3
   is standard on Omarchy already, rofi powers the click-to-manage
   popup):
   ```bash
   sudo pacman -S jq rofi
   ```

2. **Create the config directory and copy files in:**
   ```bash
   mkdir -p ~/.config/steam-tracker
   cp tracker.py steam_search.py manage_watchlist.py steam-tracker-manage.sh ~/.config/steam-tracker/
   cp watchlist.example.json ~/.config/steam-tracker/watchlist.json
   cp settings.example.json ~/.config/steam-tracker/settings.json
   chmod +x ~/.config/steam-tracker/steam-tracker-manage.sh
   ```

3. **Edit your watchlist (optional)** — `watchlist.json` ships with
   two example games already in it. You can leave them for now and
   add/remove games later by clicking the Waybar icon (step 7), which
   searches Steam by name for you — no app_id hunting required. If
   you'd rather set it up by hand right now:
   ```bash
   nano ~/.config/steam-tracker/watchlist.json
   ```
   Find app IDs from a game's Steam store URL, e.g.
   `store.steampowered.com/app/292030/` → app_id `292030`.

4. **(Optional) Add a Discord webhook** in `settings.json` if you want
   drop alerts pushed to a channel. Leave it blank to skip Discord
   entirely and rely on Waybar only.

5. **Install the systemd units:**
   ```bash
   mkdir -p ~/.config/systemd/user
   cp steam-tracker.service steam-tracker.timer ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now steam-tracker.timer
   ```

6. **Check it ran:**
   ```bash
   systemctl --user status steam-tracker.timer
   journalctl --user -u steam-tracker.service -n 20
   cat ~/.config/steam-tracker/cache.json
   ```

7. **Add the Waybar module** — merge the contents of
   `waybar-module.json` into your Waybar config (e.g.
   `~/.config/waybar/config.jsonc`, or wherever your active theme's
   config lives), then add `"custom/steam-tracker"` to one of your
   `modules-left/center/right` arrays. Reload Waybar
   (`killall waybar && waybar &`, or your usual reload keybind).

## Why this stays lightweight

- **No persistent process.** `tracker.py` runs, does its work, exits.
  Nothing is resident in memory between the 30-minute intervals.
- **systemd, not cron or a Python scheduler loop.** It's already part
  of your base system — no extra scheduler library or dependency.
- **Waybar polls a flat file**, not the tracker itself — reading a
  small JSON file every 5 minutes is essentially free.
- **Atomic writes** (`os.replace`) mean Waybar never reads a
  half-written cache file mid-update.
- **Cache stays in sync with the watchlist.** Removing a game prunes
  its cached data immediately, so it can't linger and falsely show up
  as "on sale" after you've stopped tracking it.

## Tweaking the interval

Edit `OnUnitActiveSec=30min` in `steam-tracker.timer` to whatever
cadence you like, then:
```bash
systemctl --user daemon-reload
systemctl --user restart steam-tracker.timer
```
