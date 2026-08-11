import ssl
import urllib3

# Apply SSL bypass to urllib3.PoolManager
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
_orig_init = urllib3.PoolManager.__init__
def _patched_init(self, *args, **kwargs):
    kwargs['ssl_context'] = ctx
    _orig_init(self, *args, **kwargs)
urllib3.PoolManager.__init__ = _patched_init
urllib3.disable_warnings()

# Now import functions from comprehensive_extractor
import sys
sys.path.insert(0, '.')

# Read the extractor file, extract functions, and execute
import importlib.util
spec = importlib.util.spec_from_file_location("comprehensive_extractor", "comprehensive_extractor.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Now use the functions
extract_all_symbols = module.extract_all_symbols

print("Starting symbol extraction...")
symbols = extract_all_symbols()
if symbols:
    print(f"Extracted {len(symbols)} symbols")
    print("Sample symbols:", [s["symbol"] for s in symbols[:5]])
else:
    print("No symbols extracted!")