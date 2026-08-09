#!/usr/bin/env python
import sqlite3
import time
import psutil
import os
from datetime import datetime
import json

DB_PATH = 'data/market_data.db'

def check_database_locks():
    """Check for database lock contention."""
    result = {}
    try:
        # Check if database file is locked
        stat_result = os.stat(DB_PATH)
        result['last_modified'] = datetime.fromtimestamp(stat_result.st_mtime).isoformat()
        result['database_size_mb'] = round(stat_result.st_size / 1024 / 1024, 2)
        
        # Try to execute a simple query to test for locks
        start_time = time.time()
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM symbols")
        cursor.fetchone()
        query_time = time.time() - start_time
        conn.close()
        
        result['query_response_time'] = round(query_time * 1000, 2)  # ms
        result['database_status'] = 'OK'
    except sqlite3.OperationalError as e:
        result['database_status'] = f'LOCKED: {e}'
        result['query_response_time'] = None
    except Exception as e:
        result['database_status'] = f'ERROR: {e}'
        result['query_response_time'] = None
    
    # Check active processes accessing the database
    processes_using_db = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.cmdline()
                if any('python' in str(cmd) for cmd in cmdline if cmd):
                    processes_using_db.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name']
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    result['active_processes'] = len(processes_using_db)
    result['timestamp'] = datetime.now().isoformat()
    return result

def monitor_database(interval_seconds=30, log_file='scheduler/db_monitor.log'):
    """Continuously monitor the database for lock issues."""
    print("Starting database monitoring...")
    while True:
        status = check_database_locks()
        log_entry = json.dumps(status)
        print(f"[{status['timestamp']}] {status['database_status']} "
              f"(Response: {status.get('query_response_time', 'N/A')}ms)")
        
        with open(log_file, 'a') as f:
            f.write(log_entry + '\n')
        
        time.sleep(interval_seconds)

if __name__ == '__main__':
    monitor_database()