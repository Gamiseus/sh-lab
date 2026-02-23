import sys
import json
import logging
from steam.client import SteamClient

# Configure logging to stderr to keep stdout clean for JSON
logging.basicConfig(stream=sys.stderr, level=logging.ERROR)

def fetch_metadata(app_ids):
    client = SteamClient()
    try:
        # Anonymous login (synchronous)
        client.anonymous_login()
        
        # Fetch PICS data
        # get_product_info returns {appid: data}
        # We need to handle retry/timeout internally if needed, but client handles basic retries.
        products = client.get_product_info(app_ids, timeout=15)
        
        if not products:
             print(json.dumps({}))
             return

        # PICS data needs to be serialized. 
        # The returned data is a dict/KeyValues. We accept it as is, JSON encoder handles dicts.
        # But 'apps' key in result contains the data.
        # Structure: {'apps': {10: {...}}, 'packages': ...}
        
        # We only care about apps
        apps = products.get('apps', {})
        
        # Ensure we just print the dict
        print(json.dumps(apps, default=str))

    except Exception as e:
        logging.error(f"Failed to fetch metadata: {e}")
        # Print empty JSON on failure
        print(json.dumps({}))
    finally:
        client.logout()
        client.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Usage: fetch_metadata.py <appid1> <appid2> ...")
        sys.exit(1)
    
    # helper: parse args. Argv[1] could be comma separated or multiple args
    ids = []
    for arg in sys.argv[1:]:
        ids.extend([int(x) for x in arg.split(',') if x.strip()])
    
    fetch_metadata(ids)
