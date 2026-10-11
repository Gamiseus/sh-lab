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

    import time
    client = SteamClient()
    try:
        login_res = client.anonymous_login()
        if login_res != 1:
            time.sleep(2)
            login_res = client.anonymous_login()
            if login_res != 1:
                sys.stderr.write(f"Anonymous login failed with code {login_res}\n")
                sys.stderr.flush()
                print(json.dumps({}))
                return

        all_apps = {}
        chunk_size = 100
        total = len(app_ids)

        for i in range(0, total, chunk_size):
            chunk = app_ids[i:i + chunk_size]
            try:
                if not client.connected:
                    client.anonymous_login()

                products = client.get_product_info(chunk, timeout=25)
                if products and 'apps' in products:
                    for app_id, app_info in products['apps'].items():
                        if isinstance(app_info, dict):
                            all_apps[str(app_id)] = {
                                'common': app_info.get('common', {}),
                                'extended': app_info.get('extended', {})
                            }
            except Exception as e:
                sys.stderr.write(f"Error fetching chunk {i}..{i+len(chunk)}: {e}\n")

            curr = min(i + len(chunk), total)
            sys.stderr.write(f"PROGRESS:{curr}:{total}\n")
            sys.stderr.flush()

        print(json.dumps(all_apps, default=str))

    except Exception as e:
        sys.stderr.write(f"Failed to fetch metadata: {e}\n")
        sys.stderr.flush()
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
