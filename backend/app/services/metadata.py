import os
import shutil
import json
import logging
import re
from typing import Dict, Optional, Any, List
import httpx
from sqlmodel import Session, select
from datetime import datetime, timezone

from app.models.game import Game
from app.core.config import settings
from app.services.igdb import IGDBClient
from app.services.steam_store import SteamStoreService

logger = logging.getLogger(__name__)

class MetadataService:
    def __init__(self, session: Session):
        self.session = session
        self.igdb = IGDBClient(session)
        self.steam = SteamStoreService()
        self.metadata_base = os.path.join(settings.DATA_DIR, "metadata")
        
        if not os.path.exists(self.metadata_base):
            os.makedirs(self.metadata_base, exist_ok=True)

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use as directory/file name."""
        # Replace invalid chars with underscore
        clean = re.sub(r'[\\/*?:"<>|]', '_', name)
        # Remove usage of . or space at start/end
        clean = clean.strip(". ")
        return clean

    def _get_game_dir(self, title: str) -> str:
        """Get absolute path to game metadata directory."""
        folder_name = self._sanitize_filename(title)
        path = os.path.join(self.metadata_base, folder_name)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    def _get_public_url(self, title: str, filename: str) -> str:
        """Get public URL for a file in game metadata directory."""
        folder_name = self._sanitize_filename(title)
        # Note: /metadata is mounted to /data/metadata/
        return f"/metadata/{folder_name}/{filename}"

    async def download_image(self, url: str, title: str, filename: str) -> Optional[str]:
        """Download image and return public URL."""
        if not url:
            return None
            
        try:
            game_dir = self._get_game_dir(title)
            file_path = os.path.join(game_dir, filename)
            
            # Simple extension check/fix? 
            # If filename has no ext, try to guess from url?
            # For now assume filename includes ext or is generic like "cover.jpg"
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30.0)
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(resp.content)
                    return self._get_public_url(title, filename)
        except Exception as e:
            logger.error(f"Failed to download image {url} for {title}: {e}")
            return None
        return None

    async def enrich_game(self, game: Game, skip_steam: bool = False) -> Dict[str, Any]:
        """
        Enrich game metadata using priority: IGDB > Steam.
        Downloads assets to local storage.
        Updates Game object in DB.
        Returns the metadata dict applied.
        """
        updates: Dict[str, Any] = {}
        
        # 1. Fetch Steam Data
        steam_data = {}
        if game.steam_app_id and not skip_steam:
            try:
                steam_data = await self.steam.enrich_game(game.steam_app_id) or {}
                # Map Steam data to local schema
                # (SteamStoreService already maps vaguely to Game schema dict)
            except Exception as e:
                logger.error(f"Steam fetch failed for {game.title}: {e}")

        # 2. Fetch IGDB Data
        igdb_data = {}
        try:
            # Prefer searching by title? Or external ID if we had it?
            # We don't store IGDB ID on game unless previously verified.
            # If game.igdb_id is set, use it? IGDBClient supports search, not get by ID yet?
            # Check IGDBClient implementation
            # It has `search_game(query)`.
            search_res = await self.igdb.search_game(game.title)
            if search_res:
                igdb_data = search_res
        except Exception as e:
             logger.error(f"IGDB fetch failed for {game.title}: {e}")

        # 3. Merge Strategies
        # Priority: IGDB > Steam > Keep Existing
        # We build a composite dict
        
        # Helper to merge: if value in source is not None, use it.
        def merge(target_key: str, val: Any):
            if val is not None and val != "":
                updates[target_key] = val

        # Apply Steam first (Lower Priority)
        if steam_data:
            for k, v in steam_data.items():
                if hasattr(game, k):
                    merge(k, v)
        
        # Apply IGDB (Higher Priority)
        # IGDBClient.search_game returns simple dict: 
        # {id, name, summary, rating, cover: {url}, ...}
        if igdb_data:
            if "summary" in igdb_data:
                merge("description", igdb_data["summary"])
                merge("summary", igdb_data["summary"])
            if "rating" in igdb_data:
                merge("rating", igdb_data["rating"])
            if "id" in igdb_data:
                merge("igdb_id", igdb_data["id"])
            
            # Note: IGDB covers are handled separately via download

        # 4. Download Assets (Store Locally)
        # Cover
        cover_source = None
        if igdb_data.get("cover", {}).get("url"):
             cover_source = igdb_data["cover"]["url"]
        elif steam_data.get("header_image"):
             cover_source = steam_data.get("header_image")
        
        if cover_source:
             # IGDB URLs often start with //
             if cover_source.startswith("//"):
                 cover_source = "https:" + cover_source
             
             local_cover = await self.download_image(cover_source, game.title, "cover.jpg")
             if local_cover:
                 updates["cover_url"] = local_cover

        # Background / Screenshots
        # Steam provides screenshots. IGDB provides screenshots.
        # Prefer Steam for backgrounds (usually header_image or screenshots)
        bg_source = steam_data.get("background_url") or steam_data.get("header_image")
        if bg_source:
            local_bg = await self.download_image(bg_source, game.title, "background.jpg")
            if local_bg:
                updates["background_url"] = local_bg

        # 5. Apply Updates to Game Object
        for k, v in updates.items():
            if hasattr(game, k):
                setattr(game, k, v)
        
        game.updated_at = datetime.now(timezone.utc)
        self.session.add(game)
        self.session.commit()
        self.session.refresh(game)
        
        # Save JSON dump for debug
        try:
            game_dir = self._get_game_dir(game.title)
            with open(os.path.join(game_dir, "metadata.json"), "w") as f:
                # Convert Game to dict
                json.dump(game.model_dump(mode="json"), f, indent=2)
        except Exception:
            pass

        return updates
