#!/usr/bin/env bash
# Triggered by clicking the Waybar Steam Tracker module.
# Lets you search Steam by name and add/remove games from the
# watchlist without ever hand-editing JSON.
#
# Uses `rofi` in dmenu mode (works well on Omarchy). If you'd rather
# use `walker` or another launcher, swap the `rofi -dmenu` calls below
# for your launcher's dmenu-compatible mode.

set -euo pipefail

CONFIG_DIR="$HOME/.config/steam-tracker"
SEARCH_SCRIPT="$CONFIG_DIR/steam_search.py"
MANAGE_SCRIPT="$CONFIG_DIR/manage_watchlist.py"

action=$(printf "Add game\nRemove game\nView list" | rofi -dmenu -p "Steam Tracker")

case "$action" in
  "Add game")
    term=$(rofi -dmenu -p "Search Steam for:" < /dev/null)
    [ -z "$term" ] && exit 0

    results=$(python3 "$SEARCH_SCRIPT" "$term" || true)
    if [ -z "$results" ]; then
      notify-send "Steam Tracker" "No matches found for '$term'."
      exit 0
    fi

    # Show "Name" only in the picker, keep app_id mapped via cut.
    picked_name=$(echo "$results" | cut -f2 | rofi -dmenu -p "Pick a game:")
    [ -z "$picked_name" ] && exit 0

    picked_line=$(echo "$results" | grep -P "\t${picked_name}$" | head -n1)
    app_id=$(echo "$picked_line" | cut -f1)

    python3 "$MANAGE_SCRIPT" add "$app_id" "$picked_name"
    notify-send "Steam Tracker" "Added: $picked_name"

    # Refresh the cache immediately so Waybar reflects the new game
    # without waiting for the next 30-min timer tick.
    systemctl --user start steam-tracker.service &
    ;;

  "Remove game")
    current=$(python3 "$MANAGE_SCRIPT" list || true)
    if [ -z "$current" ]; then
      notify-send "Steam Tracker" "Watchlist is empty."
      exit 0
    fi

    picked_name=$(echo "$current" | cut -f2 | rofi -dmenu -p "Remove which game:")
    [ -z "$picked_name" ] && exit 0

    picked_line=$(echo "$current" | grep -P "\t${picked_name}$" | head -n1)
    app_id=$(echo "$picked_line" | cut -f1)

    python3 "$MANAGE_SCRIPT" remove "$app_id"
    notify-send "Steam Tracker" "Removed: $picked_name"

    # Refresh the cache immediately so a removed game's stale sale
    # data doesn't keep showing on Waybar until the next timer tick.
    systemctl --user start steam-tracker.service &
    ;;

  "View list")
    current=$(python3 "$MANAGE_SCRIPT" list || true)
    if [ -z "$current" ]; then
      notify-send "Steam Tracker" "Watchlist is empty."
    else
      # rofi has no line-count limit, unlike notify-send popups which
      # get truncated by the notification daemon after a few lines.
      count=$(echo "$current" | wc -l)
      echo "$current" | cut -f2 | rofi -dmenu -p "Watchlist (${count} games):" -no-custom
    fi
    ;;

  *)
    exit 0
    ;;
esac