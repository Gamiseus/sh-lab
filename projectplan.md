# 📋 SH-LAB Detailed Implementation Plan

**Version:** 1.0
**Created:** 2026-01-22
**Total Phases:** 11

> [!NOTE]
> **Dependency Legend**
> * **[DEPENDS: X.Y]**: Requires task X.Y completion
> * **[BLOCKS: X.Y]**: Must be done before X.Y
> * **[ADMIN/API/DB/RUST/REACT]**: Component-specific tasks

---

## ✅ Completed & Verified Phases

<details>
<summary><b>Phase 0: Foundation Fixes (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **0.1.1** | [API] | Remove duplicate return None in store.py | ✅ |
| **0.1.2** | [RUST] | Cleanup unused imports | ✅ |
| **0.2.1** | [TEST] | Verify repo scan | ✅ |
| **0.2.2** | [TEST] | Verify library scan | ✅ |

</details>

<details>
<summary><b>Phase 1: Database Schema (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **1.1** | [DB] | Core Schema Updates (Genres, Tags, SteamID) | ✅ |
| **1.2** | [DB] | User System Schema (Users, Sessions) | ✅ |
| **1.3** | [DB] | Activity Schema (Playtime, Reviews) | ✅ |

</details>

<details>
<summary><b>Phase 2: Authentication (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **2.1** | [API] | Backend Auth Infrastructure | ✅ |
| **2.2** | [API] | Auth Endpoints (JWT) | ✅ |
| **2.3** | [ADMIN] | User Management Dashboard | ✅ |
| **2.4** | [REACT] | Frontend Auth Context | ✅ |

</details>

<details>
<summary><b>Phase 3: Game Management (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **3.1** | [ADMIN] | Game Management UI | ✅ |
| **3.2** | [ADMIN] | Repo Scanning | ✅ |
| **3.3** | [API] | IGDB Integration | ✅ |

</details>

<details>
<summary><b>Phase 4: Install System (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **4.1** | [RUST] | Basic Install Flow | ✅ |
| **4.2** | [RUST] | Download Queue | ✅ |
| **4.3** | [API] | HTTP Chunk Download | ✅ |

</details>

<details>
<summary><b>Phase 5: Launching & Playtime (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **5.1** | [RUST] | Game Launch System | ✅ |
| **5.2** | [RUST] | Playtime Tracking | ✅ |

</details>

<details>
<summary><b>Phase 6: Store Enhancements (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **6.1** | [API] | Search & Discovery | ✅ |
| **6.3** | [API] | Trailers (yt-dlp) | ✅ |
| **6.4** | [API] | Steam Integration | ✅ |

</details>

<details>
<summary><b>Phase 7: Reviews (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **7.1** | [API] | Review API | ✅ |
| **7.2** | [REACT] | Review UI | ✅ |

</details>

<details>
<summary><b>Phase 8: Community (Verified)</b></summary>

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **8.1** | [API] | User Profile API | ✅ |
| **8.2** | [REACT] | Profile UI | ✅ |
| **8.3** | [REACT] | Community Page | ✅ |

</details>

---

## 🚧 Active Development Phases

### PHASE 9: News System
**Priority:** LOW | **Est:** 4-6h | **Deps:** Phase 2

#### 9.1 News API
| Task | Type | Description | Depends |
| :--- | :---: | :--- | :--- |
| **9.1.1** | [API] | `GET /news` endpoint (public) | 1.4.1 |
| **9.1.2** | [API] | `POST /news` (admin publishing) | 9.1.1 |
| **9.1.3** | [API] | `PUT /news/{id}` (edit) | 9.1.1 |
| **9.1.4** | [API] | `DELETE /news/{id}` | 9.1.1 |

#### 9.2 News UI
| Task | Type | Description | Depends |
| :--- | :---: | :--- | :--- |
| **9.2.1** | [REACT] | `NewsPage.tsx` | 9.1.1 |
| **9.2.2** | [REACT] | News list cards | 9.2.1 |
| **9.2.3** | [REACT] | Markdown Renderer | 9.2.2 |

#### 9.3 Admin News Controls
| Task | Type | Description | Depends |
| :--- | :---: | :--- | :--- |
| **9.3.1** | [ADMIN] | Add "News" section | 9.1.* |
| **9.3.2** | [ADMIN] | Post Editor (Markdown) | 9.3.1 |

---

## 🔮 Future Phases

### PHASE 10: Dedicated Servers
**Priority:** LOW | **Est:** 10-14h | **Deps:** Phase 2

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **10.1** | [API] | Server Management API | ❌ |
| **10.2** | [REACT] | Servers Page UI | ❌ |
| **10.3** | [ADMIN] | Server Config Controls | ❌ |

### PHASE 11: Requests & Update System
**Priority:** LOW | **Est:** 12-16h | **Deps:** Phase 2, 4

| Task | Type | Description | Status |
| :--- | :---: | :--- | :---: |
| **11.1** | [API] | Game Requests API | ❌ |
| **11.2** | [ADMIN] | Request Approval/Queue | ❌ |
| **11.3** | [RUST] | Self-Updater (`updater.exe`) | ❌ |
| **11.4** | [API] | Delta Update System | ❌ |

---

### Phase 12: Tools Integration
**Priority:** FUTURE | **Est:** TBD

| Task | Type | Description |
| :--- | :---: | :--- |
| **12.1** | [RUST] | DRM Removal Integration |
| **12.2** | [RUST] | Online Fix Integration |
| **12.3** | [RUST] | DLC Unlocker Integration |

---

## 🏗️ Architecture & Flow

### Backend Structure
```
backend/
├── app/
│   ├── api/v1/endpoints/  # Routes
│   ├── models/            # SQLModel schemas
│   └── services/          # Logic (IGDB, Steam, Library)
```

### Frontend Structure
```
frontend/
├── src/
│   ├── pages/             # Route Views
│   ├── components/        # Reusable UI
│   └── stores/            # Zustand State
├── src-tauri/
│   └── src/               # Rust Backend (File Ops, Scanning)
```

### Critical Flow: Installation
1.  **User** clicks Install.
2.  **React** calls `prepare_install` (API).
3.  **React** invokes `install_game` (Rust).
4.  **Rust** downloads chunks from API.
5.  **Rust** writes to `sh_meta.json`.
6.  **Frontend** updates Library UI.