import asyncio
import logging
import json
import sys
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class SteamClientService:
    def __init__(self):
        self.script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "fetch_metadata.py")

    async def start(self):
        """No persistent connection needed for script approach."""
        pass

    async def get_product_info(self, app_ids: List[int]) -> Dict:
        """Fetch PICS data via isolated subprocess."""
        if not app_ids:
            return {}

        try:
            # Chunking handled by caller, but we pass args
            args = [str(x) for x in app_ids]
            
            # Run script
            # python app/scripts/fetch_metadata.py id1 id2 ...
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                self.script_path,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"Metadata script failed: {stderr.decode()}")
                return {}
            
            output = stdout.decode().strip()
            if not output:
                return {}
            
            return json.loads(output)

        except Exception as e:
            logger.error(f"Subprocess PICS Error: {e}")
            return {}

    async def close(self):
        pass

    # Stub methods to satisfy dependencies if any, though users shouldn't call them directly
    # kept simple
        
# Singleton
_steam_service = SteamClientService()

def get_steam_client() -> SteamClientService:
    return _steam_service

# Singleton
_steam_service = SteamClientService()

def get_steam_client() -> SteamClientService:
    return _steam_service
