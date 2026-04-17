"""
PICS Metadata Fetcher — subprocess invoked by SteamClientService.

Accepts app IDs via stdin (one per line or comma-separated) to avoid
OS command-line length limits. Connects once, fetches all, disconnects.

Outputs JSON to stdout. All logging goes to stderr.
"""
import sys
import json
import logging
from steam.client import SteamClient

# Configure logging to stderr to keep stdout clean for JSON
logging.basicConfig(stream=sys.stderr, level=logging.ERROR)


def fetch_metadata(app_ids):
    if not app_ids:
        print(json.dumps({}))
        return

    client = SteamClient()
    try:
        client.anonymous_login()

        # PICS supports large batches natively — fetch all at once.
        # The steam library internally chunks if needed.
        products = client.get_product_info(app_ids, timeout=30)

        if not products:
            print(json.dumps({}))
            return

        # Structure: {'apps': {10: {...}}, 'packages': ...}
        apps = products.get('apps', {})
        print(json.dumps(apps, default=str))

    except Exception as e:
        logging.error(f"Failed to fetch metadata: {e}")
        print(json.dumps({}))
    finally:
        try:
            client.logout()
            client.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    ids = []

    # Priority 1: Read from stdin if data is piped
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            for token in raw.replace('\n', ',').split(','):
                token = token.strip()
                if token.isdigit():
                    ids.append(int(token))

    # Priority 2: Fall back to argv (for small batches / manual testing)
    if not ids and len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            for token in arg.split(','):
                token = token.strip()
                if token.isdigit():
                    ids.append(int(token))

    if not ids:
        logging.error("No app IDs provided via stdin or argv")
        print(json.dumps({}))
        sys.exit(0)

    fetch_metadata(ids)
