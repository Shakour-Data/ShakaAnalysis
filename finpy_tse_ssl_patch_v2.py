#!/usr/bin/env python3
"""
SSL patch for finpy_tse module to bypass certificate verification
"""

import ssl
import requests

# Store original functions
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

# Apply monkey patch
requests.get = patched_get
requests.post = patched_post

# Also patch session methods
_original_session_get = requests.Session.get
_original_session_post = requests.Session.post

def patched_session_get(self, url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)
    return _original_session_get(self, url, *args, **kwargs)

def patched_session_post(self, url, *args, **kwargs):
    kwargs['verify'] = False
    kwargs.setdefault('timeout', 30)
    return _original_session_post(self, url, *args, **kwargs)

requests.Session.get = patched_session_get
requests.Session.post = patched_session_post

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("  Finpy_tse SSL patch applied successfully")

# Import finpy_tse after applying patches
import finpy_tse

print("  Finpy_tse module imported with SSL bypass")

# Test connection
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
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print("  Top 5:")
    print(df.head(5).to_string())
except Exception as e:
    print(f"  Error: {str(e)[:300]}")

print("  SSL patch completed")