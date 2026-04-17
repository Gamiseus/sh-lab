# 🚀 SH-LAB Project Roadmap

**Project:** Self-Hosted Game Library ("Shithead Lab")
**Vision:** Self-hosted Steam alternative with game downloads, library management, and community features.
**Last Updated:** 2026-04-16

---

## 📊 Executive Summary

| Category | Planned | Implemented | In Progress | Not Started | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Admin System** | 8 | 5 | 1 | 2 | 🟢 On Track |
| **2. News Tab** | 3 | 3 | 0 | 0 | 🟢 Complete |
| **3. Store/Games** | 18 | 8 | 1 | 9 | 🟡 Partial |
| **4. Library** | 12 | 7 | 1 | 4 | 🟡 Partial |
| **5. Community** | 8 | 3 | 0 | 5 | 🟡 Partial |
| **6. Servers** | 6 | 0 | 0 | 6 | 🔴 Backlog |
| **7. Requests** | 3 | 0 | 0 | 3 | 🔴 Backlog |
| **A. Backend Infra** | 5 | 3 | 0 | 2 | 🟡 Partial |
| **B. Frontend Infra** | 6 | 4 | 0 | 2 | 🟢 On Track |
| **C. Update System** | 8 | 0 | 0 | 8 | 🔴 Backlog |
| **TOTAL** | **77** | **33** | **3** | **41** | |

> **Overall Progress:** `[||||||||............] 43%`
> *Core systems (Auth, Store catalog, Library, Admin) are operational. Discovery and social features need work.*

---

## 🛠️ Detailed Feature Status

### 1. Admin System (Backend WebUI)
*Status: 70% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Admin Login System** | ✅ | JWT-based, `require_admin` dependency |
| **Default Credentials** | ✅ | Seeded (`admin`/`admin`) via setup endpoint |
| **Change Credentials** | ✅ | `change_password` endpoint in auth.py |
| **Settings UI** | ✅ | `SettingsPage.tsx` with backend-synced config |
| **User Mgmt Settings** | 🔄 | `create_user` endpoint exists, but no registration enable/disable toggle |
| **Data Management** | ✅ | Mass scan, background rescan, delete endpoints |
| **Admin Dashboard** | 🔄 | Admin routes exist (Games/Users/Settings) but no dashboard analytics/stats page |
| **Torrent Client Setup** | ❌ | Not started |

### 2. News Tab
*Status: 85% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Publishing System** | ✅ | Full CRUD: create, update, delete, publish/unpublish, pin, image upload |
| **Markdown Support** | ✅ | `ReactMarkdown` rendering in `NewsDetailsPage.tsx` |
| **Frontend Display** | ✅ | `NewsPage.tsx` (list) + `NewsDetailsPage.tsx` (detail) + tag filtering |

### 3. Store & Games Page
*Status: 50% Complete*

**Core Store Features**
| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Catalog Display** | ✅ | `StorePage.tsx` (14.6KB) with grid/list views |
| **IGDB Metadata** | ✅ | Full fetching via `igdb.py` + `metadata.py` |
| **Cover Images** | ✅ | IGDB download + local caching + proxy endpoints |
| **Install Button** | ✅ | Connected to Rust backend via Tauri commands |
| **Install Flow** | ✅ | `game_installer.rs` with `sh_meta.json` creation |
| **Game Details** | ✅ | `GameDetailsPage.tsx` (24KB) with full metadata display |

**Discovery Features**
| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Featured Carousel** | ✅ | `/featured` endpoint returns games with videos/high ratings |
| **Genre Browsing** | ✅ | `/genres` and `/categories` endpoints + frontend filters |
| **Popular/Trending** | ❌ | No endpoint exists |
| **New Releases** | ❌ | No endpoint exists |
| **Recommendations** | ❌ | No logic or endpoint exists |
| **Trailers** | ❌ | Video proxy exists (MP4/WebM streaming) but no yt-dlp or trailer downloading |
| **Fuzzy Search** | ❌ | Current search uses basic `ILIKE` wildcard, not `pg_trgm` trigram matching |

### 4. Library Page (Client-Side)
*Status: 65% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Display Installed** | ✅ | Scans for `sh_meta.json` via Rust scanner |
| **Cover Grid** | ✅ | Steam-like styling in `LibraryPage.tsx` |
| **Library Scanner** | ✅ | Rust-based scanner reads/writes `sh_meta.json`, matches via backend |
| **Catalog Match** | ✅ | `/store/match` endpoint matches folder names to DB games |
| **Configurable Paths** | ✅ | `library_path` config key in settings |
| **Uninstall Game** | ✅ | Rust command with `sh_meta.json` safety guard |
| **Game Info Panel** | ✅ | `GameDetailsPage` integration |
| **Playtime Tracking** | ✅ | `game_launcher.rs` session tracking + `playtime.py` API |
| **Launch Game** | 🔄 | `game_launcher.rs` (7.9KB) with executable detection and process monitoring |
| **Friends Activity** | ❌ | No activity feed endpoint in `friends.py` |
| **Recent Updates** | ❌ | No tracking system |

### 5. Community Tab
*Status: 40% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **User Profiles** | ✅ | Full `ProfilePage.tsx` (22KB) + `profiles.py` (19KB) |
| **Privacy System** | ✅ | `privacy_level` field on User model, enforced in community.py |
| **Profile Editing** | ✅ | Bio, avatar, display name update endpoints |
| **Favorite Games** | ❌ | No showcase or favorite games endpoint found |
| **Friends System** | 🔄 | `friends.py` has friend request send/accept/reject, but no activity feed |
| **Chat System** | ❌ | Not started |

### 6. Dedicated Servers
*Status: 5% (Models Only)*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Data Model** | 🔄 | `server.py` model with schemas (Create/Update/Read/Status) but no endpoints |
| **Folder Mgmt** | ❌ | - |
| **Launch Config** | ❌ | - |
| **Config Editor** | ❌ | - |
| **Player Counts** | ❌ | - |
| **Resource Monitor** | ❌ | - |

### 7. Requests System
*Status: 5% (Models Only)*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Data Model** | 🔄 | `request.py` model with schemas (Create/Update/Read/Admin) but no endpoints |
| **Request Search** | ❌ | - |
| **Queue Mgmt** | ❌ | - |
| **Admin Approval** | ❌ | - |

---

## 🏗️ Infrastructure

### A. Backend Services
| Service | Status | Tech |
| :--- | :---: | :--- |
| **Docker Compose** | ❌ | Lost during repo migration — needs recreation |
| **API Backend** | ✅ | Python FastAPI |
| **Database** | ✅ | PostgreSQL + SQLModel (`.env` with connection string lost — needs recreation) |
| **Admin UI** | ✅ | React/Vite (Admin Routes) |
| **Documentation** | 🔄 | FastAPI auto-generated Swagger at `/docs` — no custom docs |

### B. Frontend Infrastructure
| Component | Status | Tech |
| :--- | :---: | :--- |
| **Desktop App** | ✅ | Tauri v2 (Rust) |
| **UI Framework** | ✅ | React + TypeScript + CSS |
| **Offline Mode** | ❌ | Library requires backend connection — no offline cache/fallback |
| **Auth System** | ✅ | `AuthContext.tsx` with JWT token management |
| **Settings** | ✅ | Backend-synced config via settings endpoint |

### C. Update System (Future)
| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Self-Updater** | ❌ | `updater.exe` not started |
| **Version Check** | ❌ | - |
| **Delta Updates** | ❌ | - |

---

## 📅 Suggested Timeline

| Weeks | Phase | Focus | Status |
| :---: | :--- | :--- | :---: |
| **1** | 0-1 | Foundation & Database | ✅ Done |
| **2-3** | 2 | Auth & User System | ✅ Done |
| **4-5** | 3-4 | Game Mgmt & Install | ✅ Done |
| **6** | 5 | Launching & Playtime | ✅ Done |
| **7-8** | 6 | Store Enhancements | 🟡 Partial |
| **9** | 7 | Reviews | ✅ Done |
| **10-11** | 8 | Community & Profiles | 🟡 Partial |
| **12** | 9 | News System | ✅ Done |
| **13-14** | 10 | Dedicated Servers | 🔮 Future |
| **15-16** | 11 | Requests & Updates | 🔮 Future |

## 📋 Migration Notes

> [!WARNING]
> The following files were lost during the repo migration from the server PC and need to be recreated:
> - `docker-compose.yml` / `Dockerfile` — containerization setup
> - `.env` — API keys (IGDB, etc.) and database connection string
> - Any other deployment-specific configuration