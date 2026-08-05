#!/usr/bin/env python3
"""
Comprehensive SSL Bypass Patch for finpy_tse
Patches urllib3.PoolManager, requests, and session methods to bypass SSL verification
"""

import ssl
import urllib3
import requests
from urllib3.poolmanager import PoolManager
from requests.adapters import HTTPAdapter

# Store original classes/functions
_original_poolmanager_init = PoolManager.__init__
_original_requests_get = requests.get
_original_requests_post = requests.post

# Store original session methods
_original_session_init = requests.Session.__init__
_original_session_get = requests.Session.get
_original_session_post = requests.Session.post

# ==================== SSL Bypass Configuration ====================
# Create SSL context that doesn't verify certificates
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== SSL Bypass Implementation ====================

# Patch urllib3.PoolManager.__init__ to use unverified SSL context
def patched_poolmanager_init(self, *args, **kwargs):
    # Pass SSL context that bypasses verification to PoolManager
    kwargs['ssl_context'] = ssl.create_default_context()
    self.__dict__.update(kwargs)
    PoolManager.__bases__ = (urllib3.PoolManager,)
    return _original_poolmanager_init(self, *args, **kwargs)

# Patch requests.Session methods
def patched_session_init(self, *args, **kwargs):
    # Initialize with original parameters
    _original_session_init(self, *args, **kwargs)
    # Then configure to not verify SSL
    self.verify = False
    # Mount adapters with SSL disabled
    from requests.adapters import HTTPAdapter
    adapter = HTTPAdapter()
    self.mount('http://', adapter)
    self.mount('https://', adapter)

def patched_session_get(self, url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)
    return _original_session_get(self, url, *args, **kwargs)

def patched_session_post(self, url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)
    return _original_session_post(self, url, *args, **kwargs)

# Patch requests.get and requests.post
def patched_requests_get(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)
    return _original_requests_get(url, *args, **kwargs)

def patched_requests_post(url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)
    return _original_requests_post(url, *args, **kwargs)

# ==================== Apply All Patches ====================
# Patch urllib3.PoolManager.__init__
PoolManager.__init__ = patched_poolmanager_init

# Patch session methods
requests.Session.__init__ = patched_session_init
requests.Session.get = patched_session_get
requests.Session.post = patched_session_post

# Patch requests.get and requests.post
requests.get = patched_requests_get
requests.post = patched_requests_post

# Disable urllib3 warnings
urllib3.disable_warnings()

# ==================== Test Connection ====================
try:
    # Import finpy_tse after applying all patches
    import finpy_tse
    print('✓ SSL Bypass Successfully Applied to finpy_tse (urllib3 + requests)')

    # Test Build_Market_StockList
    df = finpy_tse.Build_Market_StockList(
        bourse=True,
        farabourse=True,
        payeh=True,
        detailed_list=True,
        show_progress=True,
        save_excel=False,
        save_csv=False
    )
    print(f'  Shape: {df.shape}')
    print(' Sample Data:')
    print(df.head(3).to_string())
    print('✓ SUCCESS: finpy_tse now works with SSL bypass!' + '\n')
except Exception as e:
    print(f'  Error: {str(e)[:500]}')
    print('SSL bypass failed - check patches')