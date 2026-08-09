#!/usr/bin/env python
import sqlite3
import shutil
import os
from datetime import datetime

DB_PATH = 'data/market_data.db'
BACKUP_DIR = 'data/backups'

def backup_database():
    """Create a backup of the database."""
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"market_data_backup_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        
        # Close any existing connections before backup
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, backup_path)
            print(f"Backup created: {backup_path}")
            return backup_path
        else:
            print("Database file not found")
            return None
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

def rotate_backups(max_backups=7):
    """Keep only the latest N backups to save disk space."""
    try:
        backups = sorted([
            os.path.join(BACKUP_DIR, f) 
            for f in os.listdir(BACKUP_DIR) 
            if f.startswith('market_data_backup_') and f.endswith('.db')
        ])
        
        if len(backups) > max_backups:
            for old_backup in backups[:-max_backups]:
                os.remove(old_backup)
                print(f"Removed old backup: {old_backup}")
    except Exception as e:
        print(f"Backup rotation failed: {e}")

if __name__ == '__main__':
    backup_database()
    rotate_backups()