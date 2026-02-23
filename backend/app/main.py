from fastapi import FastAPI
import os
from contextlib import asynccontextmanager
from app.api.v1.api import api_router
from app.core.db import init_db
from app.core.config import settings

from app.services.steam_client import get_steam_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    
    # Start persistent Steam Client (Background)
    steam_svc = get_steam_client()
    await steam_svc.start()
    
    yield
    
    # Shutdown
    await steam_svc.close()

app = FastAPI(
    title=settings.PROJECT_NAME, 
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:1420",
        "http://tauri.localhost",
        "https://tauri.localhost"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static media files (covers, backgrounds)
# Renamed from 'media' to 'metadata' as per Phase 6 architecture
for path in ["/data/metadata", "/data/profiles", "/data/server"]:
    if not os.path.exists(path):
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            pass

app.mount("/metadata", StaticFiles(directory="/data/metadata"), name="metadata")
app.mount("/profiles", StaticFiles(directory="/data/profiles"), name="profiles")
app.mount("/server", StaticFiles(directory="/data/server"), name="server")

# Admin Dashboard
if not os.path.exists("app/static"):
    os.makedirs("app/static")
app.mount("/dashboard", StaticFiles(directory="app/static", html=True), name="dashboard")

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": "Welcome to sh_lab Backend API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

