#!/bin/bash --login
cd sds
conda activate SDS_ENV

# Initialize the command with the base script
command="python run.py"

# Check if container_data directory exists
if [ -d "container_data/" ]; then
    command="$command -c_d container_data/"
else
    echo "Warning: container_data/ directory not found, skipping -c_d argument"
fi

# Check if software.csv file exists
if [ -f "software.csv" ]; then
    command="$command -csv_f software.csv"
else
    echo "Warning: software.csv file not found, skipping -csv_f argument"
fi

# Check if spider_data directory exists
if [ -d "spider_data/" ]; then
    command="$command -s_d spider_data/"
else
    echo "Warning: spider_data/ directory not found, skipping -s_d argument"
fi

which python
which flask

# Execute the command
echo "Running: $command"
eval $command
