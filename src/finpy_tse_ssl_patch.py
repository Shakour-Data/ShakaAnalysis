"""
SSL Patch for finpy_tse to bypass certificate verification
This module patches the finpy_tse library to work around SSL certificate issues
when accessing TSE servers.
"""

import ssl
import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import urllib3.util.ssl_

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a custom SSL context that doesn't verify certificates
class NoVerifySSLContext:
    @staticmethod
    def create():
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

# Custom HTTP adapter that disables SSL verification
class NoVerifyHTTPAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        context = NoVerifySSLContext.create()
        self.poolmanager = PoolManager(num_pools=connections,
                      maxsize=maxsize,
                      block=block,
                      ssl_context=context,
                      **pool_kwargs)

def patch_finpy_tse_ssl():
    """Patch finpy_tse to disable SSL verification"""
    import finpy_tse
    
    # Patch requests session used by finpy_tse
    session = requests.Session()
    session.mount('https://', NoVerifyHTTPAdapter())
    session.mount('http://', NoVerifyHTTPAdapter())
    session.verify = False
    
    # Replace the requests module in finpy_tse
    finpy_tse.requests = session
    
    # Also patch the global requests.get if needed
    original_get = requests.get
    def patched_get(*args, **kwargs):
        kwargs['verify'] = False
        return original_get(*args, **kwargs)
    requests.get = patched_get
    
    print("  Finpy_tse SSL patch applied successfully")
    return True

def test_connection():
    """Test if we can connect to TSE servers"""
    import finpy_tse
    try:
        # Try a simple request to test connection
        test_url = "http://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/خودرو"
        response = requests.get(test_url, timeout=10, verify=False)
        if response.status_code == 200:
            print("✓ Connection to TSE servers successful")
            return True
        else:
            print(f"✗ Connection failed with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Applying SSL patch for finpy_tse...")
    if patch_finpy_tse_ssl():
        print("Testing connection...")
        test_connection()