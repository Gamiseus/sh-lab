import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
import httpx
from sqlmodel import Session, select, or_, func, col
from sqlalchemy import case
from app.core.db import get_session
from app.core.auth import get_current_user_optional
from app.models.game import Game, GameRead, GameCreate, GameUpdate
from app.models.user import User
from app.services.igdb import IGDBClient

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# Public Game Endpoints
# ============================================================

@router.get("/games", response_model=List[GameRead])
def list_catalog(
    offset: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    genres: List[str] = Query(None, alias="genre"),
    categories: List[str] = Query(None, alias="category"),
    source: Optional[str] = None,
    platform: Optional[str] = None,
    sort_by: str = "title",
    sort_order: str = "asc",
    session: Session = Depends(get_session)
):
    """
    List all known games in the catalog with optional filtering.
    
    Filters:
    - search: Fuzzy search on title and description
    - genre: Filter by genre (supports multiple, AND logic for specificity)
    - category: Filter by Steam category (supports multiple, AND logic)
    - source: Filter by source ("steam", "manual", "torrent")
    - platform: Filter by platform ("windows", "mac", "linux")
    
    Sort options: title, rating, metacritic_score, created_at, release_date, steam_review_count
    """
    query = select(Game)
    
    # Search filter (title or description)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Game.title.ilike(search_term),
                Game.description.ilike(search_term),
                Game.short_description.ilike(search_term)
            )
        )
    
    # Genre filter (AND logic - must match ALL selected genres)
    if genres:
        query = query.where(Game.genres.contains(genres))
    
    # Category filter (AND logic)
    if categories:
        for cat in categories:
            query = query.where(
                func.jsonb_path_exists(
                    Game.categories,
                    f'$[*] ? (@.description == "{cat}")'
                )
            )
    
    # Source filter
    if source:
        query = query.where(Game.source == source)
    
    # Platform filter
    if platform and platform in ["windows", "mac", "linux"]:
        query = query.where(
            func.jsonb_extract_path_text(Game.platforms, platform) == "true"
        )
    
    # Sorting
    sort_column = getattr(Game, sort_by, Game.title)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())
    
    query = query.offset(offset).limit(limit)
    games = session.exec(query).all()
    return games



@router.get("/featured", response_model=List[GameRead])
def get_featured_games(
    limit: int = 5,
    session: Session = Depends(get_session)
):
    """
    Get featured games for the hero carousel.
    Prioritizes games with videos/trailers and high ratings.
    """
    # First try games with videos
    query = select(Game).where(
        Game.movies.isnot(None),
        case(
            (func.jsonb_typeof(Game.movies) == 'array', func.jsonb_array_length(Game.movies)),
            else_=0
        ) > 0
    ).order_by(
        Game.metacritic_score.desc().nullslast()
    ).limit(limit)
    
    games = session.exec(query).all()
    
    # Fallback to any high-rated games
    if len(games) < limit:
        # Exclude already found games
        exclude_ids = [g.id for g in games]
        
        fallback = select(Game)
        if exclude_ids:
            fallback = fallback.where(Game.id.not_in(exclude_ids))
            
        fallback = fallback.order_by(
            Game.metacritic_score.desc().nullslast(),
            Game.created_at.desc()
        ).limit(limit - len(games))
        
        games.extend(session.exec(fallback).all())
    
    return games

@router.get("/games/{game_id}", response_model=GameRead)
def get_game(
    game_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get a single game by ID with full details including Steam data.
    """
    game = session.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

@router.get("/games/count")
def get_game_count(
    search: Optional[str] = None,
    genre: Optional[str] = None,
    source: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Get total count of games (for pagination).
    """
    query = select(func.count(Game.id))
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Game.title.ilike(search_term),
                Game.description.ilike(search_term)
            )
        )
    if genre:
        query = query.where(Game.genres.contains([genre]))
    if source:
        query = query.where(Game.source == source)
    
    count = session.exec(query).one()
    return {"count": count}

@router.get("/genres")
def list_genres(session: Session = Depends(get_session)):
    """
    Get list of all unique genres across all games.
    """
    games = session.exec(select(Game.genres)).all()
    all_genres = set()
    for genres in games:
        if genres:
            all_genres.update(genres)
    return sorted(list(all_genres))

@router.get("/categories")
def list_categories(session: Session = Depends(get_session)):
    """
    Get list of all unique Steam categories across all games.
    Categories include: Co-op, Multiplayer, Steam Workshop, etc.
    """
    games = session.exec(select(Game.categories)).all()
    all_categories = {}
    
    for categories in games:
        if categories:
            for cat in categories:
                cat_id = cat.get("id")
                cat_desc = cat.get("description")
                if cat_id and cat_desc:
                    all_categories[cat_id] = cat_desc
    
    return [{"id": k, "description": v} for k, v in sorted(all_categories.items(), key=lambda x: x[1])]

# ============================================================
# Discovery Endpoints
# ============================================================

@router.get("/recent", response_model=List[GameRead])
def get_recent_games(
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Get recently added games.
    """
    query = select(Game).order_by(Game.created_at.desc()).limit(limit)
    return session.exec(query).all()

@router.get("/popular", response_model=List[GameRead])
def get_popular_games(
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Get popular games based on Steam review count + local playtime.
    Priority: Steam data (70%) + local usage (30%)
    """
    # For now, sort by steam_review_count as proxy for popularity
    query = select(Game).where(
        Game.steam_review_count.isnot(None)
    ).order_by(
        Game.steam_review_count.desc()
    ).limit(limit)
    
    games = session.exec(query).all()
    
    # Fallback to rating if no steam data
    if len(games) < limit:
        fallback_query = select(Game).where(
            Game.steam_review_count.is_(None),
            Game.rating.isnot(None)
        ).order_by(Game.rating.desc()).limit(limit - len(games))
        
        games.extend(session.exec(fallback_query).all())
    
    return games

@router.get("/trending", response_model=List[GameRead])
def get_trending_games(
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Get trending games based on metacritic score + recency.
    Combines high Metacritic scores with recent additions.
    """
    # Games with high metacritic scores added recently
    query = select(Game).where(
        Game.metacritic_score.isnot(None)
    ).order_by(
        Game.metacritic_score.desc(),
        Game.created_at.desc()
    ).limit(limit)
    
    games = session.exec(query).all()
    
    # Fallback to recent if no metacritic data
    if len(games) < limit:
        fallback_query = select(Game).where(
            Game.metacritic_score.is_(None)
        ).order_by(Game.created_at.desc()).limit(limit - len(games))
        
        games.extend(session.exec(fallback_query).all())
    
    return games

@router.get("/top-rated", response_model=List[GameRead])
def get_top_rated_games(
    limit: int = 10,
    session: Session = Depends(get_session)
):
    """
    Get highest rated games by Metacritic score.
    """
    query = select(Game).where(
        Game.metacritic_score.isnot(None)
    ).order_by(
        Game.metacritic_score.desc()
    ).limit(limit)
    
    return session.exec(query).all()

# ============================================================
# Proxy Endpoints (Bypass CORS/Blocking)
# ============================================================

from fastapi import Response, Request
from starlette.background import BackgroundTask
import base64
from urllib.parse import urlparse

# Allowlist of domains the proxy is permitted to fetch from.
# Only trusted external CDNs/APIs should be listed here to prevent SSRF.
PROXY_ALLOWED_DOMAINS = {
    "cdn.akamai.steamstatic.com",
    "shared.akamai.steamstatic.com",
    "steamcdn-a.akamaihd.net",
    "cdn.cloudflare.steamstatic.com",
    "store.steampowered.com",
    "steamcommunity.com",
    "clan.akamai.steamstatic.com",
    "images.igdb.com",
    "media.steampowered.com",
    "video.akamai.steamstatic.com",
    "video.cloudflare.steamstatic.com",
}

def _validate_proxy_url(url: str) -> str:
    """Validate a URL against the allowed proxy domains. Raises HTTPException if not allowed."""
    if not url.startswith("https://") and not url.startswith("http://"):
        raise HTTPException(status_code=400, detail="Invalid URL: must start with http:// or https://")
    
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Invalid URL: no hostname")
    
    # Check against allowlist
    if hostname not in PROXY_ALLOWED_DOMAINS:
        raise HTTPException(
            status_code=403,
            detail=f"Domain '{hostname}' is not in the allowed proxy list"
        )
    
    return url

# Headers to strip from upstream responses to prevent browser issues
EXCLUDED_HEADERS = {
    "content-encoding", "content-length", "transfer-encoding", "connection", "keep-alive", "host",
    "access-control-allow-origin", "access-control-allow-methods", "access-control-allow-headers",
    "access-control-expose-headers", "access-control-max-age",
    "etag", "last-modified"
}

@router.get("/proxy/image")
async def proxy_image(url: str):
    """
    Proxy image requests (Buffered).
    Used for standard <img> tags (Posters) to avoid blocked direct loads.
    Fully buffers response to prevent connection stalls.
    """
    _validate_proxy_url(url)
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            r = await client.get(url, headers=headers)
        except Exception as e:
            # logger.info(f"Proxy Request Failed: {e}") # Debug only
            raise HTTPException(status_code=500, detail="Proxy Request Failed")

        if r.status_code != 200:
             raise HTTPException(status_code=r.status_code, detail="Upstream Image Not Found")

        # Forward safe headers
        response_headers = {
            k: v for k, v in r.headers.items() 
            if k.lower() not in EXCLUDED_HEADERS
        }

        return Response(
            content=r.content, 
            headers=response_headers,
            media_type=r.headers.get("content-type")
        )

@router.get("/proxy/image/base64")
async def proxy_image_base64(url: str):
    """
    Proxy image and return as Base64 JSON.
    Used for Screenshots and Thumbnails that are strictly blocked by browser networking.
    """
    _validate_proxy_url(url)
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            r = await client.get(url, headers=headers)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        if r.status_code != 200:
             raise HTTPException(status_code=r.status_code, detail="Upstream Image Not Found")

        try:
            b64 = base64.b64encode(r.content).decode("utf-8")
            media_type = r.headers.get("content-type", "image/jpeg")
            return {
                "mime": media_type,
                "data": b64
            }
        except Exception as e:
             raise HTTPException(status_code=500, detail="Encoding Error")

@router.get("/proxy/video")
async def proxy_video(url: str, request: Request):
    """
    Proxy video requests with Range support for streaming.
    Used for MP4/WebM playback that requires seeking and large file streaming.
    """
    _validate_proxy_url(url)
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Forward Range header (Critical for seeking)
    range_header = request.headers.get("range")
    if range_header:
        headers["Range"] = range_header

    client = httpx.AsyncClient(follow_redirects=True)
    try:
        req = client.build_request("GET", url, headers=headers)
        r = await client.send(req, stream=True)
    except Exception:
        await client.aclose()
        raise HTTPException(status_code=500, detail="Video Connection Failed")

    if r.status_code not in [200, 206]:
         await r.aclose()
         await client.aclose()
         raise HTTPException(status_code=r.status_code, detail="Remote Video Error")

    # Forward essential streaming headers
    response_headers = {}
    for k in ["content-range", "accept-ranges", "content-length", "content-type"]:
        val = r.headers.get(k)
        if val:
             response_headers[k] = val

    return StreamingResponse(
        r.aiter_bytes(), 
        status_code=r.status_code,
        headers=response_headers,
        media_type=r.headers.get("content-type"),
        background=BackgroundTask(client.aclose)
    )

# ============================================================
# Client-Side Matching
# ============================================================

@router.get("/match", response_model=Optional[GameRead])
async def match_game(
    folder_name: str = Query(..., description="Name of the folder found on client"),
    session: Session = Depends(get_session)
):
    """
    Attempt to match a client-side folder name to a known game in the DB.
    If no match found, attempts to fetch from IGDB and add to Catalog.
    """
    normalized_name = folder_name.strip()
    
    # Try exact match on Title
    existing_game = session.exec(select(Game).where(
        Game.title == normalized_name
    )).first()
    
    if existing_game:
        return existing_game

    # If not found, ask IGDB
    igdb = IGDBClient(session)
    logger.info(f"Store Match: Searching IGDB for '{normalized_name}'")
    
    result = await igdb.search_game(normalized_name)
    
    if result:
        new_game = Game(
            title=result.get("name", normalized_name),
            description=result.get("summary", ""),
            igdb_id=result.get("id"),
            summary=result.get("summary"),
            rating=result.get("rating")
        )
        
        session.add(new_game)
        session.commit()
        session.refresh(new_game)
        
        # Download Cover
        if "cover" in result and "url" in result["cover"]:
             cover_url = await igdb.download_image(
                 result["cover"]["url"], 
                 "covers",
                 new_game.title
             )
             if cover_url:
                 new_game.cover_url = cover_url
                 session.add(new_game)
                 session.commit()
                 session.refresh(new_game)
                 
        return new_game
        
    return None

@router.post("/metadata/batch", response_model=List[GameRead])
def get_games_metadata(
    game_ids: List[int],
    session: Session = Depends(get_session)
):
    """
    Get metadata for a list of Game IDs.
    Used by Frontend to populate the Library view after scanning local files.
    """
    if not game_ids:
        return []
        
    statement = select(Game).where(Game.id.in_(game_ids))
    games = session.exec(statement).all()
    return games
