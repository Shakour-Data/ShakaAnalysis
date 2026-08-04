#!/usr/bin/env python3
"""
SSL Bypass Patch for finpy_tse
"""

import ssl
import urllib3
import requests

# Core SSL Bypass
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch requests module
_original_get = requests.get
_original_post = requests.post

def patched_get(url, *args, **kwargs):
    kwargs['verify'] = False
    return _original_get(url, *args, **kwargs)

def patched_post(url, *args, **kwargs):
    kwargs['verify'] = False
    return _original_post(url, *args, **kwargs)

requests.get = patched_get
requests.post = patched_post

# Patch session methods
_original_session_get = requests.Session.get
_original_session_post = requests.Session.post

def patched_session_get(self, url, *args, **kwargs):
    kwargs['verify'] = False
    return _original_session_get(self, url, *args, **kwargs)

def patched_session_post(self, url, *args, **kwargs):
    kwargs['verify'] = False
    return _original_session_post(self, url, *args, **kwargs)

requests.Session.get = patched_session_get
requests.Session.post = patched_session_post

# Apply to finpy_tse
import finpy_tse
print('SSL Bypass Successfully Applied to finpy_tse')

# Test connection
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
    print(f'  Shape: {df.shape}')
    print('Sample:', df.head(5).to_string())
except Exception as e:
    print(f'  Error: {e[:500]}')
