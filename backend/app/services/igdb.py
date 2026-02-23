import httpx
import os
from typing import Optional, Dict, Any
from sqlmodel import Session, select
from app.core.config import settings

IGDB_BASE_URL = "https://api.igdb.com/v4"
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"

class IGDBClient:
    def __init__(self, session: Session):
        self.session = session
        self.access_token = None
        self.client_id = settings.IGDB_CLIENT_ID
        self.client_secret = settings.IGDB_CLIENT_SECRET

    async def _authenticate(self):
        if not self.client_id or not self.client_secret:
            print("IGDB credentials missing")
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
                print(f"IGDB Auth failed: {e}")
                return False

    async def search_game(self, query: str) -> Optional[Dict[str, Any]]:
        if not self.access_token:
            if not await self._authenticate():
                return None

        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }
        
        # Search for game and get basic info + cover
        sanitized_query = query.replace('"', '')
        body = f'search "{sanitized_query}"; fields name, summary, cover.url, rating; limit 5;'
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(f"{IGDB_BASE_URL}/games", headers=headers, data=body)
                response.raise_for_status()
                results = response.json()
                if results:
                    print(f"IGDB Search: Found '{results[0].get('name')}' for query '{query}'")
                    data = results[0]
                    # Upgrade cover image to high quality
                    if "cover" in data and "url" in data["cover"]:
                        data["cover"]["url"] = data["cover"]["url"].replace("t_thumb", "t_cover_big_2x")
                    return data
                print(f"IGDB Search: No results for '{query}'")
                return None
            except httpx.TimeoutException:
                print(f"IGDB Search failed: Request timed out for '{query}'")
                return None
            except httpx.HTTPStatusError as e:
                # Handle 401 Unauthorized - Retry once
                if e.response.status_code == 401:
                    print(f"IGDB Token Expired. Refreshing...")
                    if await self._authenticate():
                        # Update headers with new token
                        headers["Authorization"] = f"Bearer {self.access_token}"
                        try:
                            # Retry request
                            response = await client.post(f"{IGDB_BASE_URL}/games", headers=headers, data=body)
                            response.raise_for_status()
                            results = response.json()
                            if results:
                                print(f"IGDB Search (Retry): Found '{results[0].get('name')}'")
                                data = results[0]
                                if "cover" in data and "url" in data["cover"]:
                                    data["cover"]["url"] = data["cover"]["url"].replace("t_thumb", "t_cover_big_2x")
                                return data
                        except Exception as retry_err:
                            print(f"IGDB Retry failed: {retry_err}")
                
                print(f"IGDB Search failed: HTTP {e.response.status_code} for '{query}'")
                return None
            except Exception as e:
                print(f"IGDB Search failed: {type(e).__name__}: {e}")
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
                print(f"Failed to download image {url}: {e}")
                
        return None
