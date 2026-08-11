#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script contains a comprehensive SSL bypass that patches:
1. urllib3 (urllib3's connection and pool manager)
2. requests library
3. aiohttp (which is used by finpy_tse)

All patches are applied BEFORE importing finpy_tse.
"""

import sys
import ssl
import urllib3
import requests
import aiohttp
import traceback

# =============================================================================
# 1. CREATE UNVERIFIED SSL CONTEXT
# =============================================================================
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# =============================================================================
# 2. PATCH urllib3 - THE FOUNDATION
# =============================================================================

# Patch urllib3.PoolManager.__init__ to use our SSL context
_orig_pool_manager_init = urllib3.PoolManager.__init__
def _patched_pool_manager_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ssl_context
    _orig_pool_manager_init(self, *args, **kwargs)

urllib3.PoolManager.__init__ = _patched_pool_manager_init

# Patch urllib3.HTTPSConnection.__init__ to bypass hostname and cert checks
_orig_https_connection_init = urllib3.connection.HTTPSConnection.__init__
def _patched_https_connection_init(self, *args, **kwargs):
    kwargs['assert_hostname'] = False
    kwargs['cert_reqs'] = ssl.CERT_NONE
    _orig_https_connection_init(self, *args, **kwargs)

urllib3.connection.HTTPSConnection.__init__ = _patched_https_connection_init

# =============================================================================
# 3. PATCH REQUESTS LIBRARY
# =============================================================================

# Create a session with SSL verification disabled
_session = requests.Session()
_session.verify = False

# Store original methods
_orig_get = requests.get
_orig_post = requests.post
_orig_session_get = requests.Session.get
_orig_session_post = requests.Session.post

# Patch the module-level functions
def _patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    return _orig_get(url, *args, **kwargs)

def _patched_post(url, *args, **kwargs):
    kwargs['verify'] = False
    return _orig_post(url, *args, **kwargs)

# Patch the session methods
def _patched_session_get(self, url, *args, **kwargs):
    kwargs['verify'] = False
    return _orig_session_get(self, url, *args, **kwargs)

def _patched_session_post(self, url, *args, **kwargs):
    kwargs['verify'] = False
    return _orig_session_post(self, url, *args, **kwargs)

# Apply the patches
requests.get = _patched_get
requests.post = _patched_post
requests.Session.get = _patched_session_get
requests.Session.post = _patched_session_post

# =============================================================================
# 4. PATCH AIOHTTP (finpy_tse's underlying HTTP library)
# =============================================================================

# Store the original connector class
_orig_tcp_connector_init = aiohttp.TCPConnector.__init__

def _patched_tcp_connector_init(self, *args, **kwargs):
    # Force our SSL context
    kwargs['ssl'] = ssl_context
    _orig_tcp_connector_init(self, *args, **kwargs)

# Apply the patch
aiohttp.TCPConnector.__init__ = _patched_tcp_connector_init

# =============================================================================
# 5. DISABLE WARNINGS AND IMPORT FINPY_TSE
# =============================================================================

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Now import finpy_tse - it should work with our patches
print("Patching complete. Importing finpy_tse...")
import finpy_tse
print("finpy_tse imported successfully.")

# =============================================================================
# 6. TESTING THE EXTRACTION
# =============================================================================

print("\nTesting symbol extraction from TSE/OTC/Payeh...")

try:
    # Try to extract symbols
    df = finpy_tse.Build_Market_StockList(
        bourse=True,
        farabourse=True,
        payeh=True,
        detailed_list=True,
        show_progress=False,
        save_excel=False,
        save_csv=False
    )
    
    if df is not None and not df.empty:
        print(f"✓ Successfully extracted {len(df)} symbols!")
        print(f"\nSample data (first 5 rows):")
        print(df.head(5).to_string())
        
        # Save to CSV for verification
        csv_path = "extracted_symbols.csv"
        df.to_csv(csv_path, index=False)
        print(f"\n✓ Symbols saved to {csv_path}")
        
    else:
        print("✗ Failed to extract symbols - empty or None result")
        
except Exception as e:
    print(f"✗ Error during extraction: {e}")
    print("\nFull traceback:")
    traceback.print_exc()

print("\nSSL bypass test completed.")