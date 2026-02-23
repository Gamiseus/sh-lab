"""
Steam Store API service for fetching game metadata.
Uses the public store.steampowered.com/api/appdetails endpoint.
No API key required, rate limit: 200 requests per 5 minutes.
"""
import httpx
from typing import Optional, Dict, Any, List
import asyncio
import logging

logger = logging.getLogger(__name__)

STEAM_STORE_API = "https://store.steampowered.com/api/appdetails"
STEAM_SEARCH_API = "https://store.steampowered.com/api/storesearch"
RATE_LIMIT_DELAY = 1.5  # seconds between requests to be safe


class SteamStoreService:
    """Service for fetching game data from Steam Store API."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_app_details(self, app_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch full app details (legacy HTTP).
        Now used primarily for 'Enrichment' (slow / rich fetch).
        """
        # Call the HTTP batch logic (fallback)
        batch = await self._get_app_details_batch_http([app_id])
        return batch.get(app_id)

    async def get_app_details_batch(self, app_ids: List[int]) -> Dict[int, Optional[Dict[str, Any]]]:
        """
        Fetch details for multiple apps using PICS (Fast Lane).
        Uses the persistent Steam Client.
        """
        from app.services.steam_client import get_steam_client
        client_svc = get_steam_client()
        
        # PICS Fetch
        pics_data = await client_svc.get_product_info(app_ids)
        
        results = {}
        for app_id in app_ids:
            # PICS data structure from steamio usually:
            # { 'apps': { appid: { 'common': ..., 'extended': ... } } }
            # But get_product_info returns the 'apps' dict directly?
            # Or {appid: info}. Checking steam.py behavior...
            # steamio.Client.fetch_product_info returns dict mapped by appid.
            
            # JSON keys are strings
            app_info = pics_data.get(str(app_id)) or pics_data.get(app_id)
            
            if app_info:
                parsed = self.parse_pics_data(app_id, app_info)
                results[app_id] = parsed
            else:
                results[app_id] = None
                
        return results

    async def _get_app_details_batch_http(self, app_ids: List[int]) -> Dict[int, Optional[Dict[str, Any]]]:
        """
        Legacy HTTP Batch/Sequential Fetch (Slow).
        """
        if not app_ids:
            return {}
            
        results = {}
        # Adaptive rate limiting logic from before...
        delay = 1.4 
        
        for app_id in app_ids:
            try:
                url = f"{STEAM_STORE_API}?appids={app_id}&l=english&cc=US"
                response = await self.client.get(url)
                
                if response.status_code == 429:
                    logger.warning(f"Rate limit hit for App {app_id}. Cooling down for 60s...")
                    await asyncio.sleep(60)
                    delay = min(delay * 1.5, 5.0) 
                    response = await self.client.get(url)
                
                if response.status_code != 200:
                    results[app_id] = None
                    continue
                    
                data = response.json()
                app_data = data.get(str(app_id), {})
                
                if app_data.get("success"):
                    results[app_id] = app_data.get("data")
                else:
                    results[app_id] = None 
                
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error fetching {app_id}: {e}")
                results[app_id] = None
                
        return results

    def parse_pics_data(self, app_id: int, info: Dict) -> Dict[str, Any]:
        """
        Parse PICS (Protobuf) data into Game model format.
        PICS is sparse compared to Store API.
        """
        common = info.get("common", {})
        extended = info.get("extended", {})
        
        # Image URL construction
        # https://cdn.akamai.steamstatic.com/steamcommunity/public/images/apps/{appid}/{hash}.jpg
        icon_hash = common.get("icon")
        logo_hash = common.get("logo")
        
        header_image = None
        if logo_hash:
             header_image = f"https://cdn.akamai.steamstatic.com/steamcommunity/public/images/apps/{app_id}/{logo_hash}.jpg"
        
        # Fallback: Store Header URL is predictable!
        # https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg
        # This is strictly better than PICS logo.
        header_image = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg"
        capsule_image = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/capsule_616x353.jpg"

        genres = []
        # PICS genres are in common['associations']? Or 'genres'?
        # Usually associations: { '0': { 'type': 'genre', 'name': 'Action' } }
        assocs = common.get("associations", {})
        if isinstance(assocs, list): # sometimes list
             for a in assocs:
                 if a.get("type") == "genre":
                     genres.append(a.get("name"))
        elif isinstance(assocs, dict): # sometimes dict
             for k, v in assocs.items():
                 if v.get("type") == "genre":
                     genres.append(v.get("name"))

        return {
            "title": common.get("name", f"App {app_id}"),
            "steam_app_id": app_id,
            "description": "Metadata from PICS (Fast Load). Run enrichment for full details.",
            "short_description": None,
            "about_the_game": None, # PICS has no HTML description
            "header_image": header_image,
            "capsule_image": capsule_image,
            "developer": extended.get("developer"),
            "publisher": extended.get("publisher"),
            "genres": genres,
            "categories": None, # categories in PICS are technical usually
            "platforms": {
                "windows": common.get("oslist", "").find("windows") != -1,
                "mac": common.get("oslist", "").find("macos") != -1,
                "linux": common.get("oslist", "").find("linux") != -1
            },
            "release_date": None, # release state is code, not date string
            "source": "steam_pics"
        }

    
    async def search_games(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for games on Steam store.
        Returns list of matching apps with basic info.
        """
        try:
            response = await self.client.get(
                STEAM_SEARCH_API,
                params={"term": query, "l": "english", "cc": "US"}
            )
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])[:max_results]
            
            return [
                {
                    "app_id": item.get("id"),
                    "name": item.get("name"),
                    "tiny_image": item.get("tiny_image"),
                    "price": item.get("price", {})
                }
                for item in items
            ]
            
        except Exception as e:
            logger.error(f"Steam search error for '{query}': {e}")
            return []
    
    def parse_game_data(self, steam_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Steam API response into our Game model format.
        """
        if not steam_data:
            return {}
        
        # Extract genres as list of strings
        genres = [g.get("description") for g in steam_data.get("genres", [])]
        
        # Extract categories
        categories = steam_data.get("categories", [])
        
        # Extract screenshots
        screenshots = [
            {
                "thumbnail": s.get("path_thumbnail"),
                "full": s.get("path_full")
            }
            for s in steam_data.get("screenshots", [])
        ]
        
        # Extract movies/trailers
        movies = []
        for m in steam_data.get("movies", []):
            movie = {
                "id": m.get("id"),
                "name": m.get("name"),
                "thumbnail": m.get("thumbnail"),
                "highlight": m.get("highlight", False)
            }
            # Add streaming URLs (prefer hls for web playback)
            if m.get("hls_h264"):
                movie["hls"] = m.get("hls_h264")
            if m.get("dash_h264"):
                movie["dash"] = m.get("dash_h264")
            if m.get("webm"):
                webm_data = m.get("webm", {})
                movie["webm"] = webm_data.get("max") or webm_data.get("480")
            if m.get("mp4"):
                mp4_data = m.get("mp4", {})
                movie["mp4"] = mp4_data.get("max") or mp4_data.get("480")
            movies.append(movie)
        
        # Extract platforms
        platforms = steam_data.get("platforms", {})
        
        # Extract metacritic
        metacritic = steam_data.get("metacritic", {})
        
        # Extract achievements
        achievements = steam_data.get("achievements", {})
        achievements_highlighted = achievements.get("highlighted", [])
        
        # Extract price
        price_overview = steam_data.get("price_overview", {})
        
        # Extract recommendations (review count)
        recommendations = steam_data.get("recommendations", {})
        
        # Extract developers/publishers
        developers = steam_data.get("developers", [])
        publishers = steam_data.get("publishers", [])
        
        # Extract release date
        release_date = steam_data.get("release_date", {})
        
        # Extract requirements
        pc_req = steam_data.get("pc_requirements", {})
        mac_req = steam_data.get("mac_requirements", {})
        linux_req = steam_data.get("linux_requirements", {})
        
        return {
            "title": steam_data.get("name"),
            "steam_app_id": steam_data.get("steam_appid"),
            "description": steam_data.get("detailed_description"),
            "short_description": steam_data.get("short_description"),
            "about_the_game": steam_data.get("about_the_game"),
            "header_image": steam_data.get("header_image"),
            "capsule_image": steam_data.get("capsule_image") or steam_data.get("capsule_imagev5"),
            "background_url": steam_data.get("background"),
            "developer": developers[0] if developers else None,
            "publisher": publishers[0] if publishers else None,
            "genres": genres if genres else None,
            "categories": categories if categories else None,
            "screenshots": screenshots if screenshots else None,
            "movies": movies if movies else None,
            "platforms": platforms if platforms else None,
            "metacritic_score": metacritic.get("score"),
            "metacritic_url": metacritic.get("url"),
            "achievements_total": achievements.get("total"),
            "achievements_highlighted": achievements_highlighted if achievements_highlighted else None,
            "pc_requirements": pc_req.get("minimum") if isinstance(pc_req, dict) else None,
            "mac_requirements": mac_req.get("minimum") if isinstance(mac_req, dict) else None,
            "linux_requirements": linux_req.get("minimum") if isinstance(linux_req, dict) else None,
            "steam_review_count": recommendations.get("total"),
            "release_date": release_date.get("date"),
            "price_cents": price_overview.get("final"),
            "discount_percent": price_overview.get("discount_percent", 0),
            "source": "steam"
        }
    
    async def enrich_game(self, app_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse Steam data for a game.
        Returns parsed data ready to update Game model.
        """
        raw_data = await self.get_app_details(app_id)
        if not raw_data:
            return None
        
        await asyncio.sleep(RATE_LIMIT_DELAY)  # Rate limiting
        return self.parse_game_data(raw_data)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
_steam_service: Optional[SteamStoreService] = None

def get_steam_store_service() -> SteamStoreService:
    """Get or create Steam Store service instance."""
    global _steam_service
    if _steam_service is None:
        _steam_service = SteamStoreService()
    return _steam_service
