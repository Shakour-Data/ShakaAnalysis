#!/usr/bin/env python3
"""
Data Validation Module - Validates data completeness and integrity
"""

import sqlite3
import os
from datetime import datetime, timedelta
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'market_data.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def validate_data_completeness():
    """Comprehensive data completeness validation"""
    conn = get_db_connection()
    results = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'HEALTHY',
        'checks': [],
        'warnings': [],
        'errors': []
    }
    
    # Check 1: Symbol coverage
    try:
        total_symbols = conn.execute("SELECT COUNT(*) FROM symbols WHERE is_active = 1").fetchone()[0]
        symbols_with_data = conn.execute("""
            SELECT COUNT(DISTINCT symbol_id) 
            FROM price_data 
            WHERE symbol_id IN (SELECT id FROM symbols WHERE is_active = 1)
        """).fetchone()[0]
        
        coverage = (symbols_with_data / total_symbols * 100) if total_symbols > 0 else 0
        
        check = {
            'name': 'Symbol Coverage',
            'status': 'PASS' if coverage >= 90 else 'WARNING',
            'details': f'{symbols_with_data}/{total_symbols} symbols have data ({coverage:.1f}%)'
        }
        results['checks'].append(check)
        
        if coverage < 90:
            results['warnings'].append(f'Symbol coverage is low: {coverage:.1f}%')
            
    except Exception as e:
        results['errors'].append(f'Symbol coverage check failed: {str(e)}')
    
    # Check 2: Data freshness (last update within 2 days)
    try:
        latest_record = conn.execute("""
            SELECT MAX(date) as latest_date 
            FROM price_data
        """).fetchone()
        
        if latest_record and latest_record['latest_date']:
            latest_date = datetime.strptime(latest_record['latest_date'], '%Y-%m-%d')
            days_since_update = (datetime.now() - latest_date).days
            
            freshness_status = 'PASS' if days_since_update <= 2 else 'WARNING'
            check = {
                'name': 'Data Freshness',
                'status': freshness_status,
                'details': f'Latest data: {latest_record["latest_date"]} ({days_since_update} days ago)'
            }
            results['checks'].append(check)
            
            if days_since_update > 2:
                results['warnings'].append(f'Data is {days_since_update} days old (expected <= 2 days)')
        else:
            results['checks'].append({
                'name': 'Data Freshness',
                'status': 'ERROR',
                'details': 'No data records found'
            })
            results['errors'].append('No price data records found')
            
    except Exception as e:
        results['errors'].append(f'Data freshness check failed: {str(e)}')
    
    # Check 3: Data continuity (no gaps > 5 days)
    try:
        symbols = conn.execute("SELECT id, symbol FROM symbols WHERE is_active = 1").fetchall()
        
        gap_issues = []
        for sym in symbols:
            dates = conn.execute("""
                SELECT date FROM price_data 
                WHERE symbol_id = ? 
                ORDER BY date
            """, (sym['id'],)).fetchall()
            
            if len(dates) > 1:
                date_list = [datetime.strptime(d['date'], '%Y-%m-%d') for d in dates]
                for i in range(1, len(date_list)):
                    gap = (date_list[i] - date_list[i-1]).days
                    if gap > 5:
                        gap_issues.append(f"{sym['symbol']}: {gap}-day gap between {date_list[i-1].strftime('%Y-%m-%d')} and {date_list[i].strftime('%Y-%m-%d')}")
        
        if gap_issues:
            results['warnings'].extend(gap_issues[:5])  # Show first 5 gaps
            results['checks'].append({
                'name': 'Data Continuity',
                'status': 'WARNING',
                'details': f'{len(gap_issues)} gaps found in time series data'
            })
        else:
            results['checks'].append({
                'name': 'Data Continuity',
                'status': 'PASS',
                'details': 'No gaps > 5 days found in time series'
            })
            
    except Exception as e:
        results['errors'].append(f'Data continuity check failed: {str(e)}')
    
    # Check 4: Data quality (reasonable price ranges)
    try:
        quality_issues = conn.execute("""
            SELECT COUNT(*) as count 
            FROM price_data 
            WHERE close <= 0 OR volume < 0 OR (high < low)
        """).fetchone()
        
        if quality_issues['count'] > 0:
            results['warnings'].append(f'{quality_issues["count"]} records with invalid price/volume data')
            results['checks'].append({
                'name': 'Data Quality',
                'status': 'WARNING',
                'details': f'{quality_issues["count"]} records with invalid values'
            })
        else:
            results['checks'].append({
                'name': 'Data Quality',
                'status': 'PASS',
                'details': 'All records have valid price and volume data'
            })
            
    except Exception as e:
        results['errors'].append(f'Data quality check failed: {str(e)}')
    
    # Check 5: Volume data coverage
    try:
        records_with_volume = conn.execute("""
            SELECT COUNT(*) as count 
            FROM price_data 
            WHERE volume IS NOT NULL AND volume > 0
        """).fetchone()
        
        total_records = conn.execute("SELECT COUNT(*) FROM price_data").fetchone()
        
        if total_records['count'] > 0:
            volume_coverage = records_with_volume['count'] / total_records['count'] * 100
            results['checks'].append({
                'name': 'Volume Coverage',
                'status': 'PASS' if volume_coverage >= 80 else 'WARNING',
                'details': f'{volume_coverage:.1f}% of records have volume data'
            })
        else:
            results['checks'].append({
                'name': 'Volume Coverage',
                'status': 'ERROR',
                'details': 'No price data records found'
            })
            
    except Exception as e:
        results['errors'].append(f'Volume coverage check failed: {str(e)}')
    
    # Check 6: Symbol diversity (ensure both TSE and OTC are represented)
    try:
        exchanges = conn.execute("""
            SELECT exchange, COUNT(*) as count 
            FROM symbols 
            WHERE is_active = 1 
            GROUP BY exchange
        """).fetchall()
        
        exchange_list = [dict(e) for e in exchanges]
        results['checks'].append({
            'name': 'Market Coverage',
            'status': 'PASS',
            'details': f"Exchanges represented: {', '.join(f\"{e['exchange']} ({e['count']})\" for e in exchange_list)}"
        })
        
    except Exception as e:
        results['errors'].append(f'Market coverage check failed: {str(e)}')
    
    # Determine overall status
    error_count = len(results['errors'])
    warning_count = len(results['warnings'])
    
    if error_count > 0:
        results['overall_status'] = 'CRITICAL'
    elif warning_count > 0:
        results['overall_status'] = 'WARNING'
    else:
        results['overall_status'] = 'HEALTHY'
    
    conn.close()
    return results

def generate_validation_report():
    """Generate a human-readable validation report"""
    results = validate_data_completeness()
    
    report = []
    report.append("=" * 60)
    report.append("DATA VALIDATION REPORT")
    report.append(f"Generated: {results['timestamp']}")
    report.append("=" * 60)
    report.append("")
    
    # Overall status
    status_icon = {'HEALTHY': '✅', 'WARNING': '⚠️', 'CRITICAL': '❌'}
    report.append(f"Overall Status: {status_icon.get(results['overall_status'], '❓')} {results['overall_status']}")
    report.append("")
    
    # Individual checks
    report.append("CHECK RESULTS:")
    for check in results['checks']:
        status_icon = {'PASS': '✅', 'WARNING': '⚠️', 'ERROR': '❌'}
        icon = status_icon.get(check['status'], '❓')
        report.append(f"  {icon} {check['name']}: {check['details']}")
    
    report.append("")
    
    # Warnings
    if results['warnings']:
        report.append("WARNINGS:")
        for w in results['warnings']:
            report.append(f"  ⚠️  {w}")
        report.append("")
    
    # Errors
    if results['errors']:
        report.append("ERRORS:")
        for e in results['errors']:
            report.append(f"  ❌ {e}")
        report.append("")
    
    return '\n'.join(report)

def save_validation_report():
    """Save validation report to file"""
    report = generate_validation_report()
    
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = os.path.join(reports_dir, f'validation_report_{timestamp}.txt')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return report_path

def run_validation_checks():
    """Run all validation checks and return summary"""
    results = validate_data_completeness()
    
    print("=" * 60)
    print("DATA VALIDATION REPORT")
    print(f"Generated: {results['timestamp']}")
    print("=" * 60)
    print(f"\nOverall Status: {results['overall_status']}")
    print(f"\nChecks Performed: {len(results['checks'])}")
    print(f"Warnings: {len(results['warnings'])}")
    print(f"Errors: {len(results['errors'])}")
    
    print("\nDetailed Results:")
    for check in results['checks']:
        status_icon = {'PASS': '✅', 'WARNING': '⚠️', 'ERROR': '❌'}
        icon = status_icon.get(check['status'], '❓')
        print(f"  {icon} {check['name']}: {check['details']}")
    
    if results['warnings']:
        print("\nWarnings:")
        for w in results['warnings'][:5]:
            print(f"  ⚠️  {w}")
    
    if results['errors']:
        print("\nErrors:")
        for e in results['errors']:
            print(f"  ❌ {e}")
    
    # Save report
    report_path = save_validation_report()
    print(f"\nReport saved to: {report_path}")
    
    return results

if __name__ == "__main__":
    run_validation_checks()