#!/usr/bin/env python3
"""
SSL Bypass Patch for finpy_tse
"""

import ssl
import urllib3
import requests

# Create SSL context that bypasses verification
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings()

# Create a custom pool manager with SSL bypass
def create_bypassed_poolmanager():
    """Create a PoolManager that bypasses SSL verification"""
    import urllib3
    from urllib3.poolmanager import PoolManager
    
    class BypassedPoolManager(PoolManager):
        def __init__(self, *args, **kwargs):
            kwargs['ssl_context'] = ssl.create_default_context()
            kwargs['ssl_context'].check_hostname = False
            kwargs['ssl_context'].verify_mode = ssl.CERT_NONE
            super(BypassedPoolManager, self).__init__(*args, **kwargs)
    
    return BypassedPoolManager()

# Monkey-patch urllib3.PoolManager to return bypassed version
_original_poolmanager = urllib3.PoolManager

def bypassed_poolmanager(*args, **kwargs):
    return create_bypassed_poolmanager()

urllib3.PoolManager = bypassed_poolmanager

# Also patch requests to use verify=False
_original_get = requests.get
_original_post = requests.post

def patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)
    return _original_get(url, *args, **kwargs)

def patched_post(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)
    return _original_post(url, *args, **kwargs)

requests.get = patched_get
requests.post = patched_post

# Import and test finpy_tse
import finpy_tse
print('SSL Bypass Successfully Applied to finpy_tse')

# Test Build_Market_StockList
try:
    df = finpy_tse.Build_Market_StockList(
        bourse=True,
        farabourse=True,
        payeh=True,
        detailed_list=True,
        show_progress=False,
        save_excel=False,
        save_csv=False
    )
    print('Shape: ' + str(df.shape))
    print('Columns: ' + str(list(df.columns)))
    print('Sample Data:')
    print(df.head(3).to_string())
    print('SUCCESS: finpy_tse works with SSL bypass!')
except Exception as e:
    print('Error: ' + str(e)[:500])