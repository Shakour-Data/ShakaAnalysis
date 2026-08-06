import sys
import ssl
import urllib3
import requests
import requests.adapters
from requests.packages.urllib3.poolmanager import PoolManager
from requests.packages.urllib3.connection import HTTPSConnection

# ===== CREATE UNVERIFIED SSL CONTEXT =====
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# ===== PATCH ALL LIBRARIES BEFORE FINPY_TSE IMPORT =====
print("Patching urllib3...")

# Patch urllib3.PoolManager.__init__
_orig_pool_init = PoolManager.__init__
def _patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ssl_context
    _orig_pool_init(self, *args, **kwargs)
PoolManager.__init__ = _patched_pool_init

# Patch urllib3.connection.HTTPSConnection.__init__
_orig_https_conn_init = HTTPSConnection.__init__
def _patched_https_conn_init(self, *args, **kwargs):
    kwargs['assert_hostname'] = False
    kwargs['cert_reqs'] = ssl.CERT_NONE
    _orig_https_conn_init(self, *args, **kwargs)
HTTPSConnection.__init__ = _patched_https_conn_init

# Note: Don't patch HTTPConnectionPool.urlopen - it breaks things
# The PoolManager and HTTPSConnection patches should be enough

# ===== PATCH REQUESTS =====
print("Patching requests...")

from requests.adapters import HTTPAdapter
_orig_send = HTTPAdapter.send
def _patched_send(self, request, **kwargs):
    kwargs['verify'] = False
    return _orig_send(self, request, **kwargs)
HTTPAdapter.send = _patched_send

# ===== PATCH AIOHTTP =====
print("Patching aiohttp...")

import aiohttp
_orig_tcp_connector_init = aiohttp.TCPConnector.__init__
def _patched_tcp_connector_init(self, *args, **kwargs):
    kwargs['ssl'] = ssl_context
    _orig_tcp_connector_init(self, *args, **kwargs)
aiohttp.TCPConnector.__init__ = _patched_tcp_connector_init

# ===== DISABLE WARNINGS =====
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print("All patches applied. Now importing finpy_tse...")

# ===== IMPORT FINPY_TSE =====
import finpy_tse
print("finpy_tse imported successfully")

print("Testing Build_Market_StockList...")
try:
    result = finpy_tse.Build_Market_StockList(
        bourse=True,
        farabourse=True,
        payeh=True,
        detailed_list=True,
        show_progress=False,
        save_excel=False,
        save_csv=False
    )
    print(f"SUCCESS: Found {len(result)} symbols")
    result.to_csv('extracted_symbols.csv', index=False, encoding='utf-8')
    print("Saved to extracted_symbols.csv")
    print(result.head(3).to_string())
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
