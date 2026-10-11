"""
Steam Store API service for fetching game metadata.
Uses the public store.steampowered.com/api/appdetails endpoint.
No API key required, rate limit: 200 requests per 5 minutes.
"""
import httpx
from typing import Optional, Dict, Any, List, Callable
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

    async def get_app_details_batch(
        self,
        app_ids: List[int],
        progress_callback: Optional[Callable[[int, int], Any]] = None
    ) -> Dict[int, Optional[Dict[str, Any]]]:
        """
        Fetch details for multiple apps using PICS (Fast Lane).
        Uses the persistent Steam Client.
        """
        from app.services.steam_client import get_steam_client
        client_svc = get_steam_client()
        
        # PICS Fetch
        pics_data = await client_svc.get_product_info(app_ids, progress_callback=progress_callback)
        
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
        PICS is sparse compared to Store API but contains critical
        type/free/category info needed for filtering.
        """
        common = info.get("common", {})
        extended = info.get("extended", {})
        
        # --- App type & filtering metadata ---
        # PICS common.type values: 'Game', 'DLC', 'Demo', 'Tool',
        #   'Application', 'Video', 'Music', 'Series', 'Config', 'Hardware'
        # Normalize to lowercase to match Steam Store API format
        pics_type = common.get("type", "")
        app_type = pics_type.lower() if pics_type else "unknown"
        
        # Free game detection: extended.isfreeapp = "1" for free games
        is_free_raw = extended.get("isfreeapp", "0")
        is_free = str(is_free_raw) == "1"
        
        # Release state: 'released', 'prerelease', 'preloadonly', etc.
        release_state = common.get("releasestate", "")
        
        # --- Steam categories (for online-only detection) ---
        # PICS stores categories as: common.category = { 'category_2': '1', 'category_36': '1', ... }
        # Category IDs: 2=Single-player, 1=Multi-player, 36=Online Multi-Player,
        #   38=Co-op, 9=Co-op (old), 49=PvP, 47=LAN PvP, etc.
        raw_categories = common.get("category", {})
        category_ids = set()
        if isinstance(raw_categories, dict):
            for key, val in raw_categories.items():
                # Keys look like "category_2", extract the number
                if key.startswith("category_") and str(val) == "1":
                    try:
                        category_ids.add(int(key.split("_")[1]))
                    except (ValueError, IndexError):
                        pass
        
        # --- Image URLs ---
        header_image = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg"
        capsule_image = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/capsule_616x353.jpg"

        # --- Genres ---
        genres = []
        assocs = common.get("associations", {})
        if isinstance(assocs, list):
             for a in assocs:
                 if a.get("type") == "genre":
                     genres.append(a.get("name"))
        elif isinstance(assocs, dict):
             for k, v in assocs.items():
                 if v.get("type") == "genre":
                     genres.append(v.get("name"))

        return {
            # Filtering fields (critical for import_single_game)
            "type": app_type,
            "is_free": is_free,
            "release_state": release_state,
            "steam_category_ids": sorted(category_ids),
            # Game metadata
            "name": common.get("name", f"App {app_id}"),
            "title": common.get("name", f"App {app_id}"),
            "steam_app_id": app_id,
            "description": "Metadata from PICS (Fast Load). Run enrichment for full details.",
            "short_description": None,
            "about_the_game": None,
            "header_image": header_image,
            "capsule_image": capsule_image,
            "developer": extended.get("developer"),
            "publisher": extended.get("publisher"),
            "genres": genres,
            "categories": None,
            "platforms": {
                "windows": "windows" in common.get("oslist", ""),
                "mac": "macos" in common.get("oslist", ""),
                "linux": "linux" in common.get("oslist", ""),
            },
            "release_date": None,
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
        
        parsed = self.parse_game_data(raw_data)

        # Authoritative review summary (store appdetails only exposes a raw count)
        reviews = await self.get_review_summary(app_id)
        if reviews:
            parsed.update(reviews)

        # Full achievement list with descriptions, hidden flags and global unlock %
        if raw_data.get("achievements", {}).get("total"):
            achievements = await self.get_achievements(app_id)
            if achievements:
                parsed["achievements"] = achievements
                parsed["achievements_total"] = len(achievements)

        await asyncio.sleep(RATE_LIMIT_DELAY)  # Rate limiting
        return parsed

    async def get_review_summary(self, app_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch Steam's own review summary (same numbers as the store page).
        Returns steam_review_count / steam_review_percent / steam_review_desc.
        """
        from datetime import datetime, timezone
        try:
            r = await self.client.get(
                f"https://store.steampowered.com/appreviews/{app_id}",
                params={"json": 1, "language": "all", "purchase_type": "all",
                        "filter": "all", "num_per_page": 0},
            )
            if r.status_code != 200:
                return None
            summary = r.json().get("query_summary") or {}
            total = summary.get("total_reviews") or 0
            positive = summary.get("total_positive") or 0
            if total <= 0:
                return {
                    "steam_review_count": 0,
                    "steam_review_percent": None,
                    "steam_review_desc": summary.get("review_score_desc") or "No user reviews",
                    "steam_reviews_updated_at": datetime.now(timezone.utc),
                }
            return {
                "steam_review_count": total,
                "steam_review_percent": round(positive * 100 / total),
                "steam_review_desc": summary.get("review_score_desc"),
                "steam_reviews_updated_at": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.warning(f"Steam review summary failed for {app_id}: {e}")
            return None

    async def get_achievements(self, app_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch the full achievement list (names, descriptions, icons, hidden flag,
        global unlock %) via IPlayerService/GetGameAchievements (no API key needed).
        """
        try:
            r = await self.client.get(
                "https://api.steampowered.com/IPlayerService/GetGameAchievements/v1/",
                params={"appid": app_id, "language": "english"},
            )
            if r.status_code != 200:
                return None
            items = (r.json().get("response") or {}).get("achievements") or []
            base = f"https://shared.fastly.steamstatic.com/community_assets/images/apps/{app_id}/"
            result = []
            for a in items:
                try:
                    pct = float(a.get("player_percent_unlocked") or 0)
                except (TypeError, ValueError):
                    pct = None
                result.append({
                    "api_name": a.get("internal_name"),
                    "name": a.get("localized_name") or a.get("internal_name"),
                    "description": a.get("localized_desc") or "",
                    "icon": base + a["icon"] if a.get("icon") else None,
                    "icon_gray": base + a["icon_gray"] if a.get("icon_gray") else None,
                    "hidden": bool(a.get("hidden")),
                    "percent": pct,
                })
            result.sort(key=lambda x: x["percent"] if x["percent"] is not None else -1, reverse=True)
            return result
        except Exception as e:
            logger.warning(f"Steam achievements fetch failed for {app_id}: {e}")
            return None
    
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
