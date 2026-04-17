import asyncio
import logging
import json
import sys
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Maximum time to wait for the PICS subprocess (seconds).
# Large libraries (~800 IDs) may take a while on first fetch.
SUBPROCESS_TIMEOUT = 120


class SteamClientService:
    def __init__(self):
        self.script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "scripts",
            "fetch_metadata.py",
        )

    async def start(self):
        """No persistent connection needed for script approach."""
        pass

    async def get_product_info(self, app_ids: List[int]) -> Dict:
        """
        Fetch PICS data via isolated subprocess.
        
        IDs are passed via stdin (comma-separated) to avoid OS
        command-line length limits on large libraries.
        """
        if not app_ids:
            return {}

        try:
            # Prepare stdin payload: comma-separated IDs
            stdin_data = ",".join(str(x) for x in app_ids)

            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                self.script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data.encode()),
                timeout=SUBPROCESS_TIMEOUT,
            )

            if proc.returncode != 0:
                logger.error(f"Metadata script failed (rc={proc.returncode}): {stderr.decode()}")
                return {}

            output = stdout.decode().strip()
            if not output:
                return {}

            return json.loads(output)

        except asyncio.TimeoutError:
            logger.error(f"PICS subprocess timed out after {SUBPROCESS_TIMEOUT}s for {len(app_ids)} IDs")
            try:
                proc.kill()
            except Exception:
                pass
            return {}
        except Exception as e:
            logger.error(f"Subprocess PICS Error: {e}")
            return {}

    async def close(self):
        pass


# Singleton
_steam_service = SteamClientService()

def get_steam_client() -> SteamClientService:
    return _steam_service
