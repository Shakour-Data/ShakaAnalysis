#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shaka Analysis Daily Scheduler
Runs the complete analysis pipeline on a daily schedule.
Configured for Windows Task Scheduler or cron-style execution.
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime


# Core pipeline script path
PIPELINE_SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'complete_pipeline_simple.py')
PIPELINE_SCRIPT = os.path.abspath(PIPELINE_SCRIPT)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'outputs')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_pipeline():
    """Execute the complete analysis pipeline."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Shaka Analysis Pipeline...")
    try:
        # Execute pipeline
        result = subprocess.run(
            [sys.executable, PIPELINE_SCRIPT],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(PIPELINE_SCRIPT)
        )
        if result.returncode == 0:
            print("✅ Pipeline execution completed successfully")
            # Print summary output
            stdout_lines = result.stdout.strip().split('\n')
            for line in stdout_lines:
                if any(kw in line for kw in ['✅', '🎉', 'COMPLETE', 'Saved', 'Calculated']):
                    print(f"  {line}")
        else:
            print("❌ Pipeline execution failed")
            print(f"Error output: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Pipeline execution error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Shaka Analysis Daily Scheduler')
    parser.add_argument('--run-now', action='store_true', help='Run the pipeline immediately')
    parser.add_argument('--setup-task', action='store_true', help='Configure Windows Task Scheduler (placeholder)')
    args = parser.parse_args()

    if args.run_now:
        success = run_pipeline()
        sys.exit(0 if success else 1)
    elif args.setup_task:
        print("Setting up Windows Task Scheduler (placeholder - requires admin rights)")
        print("1. Open Task Scheduler (Win+R -> taskschd.msc)")
        print("2. Create Basic Task → Daily → Action: Start a program")
        print(f'3. Program/script: {sys.executable}')
        print(f'4. Add arguments: "{PIPELINE_SCRIPT}"')
        print("5. Trigger: Daily, repeat every 1 day")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()