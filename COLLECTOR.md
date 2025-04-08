# SDS Data Collector

## Overview

This utility script is designed to help HPC administrators and/or software deployment teams collect container definition files and module (lmod) software data across multiple HPC clusters. It systematically locates Singularity definition files (.def) and Dockerfiles, preserves their directory structure during collection, and can optionally gather module system information for comprehensive software environment analysis.

The collector serves as a key component of the broader Software Documentation Service for analyzing, and documenting software deployment across multiple HPC environments.

## Features

- Recursively searches directory trees for container definition files with configurable depth
- Preserves full path structure when copying files to ensure context is maintained
- Collects comprehensive module system data using `module spider` with optimized terminal settings to prevent truncation
- Works in both local and remote execution modes to support various operational scenarios
- Supports secure SSH connections with customizable options for security compliance
- Creates organized directory structure for collected data to simplify subsequent analysis
- Includes CSV file generation for later integration with data analysis tools
- Can synchronize data between systems using rsync with proper error handling
- Supports older systems through environment adaptation commands

## Requirements

- Python 3.6+
- SSH access (for remote mode)
- rsync (for synchronization)
- Lmod module system (for module data collection)
- Standard Unix utilities (find, cp, etc.)

## Installation
If you are reading this then the collector script (`collector.py`) already exist on your repo
If you want to use it in a different location:
1. Copy the script to your local machine or server:
    ```
    scp collector.py your_username@your_server:~/
    ```
2. Ensure Python 3.6+ is installed:
    ```
    python3 --version
    ```
3. No additional Python packages are required as the script only uses the standard library

## Usage

### Basic Usage (Local Mode)

Run the script directly on the system where you want to search for container definitions:

```bash
python3 collector.py --directory /path/to/search --resource cluster_name
```
This will search the specified directory for container definition files and save them to ./container_data/cluster_name/ while preserving their original directory structure.

### Remote Mode (Execute on Cluster)
Execute the script on a remote cluster and retrieve the results:
```bash
python3 collector.py --directory /path/on/cluster --resource cluster_name --remote cluster.example.edu --username your_username --sync
```

This will:
1. Connect to the remote cluster via SSH
2. Copy the script to the remote system
3. Execute it there to collect container definitions
4. Sync the results back to your local machine

### Collecting Module Data
Include module system information in your collection:
```bash
python3 collector.py --directory /path/to/search --resource cluster_name --lmod
```
Add the `--lmod` flag. This will collect container definitions and also run module spider to gather information about available software modules, saving the output to ./spider_data/cluster_name/.

### Using with Python Version Issues
If your remote system has an older Python version with compatibility issues and you need to load a new one:
```bash
python3 collector.py --directory /path/to/search --resource cluster_name --remote cluster.example.edu --username your_username --pre_command "module load python/3.8" --sync
```
Change the `--pre_command` to the command you need to switch your environment to python3.6+
This loads a newer Python version before executing the script on the remote system.

## Command Line Arguments
- `--directory`: Directory to search for definition files (required)
- `--resource`: Name of the cluster/resource for organization (required)
- `--max-depth`: Maximum directory depth to search (default: 4)
- `--sync`: Enable rsync to transfer files between machines
- `--remote`: Hostname of the remote machine for server mode
- `--username`: Username for the remote machine login
- `--remote_path`: Path on remote machine to store files (default: current directory)
- `--ssh_options`: SSH options as a list for custom SSH configurations
- `--run_mode`: Explicitly set where the script is running ("server" or "cluster")
- `--pre_command`: Command to run on the remote machine before executing the script
- `--lmod`: Collect module system data using module spider

## Output Structure
The script creates an organized directory structure:
```
./container_data/
  └── {resource_name}/
      ├── {resource_name}.csv    # CSV file with container metadata
      └── {preserved_directory_structure}/
          └── {definition_files}  # Original definition files with paths preserved

./spider_data/
  └── {resource_name}/
      └── {resource_name}_spider.txt  # Complete output from module spider
```

## Detailed Examples
### Find container definitions in /apps directory on local machine
When you need to document container definitions on your local system:
```bash
python3 collector.py --directory /apps --resource local_system
```
This will:
- Search the /apps directory recursively up to depth 4
- Identify all .def files and Dockerfiles
- Copy them to ./container_data/local_system/ while preserving paths
- Create a local_system.csv file with basic metadata

### Execute on a remote HPC cluster and sync results back
For collecting data from a remote HPC system:
```bash
python3 collector.py --directory /opt/apps --resource hpc_cluster --remote hpc.university.edu --username researcher --sync
```
This connects to the remote HPC system, runs the collection process there, and synchronizes the results back to your local machine, making it easy to gather data from multiple clusters.

### Collect both container and module information from a cluster
For a comprehensive software environment snapshot:
```bash
python3 collector.py --directory /share/apps --resource compute_cluster --remote cluster.org --username user123 --lmod --sync
```
This collects both container definitions and complete module information, providing a full picture of the software environment on the compute_cluster system.

### Using custom SSH options for secure environments
For environments with strict security requirements:
```bash
python3 collector.py --directory /secure/apps --resource secure_cluster --remote secure.facility.gov --username security_user --ssh_options "-i ~/.ssh/secure_key" "-p 2222" "-o StrictHostKeyChecking=yes"
```
