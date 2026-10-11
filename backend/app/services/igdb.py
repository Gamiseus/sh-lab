import httpx
import os
import logging
import re
from typing import Optional, Dict, Any
from sqlmodel import Session, select
from app.core.config import settings

logger = logging.getLogger(__name__)

IGDB_BASE_URL = "https://api.igdb.com/v4"
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"

class IGDBClient:
    def __init__(self, session: Session):
        self.session = session
        self.access_token = None
        self.client_id = settings.IGDB_CLIENT_ID
        self.client_secret = settings.IGDB_CLIENT_SECRET

        if not self.client_id and self.session:
            from app.models.config import SystemConfig
            cfg = self.session.get(SystemConfig, "igdb_client_id")
            if cfg and cfg.value:
                self.client_id = cfg.value
        if not self.client_secret and self.session:
            from app.models.config import SystemConfig
            cfg = self.session.get(SystemConfig, "igdb_client_secret")
            if cfg and cfg.value:
                self.client_secret = cfg.value

    async def _authenticate(self):
        if not self.client_id or not self.client_secret:
            logger.warning("IGDB credentials missing")
            return False
            
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(TWITCH_AUTH_URL, params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials"
                })
                response.raise_for_status()
                data = response.json()
                self.access_token = data["access_token"]
                return True
            except Exception as e:
                logger.info(f"IGDB Auth failed: {e}")
                return False

    async def search_game(self, query: str) -> Optional[Dict[str, Any]]:
        if not self.access_token:
            if not await self._authenticate():
                return None

        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # Search for game and get basic info + cover + popularity
        sanitized_query = query.replace('"', '').strip()
        body = f'search "{sanitized_query}"; fields name, summary, cover.url, rating, total_rating_count; limit 10;'
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{IGDB_BASE_URL}/games", headers=headers, data=body)
                response.raise_for_status()
                results = response.json()
                if results:
                    clean_query = sanitized_query.lower()
                    best = None
                    # Exact title match (case-insensitive)
                    for item in results:
                        if (item.get("name") or "").strip().lower() == clean_query:
                            best = item
                            break
                    if not best:
                        # Pick result with highest rating votes, or first item
                        best = max(results, key=lambda x: x.get("total_rating_count") or 0) if any(x.get("total_rating_count") for x in results) else results[0]

                    logger.info(f"IGDB Search: Found '{best.get('name')}' for query '{query}'")
                    data = best
                    # Upgrade cover image to high quality and full URL
                    if "cover" in data and isinstance(data["cover"], dict) and "url" in data["cover"]:
                        cover_url = data["cover"]["url"].replace("t_thumb", "t_cover_big_2x")
                        if cover_url.startswith("//"):
                            cover_url = "https:" + cover_url
                        data["cover"]["url"] = cover_url
                    return data
                logger.info(f"IGDB Search: No results for '{query}'")
                # Fallback: strip trailing parentheses like (2009), (US), (Game of the Year Edition), etc.
                clean_fallback = re.sub(r'\s*\([^)]*\)\s*$', '', query).strip()
                if clean_fallback and clean_fallback != query:
                    logger.info(f"IGDB Search: Retrying '{query}' as '{clean_fallback}'")
                    return await self.search_game(clean_fallback)
                return None
            except httpx.TimeoutException:
                logger.info(f"IGDB Search failed: Request timed out for '{query}'")
                return None
            except httpx.HTTPStatusError as e:
                # Handle 401 Unauthorized - Retry once
                if e.response.status_code == 401:
                    logger.info(f"IGDB Token Expired. Refreshing...")
                    if await self._authenticate():
                        # Update headers with new token
                        headers["Authorization"] = f"Bearer {self.access_token}"
                        try:
                            # Retry request
                            response = await client.post(f"{IGDB_BASE_URL}/games", headers=headers, data=body)
                            response.raise_for_status()
                            results = response.json()
                            if results:
                                logger.info(f"IGDB Search (Retry): Found '{results[0].get('name')}'")
                                data = results[0]
                                if "cover" in data and "url" in data["cover"]:
                                    data["cover"]["url"] = data["cover"]["url"].replace("t_thumb", "t_cover_big_2x")
                                return data
                        except Exception as retry_err:
                            logger.info(f"IGDB Retry failed: {retry_err}")
                
                logger.info(f"IGDB Search failed: HTTP {e.response.status_code} for '{query}'")
                return None
            except Exception as e:
                logger.info(f"IGDB Search failed: {type(e).__name__}: {e}")
                return None

    async def download_image(self, url: str, subfolder: str, game_title: str) -> Optional[str]:
        """
        Download image to app/metadata/{sanitized_game_title}/{filename}.
        Returns the relative URL path.
        """
        if not url:
            return None
            
        # Fix URL protocol
        if url.startswith("//"):
             url = "https:" + url
             
        # Sanitize Game Title for Folder Name
        import re
        safe_title = re.sub(r'[<>:"/\\|?*]', '', game_title).strip()
        if not safe_title:
            safe_title = "unknown_game"

        filename = url.split("/")[-1]
        
        # Structure: /data/metadata/{Game Name}/cover.jpg
        base_dir = f"/data/metadata/{safe_title}"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
            
        file_path = f"{base_dir}/{filename}"
        
        # Check cache
        if os.path.exists(file_path):
             return f"/metadata/{safe_title}/{filename}"
             
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(resp.content)
                    return f"/metadata/{safe_title}/{filename}"
            except Exception as e:
                logger.info(f"Failed to download image {url}: {e}")
                
        return None
