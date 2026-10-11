import asyncio
import logging
import json
import sys
import os
from typing import Optional, List, Dict, Any, Callable

logger = logging.getLogger(__name__)


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

    async def get_product_info(
        self,
        app_ids: List[int],
        progress_callback: Optional[Callable[[int, int], Any]] = None,
    ) -> Dict:
        """
        Fetch PICS data via isolated subprocess.
        
        IDs are passed via stdin (comma-separated) to avoid OS
        command-line length limits on large libraries.
        Progress updates from stderr are dispatched to progress_callback.
        """
        if not app_ids:
            return {}

        stdin_data = ",".join(str(x) for x in app_ids)
        timeout = max(300, int(len(app_ids) * 0.5) + 60)

        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                self.script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )

            # Write stdin immediately and close it
            proc.stdin.write(stdin_data.encode())
            await proc.stdin.drain()
            proc.stdin.close()
            await proc.stdin.wait_closed()

            async def read_stderr():
                while True:
                    line = await proc.stderr.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    if text.startswith("PROGRESS:"):
                        parts = text.split(":")
                        if len(parts) == 3 and progress_callback:
                            try:
                                curr, tot = int(parts[1]), int(parts[2])
                                if asyncio.iscoroutinefunction(progress_callback):
                                    await progress_callback(curr, tot)
                                else:
                                    progress_callback(curr, tot)
                            except Exception:
                                pass
                    elif text:
                        logger.debug(f"[fetch_metadata] {text}")

            async def read_stdout():
                chunks = []
                while True:
                    chunk = await proc.stdout.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                return b"".join(chunks)

            stdout_bytes, _ = await asyncio.wait_for(
                asyncio.gather(read_stdout(), read_stderr()),
                timeout=timeout,
            )
            await proc.wait()

            if proc.returncode != 0:
                logger.error(f"Metadata script exited with code {proc.returncode}")
                return {}

            output = stdout_bytes.decode("utf-8", errors="replace").strip()
            if not output:
                return {}

            return json.loads(output)

        except asyncio.TimeoutError:
            logger.error(f"PICS subprocess timed out after {timeout}s for {len(app_ids)} IDs")
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            return {}
        except Exception as e:
            logger.error(f"Subprocess PICS Error: {e}")
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            return {}

    async def close(self):
        pass


# Singleton
_steam_service = SteamClientService()

def get_steam_client() -> SteamClientService:
    return _steam_service
