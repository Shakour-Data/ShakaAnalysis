import sys
import ssl
import urllib3
import requests
import aiohttp
import warnings
warnings.filterwarnings('ignore')

# Simple SSL bypass
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Patch urllib3.PoolManager
from requests.packages.urllib3.poolmanager import PoolManager
_orig_pool_init = PoolManager.__init__
def _patched_pool_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ssl_context
    _orig_pool_init(self, *args, **kwargs)
PoolManager.__init__ = _patched_pool_init

# Patch requests
_orig_requests_get = requests.get
def _patched_requests_get(url, *args, **kwargs):
    kwargs['verify'] = False
    return _orig_requests_get(url, *args, **kwargs)
requests.get = _patched_requests_get

# Patch aiohttp
_orig_tcp_connector_init = aiohttp.TCPConnector.__init__
def _patched_tcp_connector_init(self, *args, **kwargs):
    kwargs['ssl'] = ssl_context
    _orig_tcp_connector_init(self, *args, **kwargs)
aiohttp.TCPConnector.__init__ = _patched_tcp_connector_init

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import finpy_tse
import finpy_tse
print('finpy_tse imported')

# Test Build_Market_StockList with direct call
try:
    print('Testing Build_Market_StockList...')
    result = finpy_tse.Build_Market_StockList(
        bourse=True,
        farabourse=False,
        payeh=False,
        detailed_list=True,
        show_progress=False,
        save_excel=False,
        save_csv=False
    )
    print(f'Result type: {type(result)}')
    
    if result is None:
        print('Result is None')
    elif isinstance(result, str):
        print(f'String length: {len(result)}')
        # Try to see if it's HTML
        if '<table' in result.lower():
            print('Result appears to be HTML table')
        else:
            print('Result appears to be text/HTML')
            # Show first 500 chars
            print(f'First 500 chars: {result[:500]}')
    else:
        print(f'Result object shape: {result.shape}')
        print(result.head(3))
        
except Exception as e:
    print(f'Error type: {type(e).__name__}')
    error_str = str(e)
    print(f'Error message: {error_str[:200]}')