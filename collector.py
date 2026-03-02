import argparse
import subprocess
import sys
import os
from pathlib import Path
import time
import tempfile
import shutil

def is_docker_file(path: Path) -> bool:
    if path.suffix == '.def':
        return True

    try:
        with open(path, 'r', errors='ignore') as f:
            first_few_lines = ''.join([f.readline() for _ in range(5)])
            if 'FROM' in first_few_lines:
                return True
    except Exception:
        pass

    return False

def setup_argparse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Uses ssh to access the resource and uses the find command to locate and copy .def \
            and docker files while preserving directory structure. Optionally uses rsync to sync the files."
    )
    parser.add_argument("--directory", help="Directory (in your resource) to search for definition files")
    parser.add_argument("--resource", help="Name of the current resource/cluster")
    parser.add_argument("--max-depth", type=int, default=4, help="Maximum directory depth to search (default: 4)")
    parser.add_argument("--sync", action="store_true", help="Use rsync to transfer files between machines")
    parser.add_argument("--remote", help="The hostname of the remote machine (cluster or server)")
    parser.add_argument("--username", help="The username for the remote machine")
    parser.add_argument("--remote_path", default="./", help="Path on remote machine to store the files (default: current directory)")
    parser.add_argument("--ssh_options", nargs="+", default=["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"],
                        help="SSH options as a list (e.g., '--ssh_options -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null')")
    parser.add_argument("--run_mode", choices=["server", "cluster"],
                        help="Explicitly set where the script is running: 'server' (connect to cluster) or 'cluster' (run locally)")
    parser.add_argument("--pre_command", help="Command to run on the remote machine before executing the script (e.g., 'module load python/3.8')")
    parser.add_argument("--lmod", action="store_true", help="Also collect lmod data from the system (gets output of 'module spider')")
    return parser.parse_args()

def find_container_files(start_dir: Path, max_depth: int, resource_name: str) -> Path:
    """Search for container definition files locally and save them with structure preserved."""
    # Create container_data directory structure
    dest_dir = Path(f"./container_data/{resource_name}")
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Initialize CSV file
    csv_file = dest_dir / f"{resource_name}.csv"
    with open(csv_file, 'w') as cf:
        cf.write("software_name,software_versions,container_name,definition_file,container_file,container_description,notes\n")

    print("Starting file search using find command...")

    # Run the find command to get all matching files
    cmd = [
        "find",
        str(start_dir),
        "-maxdepth", str(max_depth),
        "-type", "f",
        "\\(", "-name", "*.def", "-o", "-name", "*docker*", "\\)",
        "2>/dev/null"
    ]

    try:
        # Use shell=True to allow redirecting stderr with 2>/dev/null
        result = subprocess.run(" ".join(cmd), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        found_files = result.stdout.strip().split('\n')
        # Remove empty entries
        found_files = [f for f in found_files if f]

        print(f"Found {len(found_files)} files to process")

        # Copy files while preserving path structure
        processed_count = 0
        for file_path in found_files:
            if not file_path:  # Skip empty strings
                continue

            source_path = Path(file_path)
            # Preserve the entire absolute path by converting it to a path without the leading '/'
            # This ensures we keep the full directory structure
            path_without_leading_slash = str(source_path).lstrip('/')
            dest_path = dest_dir / path_without_leading_slash

            # Ensure *docker* files are actual dockerfiles
            if "docker" in file_path and not is_docker_file(source_path):
                continue

            # Create parent directories if they don't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle duplicate filenames
            if dest_path.exists():
                dest_path = Path(str(dest_path) + "_2")

            # Copy the file
            try:
                subprocess.run(["cp", file_path, str(dest_path)], check=True)
                print(f"Copied: {file_path}")
                # Update CSV with this file
                with open(csv_file, 'a') as cf:
                    cf.write(f",,,{file_path},,,,\n")
                processed_count += 1
            except subprocess.CalledProcessError as e:
                print(f"Failed to copy {file_path}: {e}")

        print(f"Successfully processed {processed_count}/{len(found_files)} definition files")
        return dest_dir

    except subprocess.CalledProcessError as e:
        print(f"Error executing find command: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def collect_module_spider_data(resource_name: str) -> Path:
    """Collect module spider data and save it."""
    # Create spider_data directory structure
    dest_dir = Path(f"./spider_data/{resource_name}")
    dest_dir.mkdir(parents=True, exist_ok=True)

    spider_file = dest_dir / f"{resource_name}_spider.txt"

    print("Collecting module spider data...")

    try:
        env = os.environ.copy()
        env["COLUMNS"] = "1000" # set a very wide terminal width so 'module spider' doesn't get truncated
        env["TERM"] = "xterm-256-color" # set a terminal type that supports wide width

        # Run module spider command and save output
        # Run command within login shell
        result = subprocess.run(["bash", "-l", "-c", f"module spider > {spider_file}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

        if result.returncode != 0:
            print(f"Error running module spider command: {result.stderr}")
        with open(spider_file, 'w') as f:
            f.write(result.stdout)

        print(f"Module spider data saved to {spider_file}")
        return dest_dir

    except subprocess.CalledProcessError as e:
        print(f"Error executing module spider command: {e}")
        # Continue execution, don't exit
        return dest_dir
    except Exception as e:
        print(f"Unexpected error collecting module data: {e}")
        return dest_dir

def sync_directory_to_remote(args, local_directory: Path, remote_subdir: str):
    """Sync files from the current machine to a specific subdirectory on the remote machine."""
    if not (args.remote and args.username):
        print(f"Error: --remote and --username are required for syncing {local_directory} files.")
        return False

    try:
        print(f"Syncing {local_directory} TO remote machine {args.remote}...")
        # Build rsync command
        rsync_cmd = [
            "rsync",
            "-avz"  # archive mode, verbose, compress
        ]
        # Add SSH options for rsync
        if args.ssh_options:
            # For rsync, we need to format the SSH options differently
            ssh_args = " ".join(args.ssh_options)
            rsync_cmd.extend(["-e", f"ssh {ssh_args}"])

        # Get just the directory name (e.g., "container_data" from "./container_data/resource")
        dir_name = local_directory.parts[-2]  # Get the parent directory name
        resource_name = local_directory.parts[-1]  # Get the resource name

        # Create the subdirectory on the remote first
        create_dir_cmd = [
            "ssh"
        ]
        if args.ssh_options:
            create_dir_cmd.extend(args.ssh_options)

        remote_path = f"{args.remote_path}/{dir_name}"
        create_dir_cmd.extend([
            f"{args.username}@{args.remote}",
            f"mkdir -p {remote_path}"
        ])

        print(f"Creating directory on remote: {remote_path}")
        subprocess.run(create_dir_cmd, check=True)

        # Now do the actual rsync
        rsync_cmd.extend([
            f"{local_directory}/",
            f"{args.username}@{args.remote}:{args.remote_path}/{dir_name}/{resource_name}/"
        ])

        # Execute rsync command
        print(f"Running: {' '.join(rsync_cmd)}")
        result = subprocess.run(rsync_cmd, check=True)

        print(f"Sync of {local_directory} to remote machine completed successfully.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error syncing {local_directory} to remote machine: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during sync of {local_directory}: {e}")
        return False

def run_on_remote_and_sync_back(args):
    """Connect to the remote cluster, run the search there, and sync results back."""
    if not (args.remote and args.username):
        print("Error: --remote and --username are required for remote execution.")
        sys.exit(1)

    try:
        # Get the current script path
        current_script = Path(sys.argv[0]).resolve()

        # Add SSH options
        ssh_cmd = [
            "ssh"
        ]
        # Add SSH options
        if args.ssh_options:
            ssh_cmd.extend(args.ssh_options)

        ssh_cmd.extend([
            f"{args.username}@{args.remote}",
            "mkdir -p ~/sds_collector"
        ])
        print(f"Running command: {' '.join(ssh_cmd)}")
        subprocess.run(ssh_cmd, check=True)

        # Build SCP command
        scp_cmd = [
            "scp"
        ]

        # Add SSH options
        if args.ssh_options:
            scp_cmd.extend(args.ssh_options)

        scp_cmd.extend([
            str(current_script),
            f"{args.username}@{args.remote}:~/sds_collector/"
        ])
        print("Copying script to remote cluster...")
        subprocess.run(scp_cmd, check=True)

        # Run the script on the remote cluster
        remote_script_name = current_script.name

        # Build the remote command with appropriate flags
        remote_cmd_parts = [
            "cd ~/sds_collector",
        ]

        # Add pre_command if specified
        if args.pre_command:
            remote_cmd_parts.append(args.pre_command)

        # Base command to run the script
        script_cmd = f"python3 {remote_script_name} --resource {args.resource} --max-depth {args.max_depth} --run_mode cluster"

        # Add directory if specified
        if args.directory:
            script_cmd += f" --directory {args.directory}"

        # Add lmod flag if specified
        if args.lmod:
            script_cmd += " --lmod"

        remote_cmd_parts.append(script_cmd)

        # Join all command parts with '&&'
        remote_cmd = " && ".join(remote_cmd_parts)

        # Build SSH command
        ssh_cmd = [
            "ssh"
        ]

        # Add SSH options
        if args.ssh_options:
            ssh_cmd.extend(args.ssh_options)

        ssh_cmd.extend([
            f"{args.username}@{args.remote}",
            f"bash -l -c '{remote_cmd}'"
        ])

        print(f"Running script on remote cluster: {args.remote}. Script: {' '.join(ssh_cmd)}")
        subprocess.run(ssh_cmd, check=True)

        # If sync is enabled, sync the files back from remote cluster
        if args.sync:
            # Check if container_data directory exists on remote
            if args.directory:  # Only check for container data if a directory was specified
                container_remote_path = f"~/sds_collector/container_data/{args.resource}/"
                check_cmd = ["ssh"]
                if args.ssh_options:
                    check_cmd.extend(args.ssh_options)

                check_cmd.extend([
                    f"{args.username}@{args.remote}",
                    f"test -d {container_remote_path} && echo 'exists' || echo 'not-exists'"
                ])

                result = subprocess.run(check_cmd, stdout=subprocess.PIPE, text=True, check=True)
                if "exists" in result.stdout:
                    print(f"Syncing container_data from remote cluster...")
                    # Create local directories if they don't exist
                    Path(f"./container_data/{args.resource}").mkdir(parents=True, exist_ok=True)

                    rsync_cmd = ["rsync", "-avz"]
                    if args.ssh_options:
                        ssh_args = " ".join(args.ssh_options)
                        rsync_cmd.extend(["-e", f"ssh {ssh_args}"])

                    rsync_cmd.extend([
                        f"{args.username}@{args.remote}:~/sds_collector/container_data/{args.resource}/",
                        f"./container_data/{args.resource}/"
                    ])

                    # Execute rsync command
                    print(f"Running: {' '.join(rsync_cmd)}")
                    subprocess.run(rsync_cmd, check=True)

            # Check for spider_data
            if args.lmod:
                # Sync spider_data if it exists on remote
                spider_remote_path = f"~/sds_collector/spider_data/{args.resource}/"
                check_cmd = ["ssh"]
                if args.ssh_options:
                    check_cmd.extend(args.ssh_options)

                check_cmd.extend([
                    f"{args.username}@{args.remote}",
                    f"test -d {spider_remote_path} && echo 'exists' || echo 'not-exists'"
                ])

                result = subprocess.run(check_cmd, stdout=subprocess.PIPE, text=True, check=True)
                if "exists" in result.stdout:
                    print(f"Syncing spider_data from remote cluster...")
                    Path(f"./spider_data/{args.resource}").mkdir(parents=True, exist_ok=True)

                    rsync_spider_cmd = ["rsync", "-avz"]
                    if args.ssh_options:
                        ssh_args = " ".join(args.ssh_options)
                        rsync_spider_cmd.extend(["-e", f"ssh {ssh_args}"])

                    rsync_spider_cmd.extend([
                        f"{args.username}@{args.remote}:~/sds_collector/spider_data/{args.resource}/",
                        f"./spider_data/{args.resource}/"
                    ])

                    subprocess.run(rsync_spider_cmd, check=True)

            print(f"Sync from remote cluster completed successfully.")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error during remote execution: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def determine_run_mode(args):
    """Determine whether we're running on the server or cluster."""
    if args.run_mode:
        # User explicitly specified the run mode
        return args.run_mode
    elif args.remote and args.username:
        # If remote details are provided, assume we're on the server
        return "server"
    else:
        # Otherwise, assume we're on the cluster
        return "cluster"

def main() -> None:
    args = setup_argparse()

    # Check if required arguments are provided
    if not args.resource:
        print("No resource name specified. Exiting")
        sys.exit(1)

    if not args.directory and not args.lmod:
        print("Neither directory nor lmod flag specified. You must provide at least one. Exiting")
        sys.exit(1)

    # Determine if we're on the server or cluster
    run_mode = determine_run_mode(args)

    if run_mode == "server":
        # We're on the server - run on cluster and sync back
        print(f"Running in SERVER mode. Will connect to cluster {args.remote} and run commands there.")
        success = run_on_remote_and_sync_back(args)
        if not success:
            print("Remote cluster execution failed.")
            sys.exit(1)
    else:
        # We're on the cluster - run locally
        print("Running in CLUSTER mode (local execution)...")

        if args.directory:
            # Process container files
            start_dir = Path(args.directory)
            if start_dir.exists() and start_dir.is_dir():
                container_dir = find_container_files(start_dir, args.max_depth, args.resource)
                print(f"Container files saved to {container_dir}/")
            else:
                print(f"Directory {start_dir} does not exist. Skipping container file search.")

        # Collect lmod data if requested
        if args.lmod:
            # Collect module spider data
            spider_dir = collect_module_spider_data(args.resource)
            print(f"Module spider data saved to {spider_dir}/")

        # If sync is enabled and remote details are provided, sync to server
        if args.sync and args.remote and args.username:
            # Sync container data
            sync_directory_to_remote(args, container_dir, "container_data")
            # Sync lmod data if collected
            if args.lmod:
                sync_directory_to_remote(args, spider_dir, "spider_data")

if __name__ == "__main__":
    start_time = time.time()
    main()
    total_time = time.time() - start_time
    print(f"Total execution time: {total_time:.2f} seconds")