#!/usr/bin/env python3
import subprocess
import sys
import argparse
import threading
import time
from pathlib import Path
from datetime import datetime
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

class FlaskWatcher(FileSystemEventHandler):
    def __init__(self, reset_command, auto_update_interval=86400):
        self.reset_command = reset_command
        self.flask_process = None
        self.restart_timer = None # for rerunning app
        self.reset_timer = None # for resetting db
        self.debounce_delay = 5
        self.auto_update_interval = auto_update_interval # Default 24 hours in seconds
        self.periodic_timer = None

        # Define what to watch
        self.data_paths = ["spider_data", "container_data", "software_uses", "software.csv"]
        self.config_file = "config.yaml"


    def schedule_periodic_update(self):
        """Schedule the next automatic data update"""
        if self.periodic_timer:
            self.periodic_timer.cancel()

        print(f"Scheduling next automatic database update in {self.auto_update_interval} seconds ({self.auto_update_interval/3600:.1f} hours)")
        self.periodic_timer = threading.Timer(self.auto_update_interval, self.periodic_update)
        self.periodic_timer.start()

    def periodic_update(self):
        """Perform periodic database update"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Performing scheduled 24-hour database update...")
        self.reset_and_restart()
        # Reschedule the next periodic update
        # self.schedule_periodic_update()

    def schedule_reset_and_restart(self):
        """Debounced database reset and Flask restart for data changes"""
        if self.reset_timer:
            self.reset_timer.cancel()

        print("Scheduling database reset and Flask restart...")
        self.reset_timer = threading.Timer(self.debounce_delay, self.reset_and_restart_with_timer_reset)
        self.reset_timer.start()

    def reset_and_restart_with_timer_reset(self):
        """Wrapper to reset database, restart Flask, and reset the periodic timer"""
        self.reset_and_restart()
        # Reset the 24-hour timer since we just did an update
        # print("Resetting 24-hour auto-update timer...")
        # self.schedule_periodic_update()

    def on_modified(self, event):

        file_path = str(Path(event.src_path))

        # Config change - just restart Flask
        if self.config_file in file_path:
            print(f"Config changed: {file_path}")
            self.schedule_flask_restart()

        # Data change - reset database then restart Flask
        elif any(data_path in file_path for data_path in self.data_paths):
            print(f"Data changed: {file_path}")
            self.schedule_reset_and_restart()

    def on_moved(self, event):
        # no return for directory as it will ignore children dirs/files
        file_path = str(Path(event.src_path))
        if any(data_path in file_path for data_path in self.data_paths):
            print(f"Data moved: {file_path}")
            self.schedule_reset_and_restart()

    def on_created(self, event):
        # no return for directory as it will ignore children dirs/files
        file_path = str(Path(event.src_path))
        if any(data_path in file_path for data_path in self.data_paths):
            print(f"Data file created: {file_path}")
            self.schedule_reset_and_restart()

    def on_deleted(self, event):
        if event.is_directory:
            return

        file_path = str(Path(event.src_path))
        # Data file deleted - reset database
        if any(data_path in file_path for data_path in self.data_paths):
            print(f"Data file deleted: {file_path}")
            self.schedule_reset_and_restart()

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
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Resetting database and restarting Flask...")
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
        self.flask_process = subprocess.Popen([sys.executable, "-m", "flask", "run", "--port", "8080"])
        print("Flask started")

def parse_args():
    from app.paths import data_dir
    d = data_dir()
    parser = argparse.ArgumentParser(description="Watch files and manage Flask app")
    parser.add_argument("-s_d", "--spider_dir", default=str(d / "spider_data"), help="Spider data directory")
    parser.add_argument("-c_d", "--container_dir", default=str(d / "container_data"), help="Container data directory")
    parser.add_argument("-csv_f", "--csv_file", default=str(d / "software.csv"), help="CSV file path")
    parser.add_argument("-s_u_d", "--software_use_dir", default=str(d / "software_uses"), help="Software use directory for custom example use information.")
    parser.add_argument("--no-initial-reset", action="store_true", help="Skip initial database reset")
    parser.add_argument("--update-interval", type=int, default=86400,
        help="Automatic database update interval in seconds (default: 86400 = 24 hours)")
    return parser.parse_args()

def main():
    args = parse_args()

    # Build reset command
    reset_command = f"python reset_database.py -s_d {args.spider_dir} -c_d {args.container_dir} -csv_f {args.csv_file}"
    print(f"Reset command: {reset_command}")
    print(f"Watching: {args.spider_dir}, {args.container_dir}, {args.csv_file}, {args.software_use_dir}, config.yaml")
    print(f"Auto-update interval: {args.update_interval} seconds ({args.update_interval/3600:.1f} hours)")

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
    watcher = FlaskWatcher(reset_command, auto_update_interval=args.update_interval)
    watcher.start_flask()
    # watcher.schedule_periodic_update()

    observer = PollingObserver()
    observer.schedule(watcher, ".", recursive=True)
    observer.start()

    print("File watcher active with automatic updates. Press Ctrl+C to stop.")

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