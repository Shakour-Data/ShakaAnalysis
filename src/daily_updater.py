#!/usr/bin/env python3
"""
Daily data update scheduler for market data
Runs at 7:00 PM daily to fetch and store updated market data
"""

import schedule
import time
import logging
from datetime import datetime
import threading
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_updates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def import_data_extractor():
    """Import data extractor modules"""
    try:
        from comprehensive_extractor import (
            extract_all_symbols,
            extract_symbol_data,
            create_comprehensive_database
        )
        return {
            'extract_symbols': extract_all_symbols,
            'extract_data': extract_symbol_data,
            'create_database': create_comprehensive_database
        }
    except ImportError:
        logger.error("Could not import data extraction modules")
        return None

def get_database_module():
    """Import database modules"""
    try:
        from database import (
            initialize_database,
            bulk_insert_symbols,
            bulk_insert_price_data,
            get_symbol_id,
            update_data_metadata,
            get_data_completeness
        )
        return {
            'init_db': initialize_database,
            'insert_symbols': bulk_insert_symbols,
            'insert_price_data': bulk_insert_price_data,
            'get_symbol_id': get_symbol_id,
            'update_metadata': update_data_metadata,
            'get_completeness': get_data_completeness
        }
    except ImportError as e:
        logger.error(f"Could not import database modules: {e}")
        return None

class DailyDataUpdater:
    def __init__(self):
        self.data_extractor = import_data_extractor()
        self.database = get_database_module()
        
        if not self.data_extractor or not self.database:
            raise RuntimeError("Failed to initialize required modules")
    
    def run_daily_update(self):
        """Execute daily data update process"""
        logger.info("Starting daily market data update")
        start_time = datetime.now()
        
        try:
            # Initialize database
            self.database['init_db']()
            logger.info("Database initialized")
            
            # Extract all symbols
            symbols = self.data_extractor['extract_symbols']()
            logger.info(f"Extracted {len(symbols)} symbols")
            
            # Update symbols in database
            if symbols:
                inserted_symbols = self.database['insert_symbols'](symbols)
                logger.info(f"Inserted {inserted_symbols} symbols into database")
            
            # Process each symbol for data update
            total_processed = 0
            for i, symbol in enumerate(symbols):
                try:
                    # Extract data for this symbol
                    symbol_data = self.data_extractor['extract_data'](symbol)
                    
                    if symbol_data:
                        # Get symbol ID
                        symbol_id = self.database['get_symbol_id'](symbol)
                        
                        if symbol_id:
                            # Insert price data
                            inserted_count = self.database['insert_price_data'](symbol_id, symbol_data['price_data'])
                            total_processed += inserted_count
                            
                            # Update metadata
                            self.database['update_metadata'](
                                symbol,
                                'price',
                                symbol_data['metadata']['start_date'],
                                symbol_data['metadata']['end_date'],
                                len(symbol_data['price_data'])
                            )
                    
                    # Progress update
                    if (i + 1) % 10 == 0:
                        logger.info(f"Processed {i + 1}/{len(symbols)} symbols")
                        
                except Exception as e:
                    logger.error(f"Error processing symbol {symbol}: {str(e)}")
                    continue
            
            # Log completion summary
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"Daily update completed successfully")
            logger.info(f"  - Processed {len(symbols)} symbols")
            logger.info(f"  - Inserted {total_processed} price records")
            logger.info(f"  - Duration: {duration}")
            
            # Log data completeness
            completeness = self.database['get_completeness']()
            logger.info(f"  - Data completeness: {completeness['completeness_percentage']}% ({completeness['symbols_with_data']}/{completeness['total_symbols']} symbols)")
            
            return True
            
        except Exception as e:
            logger.error(f"Daily update failed: {str(e)}")
            return False
    
    def run_maintenance_tasks(self):
        """Run maintenance tasks"""
        logger.info("Running daily maintenance tasks")
        
        try:
            completeness = self.database['get_completeness']()
            
            # Log data quality metrics
            logger.info(f"Data quality metrics:")
            logger.info(f"  - Total symbols: {completeness['total_symbols']}")
            logger.info(f"  - Symbols with data: {completeness['symbols_with_data']}")
            logger.info(f"  - Total records: {completeness['total_records']:,}")
            logger.info(f"  - Completeness: {completeness['completeness_percentage']}%")
            
            # Log top symbols by record count
            if completeness['symbol_details']:
                logger.info(f"Top 5 symbols by record count:")
                for detail in completeness['symbol_details'][:5]:
                    logger.info(f"  - {detail['symbol']}: {detail['record_count']:,} records")
            
            return True
            
        except Exception as e:
            logger.error(f"Maintenance tasks failed: {str(e)}")
            return False

def start_scheduler():
    """Start the daily update scheduler"""
    updater = DailyDataUpdater()
    
    # Schedule daily update at 7:00 PM
    schedule.every().day.at("19:00").do(updater.run_daily_update)
    
    # Schedule maintenance at 7:05 PM (5 minutes after data update)
    schedule.every().day.at("19:05").do(updater.run_maintenance_tasks)
    
    logger.info("Daily update scheduler started")
    logger.info("Scheduled tasks:")
    logger.info("  - Daily data update: 7:00 PM")
    logger.info("  - Maintenance tasks: 7:05 PM")
    
    # Run initial update
    logger.info("Running initial data update...")
    updater.run_daily_update()
    updater.run_maintenance_tasks()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        start_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {str(e)}")
        raise
