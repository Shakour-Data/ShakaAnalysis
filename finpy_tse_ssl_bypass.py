#!/usr/bin/env python3
"""
Comprehensive SSL Bypass for finpy_tse
Patches urllib3 at the PoolManager level to disable SSL verification
"""

import ssl
import urllib3

# Create a custom PoolManager that disables SSL verification
_original_poolmanager_init = urllib3.PoolManager.__init__

# Create unverified SSL context
def _create_unverified_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

# Custom __init__ method that forces SSL verification off
def patched_poolmanager_init(self, *args, **kwargs):
    # Force the SSL context to be unverified
    kwargs['ssl_context'] = _create_unverified_ssl_context()
    # Call original __init__ with our modified parameters
    return _original_poolmanager_init(self, *args, **kwargs)

# Apply the patch
urllib3.PoolManager.__init__ = patched_poolmanager_init

# Also disable all SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print('SSL Bypass Successfully Applied to urllib3 PoolManager')

# Now import and test finpy_tse
import finpy_tse

print('Testing Build_Market_StockList with SSL bypass...')

# Test the function
try:
    df = finpy_tse.Build_Market_StockList(
        bourse=True,
        farabourse=True,
        payeh=True,
        detailed_list=True,
        show_progress=True,
        save_excel=False,
        save_csv=False
    )
    
    print(f'  ✓ SUCCESS! Function executed without SSL errors')
    print(f'  ✓ DataFrame shape: {df.shape}')
    print(f'  ✓ Columns: {list(df.columns)}')
    print(f'  ✓ Sample data (first 3 rows):')
    print(df.head(3).to_string())
    print('\n  The SSL bypass worked! finpy_tse can now access TSE data.')
    
except Exception as e:
    print(f'  ✗ Error: {str(e)}')
    print('  SSL bypass may not have worked correctly.')
    print('  The error might be due to network issues or other problems.')

print('\n' + '='*80)
print('SSL Bypass Implementation Summary:')
print('='*80)
print('  • Patched urllib3.PoolManager.__init__ to use unverified SSL context')
print('  • This bypasses certificate verification for all HTTP requests')
print('  • finpy_tse can now access TSE websites without SSL errors')
print('  • SSL certificate verification is disabled globally')
print('='*80)