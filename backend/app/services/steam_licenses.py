"""
Steam License Import Service.
Extracts owned games from Steam account via SteamCMD licenses_print command.
"""
import asyncio
import re
import subprocess
import platform
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import httpx

from sqlmodel import Session, select
from app.models.game import Game
from app.models.config import SystemConfig
from app.services.steam_store import SteamStoreService


@dataclass
class LicenseInfo:
    """Represents a single Steam license/package."""
    package_id: int
    app_ids: List[int] = field(default_factory=list)
    license_type: str = ""
    flags: str = ""


@dataclass  
class ImportResult:
    """Result of a license import operation."""
    total_found: int = 0
    imported: int = 0
    skipped_existing: int = 0
    skipped_free: int = 0
    skipped_invalid: int = 0
    errors: List[Dict] = field(default_factory=list)
    games_added: List[str] = field(default_factory=list)


class SteamLicenseService:
    """Service to import owned games from Steam account."""
    
    def __init__(self):
        self.steam_store = SteamStoreService()
        self._import_status: Dict = {}  # Track ongoing imports
    
    async def run_steamcmd(
        self,
        steamcmd_path: str,
        username: str,
        password: str,
        min_commands: List[str],
        auth_code: Optional[str] = None
    ) -> Tuple[str, str, int]:
        """
        Run SteamCMD with given commands.
        steamcmd_path should be the DIRECTORY containing steamcmd.
        Returns: (stdout, stderr, return_code)
        """
        import os
        # Build command - steamcmd_path is directory containing the executable
        is_windows = platform.system() == "Windows"
        exe_name = "steamcmd.exe" if is_windows else "steamcmd.sh"
        executable = os.path.join(steamcmd_path, exe_name)
        
        login_args = ["+login", username, password]
        if auth_code:
            login_args.append(auth_code)
            
        cmd = [
            executable,
            *login_args,
            *min_commands,
            "+quit"
        ]
        
        # Run asynchronously
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return (
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
            process.returncode or 0
        )
    
    async def get_licenses_output(
        self,
        steamcmd_path: str,
        username: str,
        password: str,
        auth_code: Optional[str] = None
    ) -> str:
        """Run licenses_print and return raw output."""
        stdout, stderr, code = await self.run_steamcmd(
            steamcmd_path,
            username,
            password,
            ["+licenses_print"],
            auth_code
        )
        
        if code != 0:
            raise RuntimeError(f"SteamCMD failed with code {code}: {stderr}")
        
        return stdout
    
    def parse_licenses_output(self, output: str) -> List[LicenseInfo]:
        """
        Parse licenses_print output to extract package and app IDs.
        
        Example output format:
        License packageID 1234 - ...
         - appids: 5678,9012,3456  (or similar format)
        
        Returns list of LicenseInfo with package and app IDs.
        """
        licenses = []
        current_license = None
        
        for line in output.split("\n"):
            line = line.strip()
            
            # Look for license/package lines
            # Pattern: "License packageID XXXXX" or "packageID XXXXX"
            package_match = re.search(r"(?:License\s+)?packageID\s+(\d+)", line, re.IGNORECASE)
            if package_match:
                if current_license:
                    licenses.append(current_license)
                current_license = LicenseInfo(package_id=int(package_match.group(1)))
                continue
            
            # Look for appids line
            # Pattern: "appids : 123,456,789" or "Apps : 123, 456"
            appids_match = re.search(r"(?:appids?|apps)\s*:\s*([\d,\s]+)", line, re.IGNORECASE)
            if appids_match and current_license:
                app_ids_str = appids_match.group(1)
                app_ids = [
                    int(x.strip()) 
                    for x in re.split(r"[,\s]+", app_ids_str) 
                    if x.strip().isdigit()
                ]
                current_license.app_ids.extend(app_ids)
        
        # Don't forget the last license
        if current_license:
            licenses.append(current_license)
        
        return licenses
    
    def extract_unique_app_ids(self, licenses: List[LicenseInfo]) -> List[int]:
        """Extract unique app IDs from all licenses."""
        app_ids = set()
        for lic in licenses:
            app_ids.update(lic.app_ids)
        return sorted(app_ids)
    
    async def check_is_free_game(self, app_id: int) -> Optional[bool]:
        """
        Check if a game is free via Steam API.
        Returns: True if free, False if paid, None if error.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://store.steampowered.com/api/appdetails",
                    params={"appids": str(app_id)},
                    timeout=10.0
                )
                
                if resp.status_code != 200:
                    return None
                
                data = resp.json()
                app_data = data.get(str(app_id), {})
                
                if not app_data.get("success"):
                    return None
                
                game_info = app_data.get("data", {})
                
                # Check if it's a game (type == "game")
                if game_info.get("type") != "game":
                    return None  # Not a game, skip
                
                return game_info.get("is_free", False)
                
        except Exception:
            return None
    
    async def import_single_game(
        self,
        session: Session,
        app_id: int,
        preloaded_data: Optional[Dict] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Import a single game by app ID.
        Returns: (status, error_message)
        Status: "imported", "skipped_existing", "skipped_free", "skipped_invalid", "error"
        """
        # Check if already in database
        existing = session.exec(
            select(Game).where(Game.steam_app_id == app_id)
        ).first()
        
        if existing:
            return ("skipped_existing", None)
        
        # Fetch game details
        try:
            if preloaded_data:
                game_data = preloaded_data
            else:
                game_data = await self.steam_store.get_app_details(app_id)
            
            if not game_data:
                return ("skipped_invalid", "No data returned from Steam")
            
            # Check if it's a game
            if game_data.get("type") != "game":
                return ("skipped_invalid", f"Not a game (type: {game_data.get('type')})")
            
            # Check if free
            if game_data.get("is_free", False):
                return ("skipped_free", None)
            
            # Create game entry
            game = Game(
                title=game_data.get("name", f"App {app_id}"),
                steam_app_id=app_id,
                source="steam",
                short_description=game_data.get("short_description"),
                about_the_game=game_data.get("about_the_game"),
                description=game_data.get("detailed_description"),
                developer=", ".join(game_data.get("developers", [])),
                publisher=", ".join(game_data.get("publishers", [])),
                header_image=game_data.get("header_image"),
                capsule_image=game_data.get("capsule_image"),
                genres=[g.get("description") for g in game_data.get("genres", [])] if game_data.get("genres") else [],
                screenshots=game_data.get("screenshots"),
                movies=self._parse_movies(game_data.get("movies", [])),
                categories=game_data.get("categories"),
                platforms=game_data.get("platforms"),
                metacritic_score=game_data.get("metacritic", {}).get("score") if game_data.get("metacritic") else None,
                metacritic_url=game_data.get("metacritic", {}).get("url") if game_data.get("metacritic") else None,
                pc_requirements=self._stringify_requirements(game_data.get("pc_requirements")),
                mac_requirements=self._stringify_requirements(game_data.get("mac_requirements")),
                linux_requirements=self._stringify_requirements(game_data.get("linux_requirements")),
                achievements_total=game_data.get("achievements", {}).get("total") if game_data.get("achievements") else None,
                achievements_highlighted=game_data.get("achievements", {}).get("highlighted") if game_data.get("achievements") else None,
                release_date=game_data.get("release_date", {}).get("date"),
                price_cents=self._extract_price(game_data.get("price_overview")),
                discount_percent=game_data.get("price_overview", {}).get("discount_percent") if game_data.get("price_overview") else None,
            )
            
            session.add(game)
            session.commit()
            
            return ("imported", None)
            
        except Exception as e:
            return ("error", str(e))
    
    def _parse_movies(self, movies: List[Dict]) -> List[Dict]:
        """Parse movie data to extract streaming URLs."""
        result = []
        for movie in movies:
            parsed = {
                "id": movie.get("id"),
                "name": movie.get("name"),
                "thumbnail": movie.get("thumbnail"),
            }
            # Extract MP4 URLs
            if "mp4" in movie:
                parsed["mp4"] = movie["mp4"]
            if "webm" in movie:
                parsed["webm"] = movie["webm"]
            result.append(parsed)
        return result
    
    def _stringify_requirements(self, req: Optional[Dict]) -> Optional[str]:
        """Convert requirements dict to HTML string."""
        if not req:
            return None
        if isinstance(req, str):
            return req
        min_req = req.get("minimum", "")
        rec_req = req.get("recommended", "")
        if rec_req:
            return f"{min_req}<br><br>{rec_req}"
        return min_req
    
    def _extract_price(self, price_overview: Optional[Dict]) -> Optional[int]:
        """Extract price in cents from price_overview."""
        if not price_overview:
            return None
        # price_overview has "final" in cents
        return price_overview.get("final")

    async def import_all_licenses(
        self,
        session: Session,
        steamcmd_path: str,
        username: str,
        password: str,
        batch_size: int = 20,
        delay_seconds: float = 3.0,
        auth_code: Optional[str] = None
    ) -> ImportResult:
        """
        Full import pipeline:
        1. Run licenses_print
        2. Parse output
        3. Import each game with BATCH FETCHING.
        """
        result = ImportResult()
        
        # Update status
        self._import_status = {
            "running": True,
            "phase": "Getting licenses",
            "progress": 0,
            "total": 0,
            "started_at": datetime.utcnow().isoformat()
        }
        
        try:
            # Get licenses
            output = await self.get_licenses_output(steamcmd_path, username, password, auth_code)
            licenses = self.parse_licenses_output(output)
            all_app_ids = self.extract_unique_app_ids(licenses)
            
            result.total_found = len(all_app_ids)
            
            # Filter out existing games to save requests
            ids_to_process = []
            for app_id in all_app_ids:
                existing = session.exec(select(Game).where(Game.steam_app_id == app_id)).first()
                if existing:
                    result.skipped_existing += 1
                else:
                    ids_to_process.append(app_id)

            self._import_status["phase"] = "Importing games (Batching)"
            self._import_status["total"] = len(ids_to_process)
            
            # Process in batches
            for i in range(0, len(ids_to_process), batch_size):
                chunk = ids_to_process[i : i+batch_size]
                self._import_status["progress"] = i
                
                # Fetch Batch Metadata
                batch_data = await self.steam_store.get_app_details_batch(chunk)
                
                for app_id in chunk:
                    data = batch_data.get(app_id)
                    # Pass preloaded data to import_single_game
                    status, error = await self.import_single_game(session, app_id, preloaded_data=data)
                    
                    if status == "imported":
                        result.imported += 1
                        # Get game name for the result
                        game = session.exec(
                            select(Game).where(Game.steam_app_id == app_id)
                        ).first()
                        if game:
                            result.games_added.append(game.title)
                    elif status == "skipped_existing":
                        result.skipped_existing += 1
                    elif status == "skipped_free":
                        result.skipped_free += 1
                    elif status == "skipped_invalid":
                        result.skipped_invalid += 1
                    elif status == "error":
                        result.errors.append({"app_id": app_id, "error": error})
                
                # Rate limiting - delay after each batch
                await asyncio.sleep(delay_seconds)
            
            self._import_status["phase"] = "Complete"
            self._import_status["running"] = False
            
        except Exception as e:
            self._import_status["phase"] = "Error"
            self._import_status["error"] = str(e)
            self._import_status["running"] = False
            raise
        
        return result
    
    def get_import_status(self) -> Dict:
        """Get current import status."""
        return self._import_status.copy()


async def search_steam_store(query: str, limit: int = 20) -> List[Dict]:
    """
    Search Steam store for games.
    Uses the store search API.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://store.steampowered.com/api/storesearch/",
                params={
                    "term": query,
                    "l": "english",
                    "cc": "US"
                },
                timeout=10.0
            )
            
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            items = data.get("items", [])
            
            # Return simplified results
            results = []
            for item in items[:limit]:
                results.append({
                    "appid": item.get("id"),
                    "name": item.get("name"),
                    "icon": item.get("tiny_image"),
                    "price": item.get("price", {})
                })
            
            return results
            
    except Exception:
        return []
