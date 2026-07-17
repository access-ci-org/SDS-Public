#!/bin/bash

# Legacy mount layout guard. SDS now expects a single $SDS_DATA_DIR mount.
# Operators on the old compose file would have files mounted at the repo
# root instead of under data/. Refuse to start in that case so we don't
# silently rebuild from a blank slate.
for legacy in software.csv container_data spider_data software_uses \
              analytics websites logs sds_persistent.db; do
    if [ -e "$legacy" ]; then
        echo "ERROR: Detected legacy SDS data layout at $(pwd)/$legacy"
        echo ""
        echo "SDS now expects a single ./data mount. On your host:"
        echo ""
        echo "  1. Stop this container."
        echo "  2. From your repo root, run:"
        echo ""
        echo "        bash migrate_data_layout.sh"
        echo ""
        echo "  3. Update your compose file (or docker/podman run command)"
        echo "     to mount only ./config.yaml and ./data — the migration"
        echo "     script prints the exact commands."
        echo ""
        echo "See SDS_SETUP.md for details."
        exit 1
    fi
done

DATA_DIR="${SDS_DATA_DIR:-.}"

# SDS-owned state lives under $DATA_DIR/state. Created up front so a first
# boot or a wiped mount doesn't depend on any individual writer's mkdir.
# User-input paths (container_data, spider_data, software.csv) are
# deliberately not created: their absence selects run.py arguments below
# and warns about a missing mount.
mkdir -p "$DATA_DIR/state"

source /opt/miniconda3/etc/profile.d/conda.sh
conda activate /sds/env/SDS_ENV

# Initialize the command with the base script
command="python run.py"

# Check if container_data directory exists
if [ -d "$DATA_DIR/container_data" ]; then
    command="$command -c_d $DATA_DIR/container_data"
else
    echo "Warning: $DATA_DIR/container_data directory not found, skipping -c_d argument"
fi

# Check if software.csv file exists
if [ -f "$DATA_DIR/software.csv" ]; then
    command="$command -csv_f $DATA_DIR/software.csv"
else
    echo "Warning: $DATA_DIR/software.csv file not found, skipping -csv_f argument"
fi

# Check if spider_data directory exists
if [ -d "$DATA_DIR/spider_data" ]; then
    command="$command -s_d $DATA_DIR/spider_data"
else
    echo "Warning: $DATA_DIR/spider_data directory not found, skipping -s_d argument"
fi

which python
which flask

# Execute the command
echo "Running: $command"
eval $command
