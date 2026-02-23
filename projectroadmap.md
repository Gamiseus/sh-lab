# 🚀 SH-LAB Project Roadmap

**Project:** Self-Hosted Game Library ("Shithead Lab")
**Vision:** Self-hosted Steam alternative with game downloads, library management, and community features.
**Last Updated:** 2026-01-25

---

## 📊 Executive Summary

| Category | Planned | Implemented | In Progress | Not Started | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **1. Admin System** | 8 | 6 | 1 | 1 | 🟢 On Track |
| **2. News Tab** | 3 | 1 | 0 | 2 | 🟡 Pending |
| **3. Store/Games** | 18 | 14 | 1 | 3 | 🟢 Advanced |
| **4. Library** | 12 | 8 | 2 | 2 | 🟢 Advanced |
| **5. Community** | 8 | 4 | 0 | 4 | 🟡 Partial |
| **6. Servers** | 6 | 1 | 0 | 5 | 🔴 Backlog |
| **7. Requests** | 3 | 0 | 0 | 3 | 🔴 Backlog |
| **A. Backend Infra** | 5 | 5 | 0 | 0 | 🟢 Complete |
| **B. Frontend Infra** | 6 | 5 | 0 | 1 | 🟢 Complete |
| **C. Update System** | 8 | 0 | 0 | 8 | 🔴 Backlog |
| **TOTAL** | **77** | **44** | **4** | **29** | |

> **Overall Progress:** `[|||||||||||.........] 57%`
> *Major systems (Auth, Store, Library, Admin) are operational.*

---

## 🛠️ Detailed Feature Status

### 1. Admin System (Backend WebUI)
*Status: 85% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Admin Login System** | ✅ | Implemented (JWT) |
| **Default Credentials** | ✅ | Seeded (`admin`/`admin`) |
| **Change Credentials** | ✅ | Available |
| **Settings UI** | 🔄 | Basic dashboard implemented |
| **User Mgmt Settings** | ✅ | Registration toggles, role mgmt |
| **Data Management** | ✅ | Mass Scan/Delete implemented |
| **Admin Dashboard** | ✅ | Dashboard/Games/Users/Settings sections |
| **Torrent Client Setup** | ❌ | Not started |

### 2. News Tab
*Status: 33% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Publishing System** | ❌ | Backend model exists, logic pending |
| **Markdown Support** | ❌ | - |
| **Frontend Display** | ❌ | - |

### 3. Store & Games Page
*Status: 80% Complete*

**Core Store Features**
| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Catalog Display** | ✅ | `StorePage.tsx` active |
| **IGDB Metadata** | ✅ | Full fetching implemented |
| **Cover Images** | ✅ | Local caching system active |
| **Install Button** | ✅ | Connected to Rust backend |
| **Install Flow** | ✅ | `game_installer.rs` working |
| **Game Details** | ✅ | `GameDetailsPage.tsx` active |

**Discovery Features**
| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Popular/Trending** | ✅ | Backend endpoints active |
| **New Releases** | ✅ | Implemented |
| **Genre Browsing** | ✅ | Frontend filters active |
| **Recommendations** | ✅ | Based on user activity |
| **Trailers** | ✅ | Proxy endpoints (yt-dlp) active |
| **Fuzzy Search** | ✅ | `pg_trgm` search implemented |

### 4. Library Page (Client-Side)
*Status: 75% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Display Installed** | ✅ | Scans for `sh_meta.json` |
| **Cover Grid** | ✅ | Steam-like styling |
| **Library Scanner** | ✅ | Rust-based high perf scanner |
| **Catalog Match** | ✅ | `/store/match` endpoint active |
| **Configurable Paths** | ✅ | Multi-library support |
| **Uninstall Game** | ✅ | Rust command active |
| **Game Info Panel** | ✅ | `GameDetailsPage` integration |
| **Playtime Tracking** | ✅ | Session tracking active |
| **Friends Activity** | ✅ | Endpoint exists |
| **Recent Updates** | ❌ | No tracking system yet |

### 5. Community Tab
*Status: 50% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **User Profiles** | ✅ | Full Profile Page UI |
| **Privacy System** | ✅ | Visibility settings active |
| **Favorite Games** | ✅ | Showcase implemented |
| **Profile Editing** | ✅ | Bio, Avatar, Backgrounds |
| **Chat System** | ❌ | Not started |

### 6. Dedicated Servers
*Status: 15% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Folder Mgmt** | ❌ | Model only |
| **Launch Config** | ❌ | - |
| **Config Editor** | ❌ | - |
| **Player Counts** | ❌ | - |
| **Resource Monitor** | ❌ | - |

### 7. Requests System
*Status: 0% Complete*

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Request Search** | ❌ | Model only |
| **Queue Mgmt** | ❌ | - |
| **Admin Approval** | ❌ | - |

---

## 🏗️ Infrastructure

### A. Backend Services
| Service | Status | Tech |
| :--- | :---: | :--- |
| **Docker Compose** | ✅ | Postgres 16 + FastAPI |
| **API Backend** | ✅ | Python FastAPI |
| **Database** | ✅ | PostgreSQL + SQLModel |
| **Admin UI** | ✅ | React/Vite (Admin Routes) |
| **Documentation** | ✅ | OpenAPI / Swagger |

### B. Frontend Infrastructure
| Component | Status | Tech |
| :--- | :---: | :--- |
| **Desktop App** | ✅ | Tauri v2 (Rust) |
| **UI Framework** | ✅ | React + TypeScript + Tailwind |
| **Offline Mode** | ✅ | Local Metadata handling |
| **Auth System** | ✅ | Context + storage |
| **Settings** | ✅ | Backend synced config |

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
| **7-8** | 6 | Store Enhancements | ✅ Done |
| **9** | 7 | Reviews | ✅ Done |
| **10-11** | 8 | Community & Profiles | ✅ Done |
| **12** | 9 | News System | 🟡 Next |
| **13-14** | 10 | Dedicated Servers | 🔮 Future |
| **15-16** | 11 | Requests & Updates | 🔮 Future |

> **Timeline Estimate:** We are approximately at **Week 11** of the original 16-week schedule.