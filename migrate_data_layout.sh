#!/usr/bin/env bash
# Moves legacy SDS data layout into the new ./data/ structure:
#   user inputs (software.csv, container_data/, ...) -> ./data/
#   SDS-written state (analytics/, sds_persistent.db, ...) -> ./data/state/
#
# Run from your SDS repo root with the container stopped.
set -euo pipefail

USER_INPUTS=(software.csv container_data spider_data software_uses)
STATE_FILES=(analytics websites logs sds_persistent.db)

DATA_DIR="data"
STATE_DIR="$DATA_DIR/state"

# Build the list of pending moves: only files that actually exist at root.
pending=()  # each entry is "src|dest"
for f in "${USER_INPUTS[@]}"; do
    [ -e "$f" ] && pending+=("$f|$DATA_DIR/$f")
done
for f in "${STATE_FILES[@]}"; do
    [ -e "$f" ] && pending+=("$f|$STATE_DIR/$f")
done

if [ ${#pending[@]} -eq 0 ]; then
    echo "No legacy SDS files detected in the current directory."
    echo "If you've already migrated, you're done. If you expected files here,"
    echo "double-check you're running this from your SDS root."
    exit 0
fi

# Check for conflicts: pending moves whose destination already exists.
conflicts=()
for entry in "${pending[@]}"; do
    dest="${entry#*|}"
    [ -e "$dest" ] && conflicts+=("$dest")
done

if [ ${#conflicts[@]} -gt 0 ]; then
    echo "ERROR: cannot migrate — these destinations already exist:"
    echo ""
    for c in "${conflicts[@]}"; do
        echo "  $c"
    done
    echo ""
    echo "This usually means the migration ran before AND a legacy file"
    echo "reappeared at the repo root (e.g. an app process re-created it)."
    echo ""
    echo "Decide which copy to keep, then either:"
    echo "  - if the existing destination is current, remove or back up the"
    echo "    new copy at the repo root:"
    echo "      mv <stray-file> <stray-file>.bak"
    echo "  - if the new copy at root is the one you want, move the"
    echo "    destination aside first:"
    echo "      mv <destination> <destination>.bak"
    echo ""
    echo "Then re-run this script."
    exit 1
fi

# Make sure we can write into data/.
if ! mkdir -p "$STATE_DIR" 2>/dev/null; then
    echo "ERROR: cannot create $STATE_DIR — permission denied."
    echo ""
    echo "This usually means $DATA_DIR/ exists with restrictive ownership"
    echo "(often left behind by a prior container run as root)."
    echo ""
    echo "If $DATA_DIR/ contains files you want to keep, move or back them"
    echo "up first so they're not lost:"
    echo ""
    echo "    sudo mv $DATA_DIR ${DATA_DIR}.backup"
    echo ""
    echo "If $DATA_DIR/ is empty (typical for a stale Docker mountpoint),"
    echo "remove it:"
    echo ""
    echo "    sudo rm -rf $DATA_DIR"
    echo ""
    echo "Then re-run this script."
    exit 1
fi

moved=()
for entry in "${pending[@]}"; do
    src="${entry%|*}"
    dest="${entry#*|}"
    mkdir -p "$(dirname "$dest")"
    mv "$src" "$dest"
    moved+=("$src -> $dest")
done

echo ""
echo "Moved:"
for line in "${moved[@]}"; do
    echo "  $line"
done
echo ""

echo "Your compose file now needs only two mounts. Replace the volumes: block with:"
echo ""
echo "    volumes:"
echo "      - ./config.yaml:/sds/config.yaml"
echo "      - ./data:/sds/data"
echo ""

echo "Or run with docker directly:"
echo ""
echo "    docker run -d --name sds \\"
echo "      -p 8080:80 \\"
echo "      -v ./config.yaml:/sds/config.yaml \\"
echo "      -v ./data:/sds/data \\"
echo "      sds"
echo ""

if command -v podman >/dev/null 2>&1; then
    echo "Or run with podman directly:"
    echo ""
    echo "    podman run -d --name sds \\"
    echo "      -p 8080:80 \\"
    echo "      -v ./config.yaml:/sds/config.yaml \\"
    echo "      -v ./data:/sds/data \\"
    echo "      sds"
    echo ""
fi

echo "If you have scripts that push data to this VM (cron jobs, rsync"
echo "wrappers, post-deploy hooks, etc.), update their destination paths —"
echo "they now live under data/, e.g. ./data/spider_data/<resource>/ instead"
echo "of ./spider_data/<resource>/."
echo ""
