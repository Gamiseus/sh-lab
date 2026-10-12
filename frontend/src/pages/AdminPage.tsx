import { useState, useEffect, useCallback, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  HardDrive,
  Database,
  RefreshCw,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Users,
  Clock,
  Search,
  ShieldAlert,
  Layers,
  ArrowUpRight,
  Activity,
  X,
  Lock,
  Sparkles,
  Server,
  FolderArchive,
  SlidersHorizontal,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

// ============================================================================
// Types & Interfaces
// ============================================================================

export interface StorageStatus {
  total_bytes?: number;
  total_storage?: number;
  used_bytes?: number;
  used_storage?: number;
  free_bytes?: number;
  cached_games_count?: number;
  cached_count?: number;
  orphaned_games_count?: number;
  orphaned_count?: number;
  utilization_pct?: number;
  utilization_percent?: number;
}

export interface StorageGame {
  id?: number;
  game_id?: number;
  title: string;
  steam_app_id?: number | null;
  user_count?: number;
  cached_size_bytes?: number;
  size?: number;
  build_id?: string | null;
  latest_build_id?: string | null;
  last_check?: string | null;
  is_cached?: boolean;
  orphaned_at?: string | null;
  purged_at?: string | null;
  cached_at?: string | null;
  updated_at?: string | null;
  header_image?: string | null;
}

export interface StorageUpdateResult {
  status: string;
  message: string;
  game_id: number;
  task_id?: string | null;
}

export interface StoragePurgeResult {
  status: string;
  message: string;
  game_id: number;
  freed_bytes?: number;
  purged_at?: string | null;
}

type FilterTab = "all" | "cached" | "uncached" | "orphaned" | "updates";
type SortOption = "title" | "size_desc" | "users_desc" | "last_check_desc";

// ============================================================================
// Formatting Helpers
// ============================================================================

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === undefined || bytes === null || isNaN(bytes) || bytes <= 0) {
    return "0 B";
  }
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB", "PB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  if (i < 0) return "0 B";
  const unit = sizes[Math.min(i, sizes.length - 1)];
  const val = bytes / Math.pow(k, i);
  return `${val.toFixed(val >= 100 || i === 0 ? 0 : 1)} ${unit}`;
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "Never";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Unknown";
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "Unknown";
  }
}

// ============================================================================
// AdminPage Component
// ============================================================================

export function AdminPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  // Data state
  const [status, setStatus] = useState<StorageStatus | null>(null);
  const [games, setGames] = useState<StorageGame[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & search
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [sortBy, setSortBy] = useState<SortOption>("title");

  // Interaction feedback & modals
  const [actionMessage, setActionMessage] = useState<{
    type: "success" | "error" | "info";
    text: string;
  } | null>(null);
  const [updatingGameId, setUpdatingGameId] = useState<number | null>(null);
  const [purgeTarget, setPurgeTarget] = useState<StorageGame | null>(null);
  const [isPurging, setIsPurging] = useState<boolean>(false);

  // Fetch data from backend storage endpoints
  const fetchStorageData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [statusRes, gamesRes] = await Promise.all([
        api.get<StorageStatus>("/admin/storage/status"),
        api.get<StorageGame[]>("/admin/storage/games"),
      ]);
      setStatus(statusRes.data);
      setGames(Array.isArray(gamesRes.data) ? gamesRes.data : []);
    } catch (err: any) {
      console.error("Failed to load admin storage data:", err);
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to load server storage metrics";
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && isAuthenticated && user?.is_admin) {
      fetchStorageData();
    }
  }, [authLoading, isAuthenticated, user?.is_admin, fetchStorageData]);

  // Derived metrics
  const totalBytes = status?.total_bytes ?? status?.total_storage ?? 0;
  const usedBytes = status?.used_bytes ?? status?.used_storage ?? 0;
  const freeBytes = status?.free_bytes ?? Math.max(0, totalBytes - usedBytes);
  const cachedCount =
    status?.cached_games_count ??
    status?.cached_count ??
    games.filter((g) => (g.cached_size_bytes ?? g.size ?? 0) > 0 || g.is_cached).length;
  const orphanedCount =
    status?.orphaned_games_count ??
    status?.orphaned_count ??
    games.filter((g) => Boolean(g.orphaned_at)).length;

  const calculatedUtilization =
    totalBytes > 0
      ? (usedBytes / totalBytes) * 100
      : (status?.utilization_pct ?? status?.utilization_percent ?? 0);
  const utilizationPct = Math.min(100, Math.max(0, calculatedUtilization));

  // Action: Force SteamCMD Update / Re-validation
  const handleForceUpdate = async (game: StorageGame) => {
    const id = game.game_id ?? game.id;
    if (!id) return;
    setUpdatingGameId(id);
    setActionMessage(null);
    try {
      const res = await api.post<StorageUpdateResult>(`/admin/storage/${id}/update`);
      const taskId = res.data?.task_id;
      setActionMessage({
        type: "success",
        text: `Update triggered for "${game.title}". SteamCMD validation queued${
          taskId ? ` (Task: ${taskId})` : ""
        }.`,
      });
      await fetchStorageData();
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail || err?.message || "Failed to trigger depot update";
      setActionMessage({
        type: "error",
        text: `Failed to update "${game.title}": ${detail}`,
      });
    } finally {
      setUpdatingGameId(null);
    }
  };

  // Action: Purge Cached Depot Files
  const handlePurgeGame = async () => {
    if (!purgeTarget) return;
    const id = purgeTarget.game_id ?? purgeTarget.id;
    if (!id) return;
    setIsPurging(true);
    setActionMessage(null);
    try {
      const res = await api.post<StoragePurgeResult>(`/admin/storage/${id}/purge`);
      const freed =
        res.data?.freed_bytes !== undefined && res.data?.freed_bytes !== null
          ? formatBytes(res.data.freed_bytes)
          : formatBytes(purgeTarget.cached_size_bytes ?? purgeTarget.size);
      setActionMessage({
        type: "success",
        text: `Purge completed: Freed ${freed} for "${purgeTarget.title}". Server cache state reset.`,
      });
      setPurgeTarget(null);
      await fetchStorageData();
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail || err?.message || "Failed to purge depot cache";
      setActionMessage({
        type: "error",
        text: `Failed to purge "${purgeTarget.title}": ${detail}`,
      });
    } finally {
      setIsPurging(false);
    }
  };

  // Filtered & sorted game list
  const filteredGames = useMemo(() => {
    return games
      .filter((game) => {
        const titleMatch = game.title.toLowerCase().includes(searchQuery.toLowerCase());
        const appIdMatch = game.steam_app_id
          ? String(game.steam_app_id).includes(searchQuery)
          : false;
        const buildIdMatch = game.build_id
          ? game.build_id.toLowerCase().includes(searchQuery.toLowerCase())
          : false;
        if (!titleMatch && !appIdMatch && !buildIdMatch) return false;

        const isCached =
          game.is_cached ?? ((game.cached_size_bytes ?? game.size ?? 0) > 0);
        const isOrphaned = Boolean(game.orphaned_at);
        const hasUpdate = Boolean(
          game.latest_build_id &&
            game.build_id &&
            game.latest_build_id !== game.build_id
        );

        switch (activeTab) {
          case "cached":
            return isCached;
          case "uncached":
            return !isCached;
          case "orphaned":
            return isOrphaned;
          case "updates":
            return hasUpdate;
          case "all":
          default:
            return true;
        }
      })
      .sort((a, b) => {
        switch (sortBy) {
          case "size_desc": {
            const sizeA = a.cached_size_bytes ?? a.size ?? 0;
            const sizeB = b.cached_size_bytes ?? b.size ?? 0;
            return sizeB - sizeA;
          }
          case "users_desc": {
            const usersA = a.user_count ?? 0;
            const usersB = b.user_count ?? 0;
            return usersB - usersA;
          }
          case "last_check_desc": {
            const timeA = a.last_check ? new Date(a.last_check).getTime() : 0;
            const timeB = b.last_check ? new Date(b.last_check).getTime() : 0;
            return timeB - timeA;
          }
          case "title":
          default:
            return a.title.localeCompare(b.title);
        }
      });
  }, [games, searchQuery, activeTab, sortBy]);

  // Tab counts
  const tabCounts = useMemo(() => {
    let cached = 0;
    let uncached = 0;
    let orphaned = 0;
    let updates = 0;
    games.forEach((g) => {
      const isCached = g.is_cached ?? ((g.cached_size_bytes ?? g.size ?? 0) > 0);
      if (isCached) cached++;
      else uncached++;
      if (g.orphaned_at) orphaned++;
      if (g.latest_build_id && g.build_id && g.latest_build_id !== g.build_id) updates++;
    });
    return { all: games.length, cached, uncached, orphaned, updates };
  }, [games]);

  // Handle Unauthorized / Non-Admin Access
  if (!authLoading && (!isAuthenticated || !user?.is_admin)) {
    return (
      <div className="p-8 max-w-4xl mx-auto flex flex-col items-center justify-center min-h-[60vh] text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400">
          <Lock className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Administrator Access Required
          </h1>
          <p className="text-zinc-400 max-w-md mx-auto text-sm leading-relaxed">
            The Dedicated Web Admin View (/admin) is restricted to users with administrative
            privileges. Your current session does not have permission to inspect or manage
            server storage caches.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/store")}
            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-violet-600/20"
          >
            Return to Store
          </button>
          <button
            onClick={() => navigate("/login")}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium transition-colors"
          >
            Switch Account
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* ==================================================================== */}
      {/* Page Header */}
      {/* ==================================================================== */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              <Server className="w-8 h-8 text-violet-400" />
              Dedicated Web Admin View
            </h1>
            <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-violet-500/10 border border-violet-500/30 text-violet-300 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5" />
              Admin Portal
            </span>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Comprehensive server storage monitoring, SteamCMD depot cache management, and 7-day
            orphan retention controls.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchStorageData}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-200 rounded-xl text-sm font-medium transition-colors border border-white/10 disabled:opacity-50"
            title="Refresh server storage metrics"
          >
            <RefreshCw className={`w-4 h-4 text-violet-400 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <Link
            to="/settings"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 rounded-xl text-sm font-medium transition-colors border border-white/10"
          >
            <span>Settings Panel</span>
            <ArrowUpRight className="w-4 h-4 text-zinc-400" />
          </Link>
          <Link
            to="/downloads"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-medium transition-colors shadow-lg shadow-violet-600/20"
          >
            <Activity className="w-4 h-4" />
            <span>Downloads Queue</span>
          </Link>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* Action Feedback Banner */}
      {/* ==================================================================== */}
      {actionMessage && (
        <div
          className={`flex items-center justify-between gap-3 p-4 rounded-xl border text-sm animate-in fade-in duration-200 ${
            actionMessage.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : actionMessage.type === "error"
              ? "bg-red-500/10 border-red-500/30 text-red-300"
              : "bg-blue-500/10 border-blue-500/30 text-blue-300"
          }`}
        >
          <div className="flex items-center gap-3">
            {actionMessage.type === "success" ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-400" />
            ) : actionMessage.type === "error" ? (
              <AlertTriangle className="w-5 h-5 flex-shrink-0 text-red-400" />
            ) : (
              <Activity className="w-5 h-5 flex-shrink-0 text-blue-400" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-zinc-400 hover:text-white p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Global Error Banner */}
      {error && (
        <div className="flex items-center justify-between p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchStorageData}
            className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-200 rounded-lg text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      )}

      {/* ==================================================================== */}
      {/* Metrics Overview Cards */}
      {/* ==================================================================== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Server Capacity */}
        <div className="p-5 rounded-2xl bg-zinc-900/60 border border-white/10 shadow-lg space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Total Storage Capacity
            </span>
            <div className="p-2 rounded-xl bg-violet-600/10 text-violet-400 border border-violet-500/20">
              <HardDrive className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-white tracking-tight">
              {formatBytes(totalBytes)}
            </div>
            <p className="text-xs text-zinc-400 mt-1 flex items-center gap-1">
              <span>{formatBytes(freeBytes)} unallocated space</span>
            </p>
          </div>
        </div>

        {/* Cached Depot Footprint */}
        <div className="p-5 rounded-2xl bg-zinc-900/60 border border-white/10 shadow-lg space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Cached Disk Footprint
            </span>
            <div className="p-2 rounded-xl bg-blue-600/10 text-blue-400 border border-blue-500/20">
              <Database className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-white tracking-tight">
              {formatBytes(usedBytes)}
            </div>
            <p className="text-xs text-zinc-400 mt-1 flex items-center gap-1.5">
              <span
                className={`font-semibold ${
                  utilizationPct > 85
                    ? "text-red-400"
                    : utilizationPct > 70
                    ? "text-amber-400"
                    : "text-emerald-400"
                }`}
              >
                {utilizationPct.toFixed(1)}% utilized
              </span>
              <span>of repository drive</span>
            </p>
          </div>
        </div>

        {/* Cached Game Titles */}
        <div className="p-5 rounded-2xl bg-zinc-900/60 border border-white/10 shadow-lg space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Cached Depot Titles
            </span>
            <div className="p-2 rounded-xl bg-emerald-600/10 text-emerald-400 border border-emerald-500/20">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-white tracking-tight">
              {cachedCount}{" "}
              <span className="text-sm font-normal text-zinc-400">titles</span>
            </div>
            <p className="text-xs text-emerald-400/90 mt-1 flex items-center gap-1">
              <span>Ready for HTTP chunk streaming</span>
            </p>
          </div>
        </div>

        {/* Orphaned Titles */}
        <div className="p-5 rounded-2xl bg-zinc-900/60 border border-white/10 shadow-lg space-y-3 relative overflow-hidden group">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Orphaned Titles (7-Day)
            </span>
            <div className="p-2 rounded-xl bg-amber-600/10 text-amber-400 border border-amber-500/20">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div>
            <div className="text-2xl font-black text-white tracking-tight">
              {orphanedCount}{" "}
              <span className="text-sm font-normal text-zinc-400">unreferenced</span>
            </div>
            <p className="text-xs text-amber-400/90 mt-1 flex items-center gap-1">
              <span>Retention timer active (0 users)</span>
            </p>
          </div>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* Storage Allocation Bar */}
      {/* ==================================================================== */}
      <div className="p-6 rounded-2xl bg-zinc-900/60 border border-white/10 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-violet-400" />
              Server Disk Allocation & Cache Utilization
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Live storage usage for depot repositories at /data/repo.
            </p>
          </div>
          <div className="text-xs font-mono text-zinc-300">
            {formatBytes(usedBytes)} / {formatBytes(totalBytes)} ({utilizationPct.toFixed(1)}%)
          </div>
        </div>

        {/* Multi-layer Progress bar */}
        <div className="w-full bg-zinc-950 rounded-full h-3 p-0.5 border border-white/5 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              utilizationPct > 85
                ? "bg-gradient-to-r from-red-600 to-rose-500"
                : utilizationPct > 70
                ? "bg-gradient-to-r from-amber-500 to-orange-500"
                : "bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-500"
            }`}
            style={{ width: `${Math.max(1, utilizationPct)}%` }}
          />
        </div>

        <div className="flex flex-wrap items-center gap-6 pt-1 text-xs text-zinc-400">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-violet-500" />
            <span>Cached Games: {formatBytes(usedBytes)}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
            <span>Free Disk Space: {formatBytes(freeBytes)}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span>Orphan Cleanup Policy: 7-Day Inactivity Retention</span>
          </div>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* Tracked Catalog & Cache Governance Table */}
      {/* ==================================================================== */}
      <div className="space-y-4 bg-zinc-900/60 p-6 rounded-2xl border border-white/10 shadow-lg">
        {/* Controls Bar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <FolderArchive className="w-5 h-5 text-violet-400" />
              Catalog of Tracked Games & Depot Cache
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Track user associations, cache states, SteamCMD build versions, and trigger maintenance.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search title, App ID, build..."
                className="w-full sm:w-64 pl-9 pr-3 py-2 bg-zinc-950/80 border border-white/10 rounded-xl text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500 transition-colors"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Sort Selector */}
            <div className="flex items-center gap-1.5 bg-zinc-950/80 px-3 py-1.5 rounded-xl border border-white/10 text-xs">
              <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-400" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="bg-transparent text-zinc-300 focus:outline-none cursor-pointer pr-1"
              >
                <option value="title" className="bg-zinc-900 text-white">Title (A-Z)</option>
                <option value="size_desc" className="bg-zinc-900 text-white">Cached Size</option>
                <option value="users_desc" className="bg-zinc-900 text-white">User Count</option>
                <option value="last_check_desc" className="bg-zinc-900 text-white">Last Check</option>
              </select>
            </div>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex flex-wrap items-center gap-2 border-b border-white/5 pb-3">
          {(
            [
              { id: "all", label: "All Games", count: tabCounts.all },
              { id: "cached", label: "Cached Only", count: tabCounts.cached },
              { id: "uncached", label: "Uncached", count: tabCounts.uncached },
              { id: "orphaned", label: "Orphaned", count: tabCounts.orphaned },
              { id: "updates", label: "Updates Available", count: tabCounts.updates },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? "bg-violet-600/20 text-violet-300 border border-violet-500/40 shadow-sm"
                  : "text-zinc-400 hover:text-white hover:bg-white/5 border border-transparent"
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                  activeTab === tab.id
                    ? "bg-violet-500 text-white"
                    : "bg-zinc-800 text-zinc-400"
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Data Table */}
        <div className="overflow-x-auto rounded-xl border border-white/5">
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-950/70 text-zinc-400 uppercase tracking-wider text-[11px] border-b border-white/5">
              <tr>
                <th className="py-3 px-4">Game & App ID</th>
                <th className="py-3 px-4">Depot Status</th>
                <th className="py-3 px-4">Cached Size</th>
                <th className="py-3 px-4">Tracked Users</th>
                <th className="py-3 px-4">Build ID</th>
                <th className="py-3 px-4">Last Check</th>
                <th className="py-3 px-4 text-right">Maintenance Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {isLoading && games.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-zinc-400">
                    <div className="flex flex-col items-center gap-3">
                      <RefreshCw className="w-6 h-6 animate-spin text-violet-400" />
                      <span>Loading tracked game catalog and storage status...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredGames.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-zinc-400">
                    <div className="flex flex-col items-center gap-2">
                      <Search className="w-6 h-6 text-zinc-600" />
                      <p className="font-semibold text-zinc-300">No games match current filter.</p>
                      <p className="text-zinc-500 text-xs">Try clearing your search query or switching tabs.</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredGames.map((game) => {
                  const gameId = game.game_id ?? game.id ?? 0;
                  const sizeBytes = game.cached_size_bytes ?? game.size ?? 0;
                  const isCached = game.is_cached ?? (sizeBytes > 0);
                  const isOrphaned = Boolean(game.orphaned_at);
                  const hasUpdate = Boolean(
                    game.latest_build_id &&
                      game.build_id &&
                      game.latest_build_id !== game.build_id
                  );
                  const isUpdating = updatingGameId === gameId;

                  return (
                    <tr
                      key={gameId}
                      className="hover:bg-zinc-950/40 transition-colors group"
                    >
                      {/* Title & App ID */}
                      <td className="py-3.5 px-4 font-medium text-white">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-white/10 flex items-center justify-center flex-shrink-0 text-zinc-400 group-hover:border-violet-500/30 transition-colors">
                            <FolderArchive className="w-4 h-4 text-violet-400" />
                          </div>
                          <div className="min-w-0">
                            <Link
                              to={`/games/${gameId}`}
                              className="font-semibold text-zinc-200 hover:text-violet-300 transition-colors truncate block"
                            >
                              {game.title}
                            </Link>
                            <div className="text-[11px] text-zinc-500 font-mono flex items-center gap-1.5">
                              {game.steam_app_id ? (
                                <span>App ID: {game.steam_app_id}</span>
                              ) : (
                                <span>Custom Title</span>
                              )}
                              <span>•</span>
                              <span>ID: #{gameId}</span>
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Status Badges */}
                      <td className="py-3.5 px-4">
                        <div className="flex flex-col gap-1 items-start">
                          {isCached ? (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                              Cached on Server
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-zinc-800 text-zinc-400 border border-white/5">
                              Not Cached
                            </span>
                          )}

                          {isOrphaned && (
                            <span
                              className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-center gap-1"
                              title={`Orphaned since ${formatDate(game.orphaned_at)}. Auto-purge after 7 days.`}
                            >
                              <Clock className="w-3 h-3" />
                              Orphaned (7-Day Timer)
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Cached Size */}
                      <td className="py-3.5 px-4 font-mono text-zinc-300">
                        {isCached ? (
                          <span className="font-semibold text-white">{formatBytes(sizeBytes)}</span>
                        ) : (
                          <span className="text-zinc-500">0 B</span>
                        )}
                      </td>

                      {/* Tracked Users */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-1.5 text-zinc-300">
                          <Users className="w-3.5 h-3.5 text-zinc-500" />
                          <span className="font-semibold">{game.user_count ?? 0}</span>
                          <span className="text-zinc-500">users</span>
                        </div>
                      </td>

                      {/* Build ID & Update Notice */}
                      <td className="py-3.5 px-4 font-mono text-xs">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-zinc-200">
                            {game.build_id ? `v${game.build_id}` : "Unknown"}
                          </span>
                          {hasUpdate && (
                            <span className="text-[10px] text-amber-400 font-semibold flex items-center gap-1">
                              <Sparkles className="w-3 h-3" />
                              New: v{game.latest_build_id}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Last Check */}
                      <td className="py-3.5 px-4 text-zinc-400 text-xs">
                        {formatDate(game.last_check)}
                      </td>

                      {/* Maintenance Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {/* Force Update Button */}
                          <button
                            onClick={() => handleForceUpdate(game)}
                            disabled={isUpdating}
                            className="px-2.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-violet-600/20 hover:border-violet-500/40 text-zinc-300 hover:text-violet-300 border border-white/5 transition-all text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                            title="Force SteamCMD depot update and re-validation"
                          >
                            <RefreshCw
                              className={`w-3.5 h-3.5 text-violet-400 ${
                                isUpdating ? "animate-spin" : ""
                              }`}
                            />
                            <span>{isUpdating ? "Updating..." : "Force Update"}</span>
                          </button>

                          {/* Purge Cache Button */}
                          <button
                            onClick={() => setPurgeTarget(game)}
                            disabled={!isCached || isPurging}
                            className="px-2.5 py-1.5 rounded-lg bg-zinc-800 hover:bg-red-500/20 hover:border-red-500/40 text-zinc-400 hover:text-red-300 border border-white/5 transition-all text-xs font-semibold flex items-center gap-1.5 disabled:opacity-30 disabled:cursor-not-allowed"
                            title={
                              isCached
                                ? "Purge cached depot files on demand"
                                : "Title has no cached files to purge"
                            }
                          >
                            <Trash2 className="w-3.5 h-3.5 text-red-400" />
                            <span>Purge</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* Information & Policy Card */}
      {/* ==================================================================== */}
      <div className="p-6 rounded-2xl bg-zinc-950/60 border border-white/5 space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
          <Activity className="w-4 h-4 text-violet-400" />
          Server Depot Cache Governance & Retention Policy
        </h3>
        <p className="text-xs text-zinc-400 leading-relaxed">
          Steam Headless Lab automatically caches game depot payloads downloaded via SteamCMD
          into the server repository (<code className="text-zinc-300">/data/repo/&lt;title&gt;</code>).
          When client users remove a game from their library such that zero active users reference
          it, the server arms a <strong>7-Day Retention Countdown</strong> (604,800 seconds). If no
          user re-adds the game before the retention window expires, the automated background
          worker safely purges depot files to reclaim disk space.
        </p>
        <p className="text-xs text-zinc-400 leading-relaxed">
          The <strong>Purge</strong> control above permits administrators to immediately override
          the retention period and reclaim server storage on demand. The <strong>Force Update</strong> control
          triggers SteamCMD re-validation (<code className="text-zinc-300">+app_update validate</code>)
          to synchronize with Valve's latest depot build.
        </p>
      </div>

      {/* ==================================================================== */}
      {/* Purge Confirmation Modal */}
      {/* ==================================================================== */}
      {purgeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-red-500/30 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-red-500/15 border border-red-500/30 flex items-center justify-center text-red-400 flex-shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-white">Confirm Cache Purge</h3>
                <p className="text-xs text-zinc-400 mt-1">
                  You are about to delete server disk files for:
                </p>
                <p className="text-sm font-semibold text-red-300 mt-0.5">
                  {purgeTarget.title}
                </p>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-zinc-950 border border-white/5 space-y-2 text-xs">
              <div className="flex justify-between text-zinc-400">
                <span>Disk space to free:</span>
                <span className="font-mono font-semibold text-white">
                  {formatBytes(purgeTarget.cached_size_bytes ?? purgeTarget.size)}
                </span>
              </div>
              <div className="flex justify-between text-zinc-400">
                <span>Active library users:</span>
                <span className="font-mono text-zinc-300">{purgeTarget.user_count ?? 0}</span>
              </div>
              <div className="flex justify-between text-zinc-400">
                <span>Depot location:</span>
                <span className="font-mono text-zinc-400 truncate max-w-[200px]">
                  /data/repo/{purgeTarget.title}
                </span>
              </div>
            </div>

            <p className="text-xs text-zinc-400 leading-relaxed">
              This action immediately removes all cached depot files from server storage and
              overrides the 7-day orphan retention countdown. Subsequent client install requests
              will require a new SteamCMD download.
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setPurgeTarget(null)}
                disabled={isPurging}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-xs font-semibold transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handlePurgeGame}
                disabled={isPurging}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl text-xs font-semibold transition-colors shadow-lg shadow-red-600/20 disabled:opacity-50 flex items-center gap-2"
              >
                {isPurging ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Purging Files...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Confirm & Purge</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminPage;
