#!/usr/bin/env python3
import subprocess
import sys
import argparse
import threading
import time
from pathlib import Path
from watchdog.observers.polling import PollingObserver # works better with docker
from watchdog.events import FileSystemEventHandler

class FlaskWatcher(FileSystemEventHandler):
    def __init__(self, reset_command):
        self.reset_command = reset_command
        self.flask_process = None
        self.restart_timer = None
        self.debounce_delay = 2

        # Define what to watch
        self.data_paths = ["spider_data", "container_data", "software.csv"]
        self.config_file = "config.yaml"

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = str(Path(event.src_path))

        # Config change - just restart Flask
        if self.config_file in file_path:
            print(f"Config changed: {file_path}")
            self.schedule_flask_restart()

        # Data change - reset database then restart Flask
        elif any(data_path in file_path for data_path in self.data_paths):
            print(f"Data changed: {file_path}")
            self.reset_and_restart()

    def on_deleted(self, event):
        print(event.src_path)
        if event.is_directory:
            return

        file_path = str(Path(event.src_path))
        # Data file deleted - reste database
        if any(data_path in file_path for data_path in self.data_paths):
            print(f"Data file deelted: {file_path}")
            self.reset_and_restart()

    def schedule_flask_restart(self):
        """Debounced Flask restart for config changes"""
        if self.restart_timer:
            self.restart_timer.cancel()

        print("Scheduling Flask restart...")
        self.restart_timer = threading.Timer(self.debounce_delay, self.restart_flask)
        self.restart_timer.start()

    def restart_flask(self):
        """Just restart Flask (for config changes)"""
        print("Restarting Flask...")
        self.stop_flask()
        time.sleep(1)  # Let port release
        self.start_flask()

    def reset_and_restart(self):
        """Reset database then restart Flask (for data changes)"""
        print("Resetting database and restarting Flask...")
        self.stop_flask()

        try:
            print("Running database reset...")
            subprocess.run(self.reset_command, shell=True, check=True)
            print("Database reset complete")
        except subprocess.CalledProcessError as e:
            print(f"Database reset failed: {e}")

        time.sleep(1)  # Let port release
        self.start_flask()

    def stop_flask(self):
        """Stop Flask if running"""
        if self.flask_process:
            self.flask_process.terminate()
            self.flask_process.wait()
            self.flask_process = None

    def start_flask(self):
        """Start Flask"""
        print("Starting Flask...")
        self.flask_process = subprocess.Popen(["flask", "run"])
        print("Flask started")

def parse_args():
    parser = argparse.ArgumentParser(description="Watch files and manage Flask app")
    parser.add_argument("-s_d", "--spider-dir", default="spider_data", help="Spider data directory")
    parser.add_argument("-c_d", "--container-dir", default="container_data", help="Container data directory")
    parser.add_argument("-csv_f", "--csv-file", default="software.csv", help="CSV file path")
    parser.add_argument("--no-initial-reset", action="store_true", help="Skip initial database reset")
    return parser.parse_args()

def main():
    args = parse_args()

    # Build reset command
    reset_command = f"python reset_database.py -s_d {args.spider_dir} -c_d {args.container_dir} -csv_f {args.csv_file}"
    print(f"Reset command: {reset_command}")
    print(f"Watching: {args.spider_dir}, {args.container_dir}, {args.csv_file}, config.yaml")

    # Initial database reset (optional)
    if not args.no_initial_reset:
        print("Running initial database reset...")
        try:
            subprocess.run(reset_command, shell=True, check=True)
            print("Initial reset complete")
        except subprocess.CalledProcessError as e:
            print(f"Initial reset failed: {e}")
            sys.exit(1)

    # Start watcher
    watcher = FlaskWatcher(reset_command)
    watcher.start_flask()

    observer = PollingObserver()
    observer.schedule(watcher, ".", recursive=True)
    observer.start()

    print("File watcher active. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        watcher.stop_flask()
        observer.stop()

    observer.join()

if __name__ == "__main__":
    main()