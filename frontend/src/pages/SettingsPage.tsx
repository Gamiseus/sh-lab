import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
    Plus,
    Trash2,
    Folder,
    AlertTriangle,
    CheckCircle,
    Info,
    HardDrive,
    ShoppingBag,
    Server,
    RefreshCw,
    Database,
    Layers,
    Clock,
    Users,
    ExternalLink
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

export interface StorageStatus {
    total_bytes?: number;
    used_bytes?: number;
    total_storage?: number;
    used_storage?: number;
    cached_games_count?: number;
    cached_count?: number;
    orphaned_games_count?: number;
    orphaned_count?: number;
}

export interface StorageGame {
    game_id: number;
    title: string;
    steam_app_id?: number | null;
    user_count: number;
    cached_size_bytes: number;
    build_id?: string | null;
    latest_build_id?: string | null;
    last_check?: string | null;
    is_cached: boolean;
    orphaned_at?: string | null;
}

function formatBytes(bytes: number | undefined | null): string {
    if (bytes === undefined || bytes === null || isNaN(bytes)) return "0 B";
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export function SettingsPage() {
    const queryClient = useQueryClient();
    const { user } = useAuth();

    // Local library settings state
    const [libraryPaths, setLibraryPaths] = useState<string[]>([]);
    const [newPathInput, setNewPathInput] = useState("");
    const [isAddingPath, setIsAddingPath] = useState(false);
    const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
    const [confirmReset, setConfirmReset] = useState(false);
    const [isResetting, setIsResetting] = useState(false);
    const [hideStorePrices, setHideStorePrices] = useState(false);

    // Admin storage panel state
    const [confirmPurgeId, setConfirmPurgeId] = useState<number | null>(null);
    const [actionLoading, setActionLoading] = useState<{ [gameId: number]: "update" | "purge" | null }>({});

    // Server Storage & Installs Queries
    const {
        data: storageStatus,
        isLoading: isLoadingStatus,
        refetch: refetchStatus
    } = useQuery<StorageStatus>({
        queryKey: ["adminStorageStatus"],
        queryFn: async () => {
            const res = await api.get("/admin/storage/status");
            return res.data;
        },
        enabled: !!user?.is_admin,
    });

    const {
        data: storageGames = [],
        isLoading: isLoadingGames,
        refetch: refetchGames
    } = useQuery<StorageGame[]>({
        queryKey: ["adminStorageGames"],
        queryFn: async () => {
            const res = await api.get("/admin/storage/games");
            return res.data;
        },
        enabled: !!user?.is_admin,
    });

    useEffect(() => {
        const saved = localStorage.getItem("sh_library_paths");
        if (saved) {
            try {
                setLibraryPaths(JSON.parse(saved));
            } catch {
                setLibraryPaths(["E:\\projects\\sh-lab\\data\\games"]);
            }
        } else {
            setLibraryPaths(["E:\\projects\\sh-lab\\data\\games"]);
        }

        const savedPricePref = localStorage.getItem("sh_hide_store_prices");
        if (savedPricePref !== null) {
            setHideStorePrices(savedPricePref === "true");
        }
    }, []);

    const savePaths = (paths: string[]) => {
        setLibraryPaths(paths);
        localStorage.setItem("sh_library_paths", JSON.stringify(paths));
    };

    const handleAddPath = (e: React.FormEvent) => {
        e.preventDefault();
        const trimmed = newPathInput.trim();
        if (!trimmed) return;

        if (libraryPaths.includes(trimmed)) {
            setStatusMessage({ type: "error", text: "This library location is already in your list." });
            return;
        }

        const updated = [...libraryPaths, trimmed];
        savePaths(updated);
        setNewPathInput("");
        setIsAddingPath(false);
        setStatusMessage({ type: "success", text: "Library location added successfully." });
        setTimeout(() => setStatusMessage(null), 3000);
    };

    const removePath = (pathToRemove: string) => {
        const updated = libraryPaths.filter(p => p !== pathToRemove);
        savePaths(updated);
        setStatusMessage({ type: "success", text: "Library location removed." });
        setTimeout(() => setStatusMessage(null), 3000);
    };

    const handleToggleHideStorePrices = (checked: boolean) => {
        setHideStorePrices(checked);
        localStorage.setItem("sh_hide_store_prices", String(checked));
        setStatusMessage({
            type: "success",
            text: checked ? "Storefront prices will be hidden on the main store page." : "Storefront prices are now visible."
        });
        setTimeout(() => setStatusMessage(null), 3000);
    };

    const handleResetLibrary = async () => {
        setIsResetting(true);
        try {
            await api.post("/store/reset");
            setStatusMessage({ type: "success", text: "Library reset complete. Markings refreshed." });
            setConfirmReset(false);
            queryClient.invalidateQueries({ queryKey: ["games"] });
        } catch {
            setStatusMessage({ type: "error", text: "Failed to reset library." });
        } finally {
            setIsResetting(false);
            setTimeout(() => setStatusMessage(null), 4000);
        }
    };

    // Admin Storage Actions
    const handleForceUpdate = async (gameId: number, title: string) => {
        setActionLoading(prev => ({ ...prev, [gameId]: "update" }));
        try {
            await api.post(`/admin/storage/${gameId}/update`);
            setStatusMessage({ type: "success", text: `Depot update & verification triggered for "${title}".` });
            queryClient.invalidateQueries({ queryKey: ["adminStorageGames"] });
            queryClient.invalidateQueries({ queryKey: ["adminStorageStatus"] });
        } catch {
            setStatusMessage({ type: "error", text: `Failed to trigger depot update for "${title}".` });
        } finally {
            setActionLoading(prev => ({ ...prev, [gameId]: null }));
            setTimeout(() => setStatusMessage(null), 4000);
        }
    };

    const handlePurgeCache = async (gameId: number, title: string) => {
        setActionLoading(prev => ({ ...prev, [gameId]: "purge" }));
        try {
            await api.post(`/admin/storage/${gameId}/purge`);
            setStatusMessage({ type: "success", text: `Cache successfully purged for "${title}".` });
            setConfirmPurgeId(null);
            queryClient.invalidateQueries({ queryKey: ["adminStorageGames"] });
            queryClient.invalidateQueries({ queryKey: ["adminStorageStatus"] });
        } catch {
            setStatusMessage({ type: "error", text: `Failed to purge cache for "${title}".` });
        } finally {
            setActionLoading(prev => ({ ...prev, [gameId]: null }));
            setTimeout(() => setStatusMessage(null), 4000);
        }
    };

    // Calculate Storage Metrics
    const totalBytes = storageStatus?.total_bytes ?? storageStatus?.total_storage ?? 0;
    const usedBytes = storageStatus?.used_bytes ?? storageStatus?.used_storage ?? 0;
    const cachedCount = storageStatus?.cached_games_count ?? storageStatus?.cached_count ?? 0;
    const orphanedCount = storageStatus?.orphaned_games_count ?? storageStatus?.orphaned_count ?? 0;
    const utilizationPct = totalBytes > 0 ? Math.min(100, Math.round((usedBytes / totalBytes) * 100)) : 0;

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in duration-300">
            <div>
                <h1 className="text-3xl font-extrabold tracking-tight text-white">Settings</h1>
                <p className="text-zinc-400 mt-1">Manage game storage directories, server cache, scanner preferences, and client options.</p>
            </div>

            {/* Notification alert banner */}
            {statusMessage && (
                <div
                    className={`flex items-center gap-3 p-4 rounded-xl border text-sm animate-in fade-in duration-200 ${
                        statusMessage.type === "success"
                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                            : "bg-red-500/10 border-red-500/30 text-red-300"
                    }`}
                >
                    {statusMessage.type === "success" ? (
                        <CheckCircle className="w-5 h-5 flex-shrink-0" />
                    ) : (
                        <AlertTriangle className="w-5 h-5 flex-shrink-0" />
                    )}
                    <span>{statusMessage.text}</span>
                </div>
            )}

            {/* Server Storage & Installs (Admin Only) */}
            {user?.is_admin && (
                <section className="space-y-6 bg-zinc-900/60 p-6 rounded-2xl border border-violet-500/30 shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-violet-600/5 rounded-full blur-3xl -z-10 pointer-events-none" />

                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-2 border-b border-white/5">
                        <div>
                            <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                <Server className="w-5 h-5 text-violet-400" />
                                Server Storage & Installs
                                <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-semibold border border-violet-500/30">
                                    Admin
                                </span>
                            </h2>
                            <p className="text-sm text-zinc-400 mt-0.5">
                                Server disk footprint, cached game depots, and cache maintenance controls.
                            </p>
                        </div>
                        <div className="flex items-center gap-2.5">
                            <button
                                onClick={() => {
                                    refetchStatus();
                                    refetchGames();
                                }}
                                disabled={isLoadingStatus || isLoadingGames}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:text-white bg-zinc-800/80 hover:bg-zinc-700/80 rounded-lg border border-white/10 transition-colors disabled:opacity-50"
                                title="Refresh Storage Metrics"
                            >
                                <RefreshCw className={cn("w-3.5 h-3.5", (isLoadingStatus || isLoadingGames) && "animate-spin text-violet-400")} />
                                Refresh
                            </button>
                            <Link
                                to="/admin"
                                className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-violet-300 hover:text-white bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/30 rounded-lg transition-colors"
                            >
                                Admin Page
                                <ExternalLink className="w-3.5 h-3.5" />
                            </Link>
                        </div>
                    </div>

                    {/* High-Level Storage Metrics Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="p-4 bg-zinc-950/60 rounded-xl border border-white/5 space-y-1">
                            <div className="flex items-center gap-2 text-zinc-400 text-xs font-medium">
                                <Database className="w-3.5 h-3.5 text-violet-400" />
                                Total Disk
                            </div>
                            <p className="text-xl font-extrabold text-white font-mono">
                                {isLoadingStatus ? "..." : formatBytes(totalBytes)}
                            </p>
                            <p className="text-[11px] text-zinc-500">Server disk footprint</p>
                        </div>

                        <div className="p-4 bg-zinc-950/60 rounded-xl border border-white/5 space-y-1">
                            <div className="flex items-center gap-2 text-zinc-400 text-xs font-medium">
                                <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
                                Used Storage
                            </div>
                            <p className="text-xl font-extrabold text-white font-mono">
                                {isLoadingStatus ? "..." : formatBytes(usedBytes)}
                            </p>
                            <p className="text-[11px] text-zinc-500">{utilizationPct}% capacity utilized</p>
                        </div>

                        <div className="p-4 bg-zinc-950/60 rounded-xl border border-white/5 space-y-1">
                            <div className="flex items-center gap-2 text-zinc-400 text-xs font-medium">
                                <Layers className="w-3.5 h-3.5 text-blue-400" />
                                Cached Games
                            </div>
                            <p className="text-xl font-extrabold text-white font-mono">
                                {isLoadingStatus ? "..." : cachedCount}
                            </p>
                            <p className="text-[11px] text-zinc-500">Active server titles</p>
                        </div>

                        <div className="p-4 bg-zinc-950/60 rounded-xl border border-white/5 space-y-1">
                            <div className="flex items-center gap-2 text-zinc-400 text-xs font-medium">
                                <Clock className="w-3.5 h-3.5 text-amber-400" />
                                Orphaned
                            </div>
                            <p className="text-xl font-extrabold text-white font-mono">
                                {isLoadingStatus ? "..." : orphanedCount}
                            </p>
                            <p className="text-[11px] text-zinc-500">7-day cleanup retention</p>
                        </div>
                    </div>

                    {/* Visual Disk Utilization Progress Bar */}
                    <div className="bg-zinc-950/60 p-4 rounded-xl border border-white/5 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-zinc-400">Server Storage Footprint Breakdown</span>
                            <span className="font-mono font-medium text-zinc-300">
                                {formatBytes(usedBytes)} of {formatBytes(totalBytes)} ({utilizationPct}%)
                            </span>
                        </div>
                        <div className="w-full bg-zinc-800 rounded-full h-2.5 overflow-hidden">
                            <div
                                className={cn(
                                    "h-full rounded-full transition-all duration-500",
                                    utilizationPct > 90
                                        ? "bg-red-500"
                                        : utilizationPct > 70
                                        ? "bg-amber-500"
                                        : "bg-gradient-to-r from-violet-500 to-indigo-500"
                                )}
                                style={{ width: `${Math.min(100, Math.max(0, utilizationPct))}%` }}
                            />
                        </div>
                    </div>

                    {/* Tracked Games Catalog Breakdown */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-bold text-zinc-200 uppercase tracking-wider">
                                Tracked Titles & Cache Footprint ({storageGames.length})
                            </h3>
                            <span className="text-xs text-zinc-500">SteamCMD Depot Management</span>
                        </div>

                        {isLoadingGames ? (
                            <div className="p-8 text-center text-zinc-400 text-sm bg-zinc-950/40 rounded-xl border border-white/5">
                                <RefreshCw className="w-5 h-5 mx-auto animate-spin text-violet-400 mb-2" />
                                Loading tracked games & storage breakdown...
                            </div>
                        ) : storageGames.length === 0 ? (
                            <div className="p-8 text-center text-zinc-400 text-sm bg-zinc-950/40 rounded-xl border border-white/5">
                                No games are currently tracked in the server repository.
                            </div>
                        ) : (
                            <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                                {storageGames.map((game) => (
                                    <div
                                        key={game.game_id}
                                        className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-zinc-950/60 p-3.5 rounded-xl border border-white/5 hover:border-violet-500/20 transition-all"
                                    >
                                        <div className="min-w-0 flex-1 space-y-1">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <h4 className="font-bold text-white text-sm truncate">{game.title}</h4>
                                                {game.steam_app_id && (
                                                    <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                                                        AppID: {game.steam_app_id}
                                                    </span>
                                                )}
                                                {game.is_cached ? (
                                                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                        Cached
                                                    </span>
                                                ) : (
                                                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400">
                                                        Not Cached
                                                    </span>
                                                )}
                                                {game.orphaned_at && (
                                                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20" title="Orphaned: in 7-day retention period">
                                                        Orphaned
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-3 text-xs text-zinc-400 flex-wrap">
                                                <span className="flex items-center gap-1">
                                                    <Users className="w-3.5 h-3.5 text-zinc-500" />
                                                    {game.user_count} {game.user_count === 1 ? "user" : "users"}
                                                </span>
                                                <span>•</span>
                                                <span className="flex items-center gap-1 font-mono text-zinc-300">
                                                    <HardDrive className="w-3.5 h-3.5 text-zinc-500" />
                                                    {formatBytes(game.cached_size_bytes)}
                                                </span>
                                                {game.build_id && (
                                                    <>
                                                        <span>•</span>
                                                        <span className="font-mono text-zinc-400 text-[11px]">
                                                            Build: {game.build_id}
                                                        </span>
                                                    </>
                                                )}
                                            </div>
                                        </div>

                                        {/* Action buttons */}
                                        <div className="flex items-center gap-2 flex-shrink-0 pt-1 sm:pt-0">
                                            <button
                                                onClick={() => handleForceUpdate(game.game_id, game.title)}
                                                disabled={actionLoading[game.game_id] !== undefined && actionLoading[game.game_id] !== null}
                                                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 hover:text-white rounded-lg border border-violet-500/30 transition-colors disabled:opacity-50"
                                                title="Force SteamCMD depot update & validation"
                                            >
                                                <RefreshCw
                                                    className={cn(
                                                        "w-3.5 h-3.5",
                                                        actionLoading[game.game_id] === "update" && "animate-spin text-violet-400"
                                                    )}
                                                />
                                                {actionLoading[game.game_id] === "update" ? "Updating..." : "Force Update"}
                                            </button>

                                            {confirmPurgeId === game.game_id ? (
                                                <div className="flex items-center gap-1.5">
                                                    <button
                                                        onClick={() => handlePurgeCache(game.game_id, game.title)}
                                                        disabled={actionLoading[game.game_id] === "purge"}
                                                        className="px-2.5 py-1.5 text-xs font-semibold bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors"
                                                    >
                                                        {actionLoading[game.game_id] === "purge" ? "Purging..." : "Confirm"}
                                                    </button>
                                                    <button
                                                        onClick={() => setConfirmPurgeId(null)}
                                                        className="px-2 py-1.5 text-xs text-zinc-400 hover:text-white"
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            ) : (
                                                <button
                                                    onClick={() => setConfirmPurgeId(game.game_id)}
                                                    disabled={!game.is_cached || (actionLoading[game.game_id] !== undefined && actionLoading[game.game_id] !== null)}
                                                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                                    title={game.is_cached ? "Purge cached files from server disk" : "No files currently cached"}
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                    Purge
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </section>
            )}

            {/* Local Libraries Management */}
            <section className="space-y-5 bg-zinc-900/60 p-6 rounded-2xl border border-white/10 shadow-lg">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-bold text-white flex items-center gap-2">
                            <HardDrive className="w-5 h-5 text-violet-400" />
                            Storage & Game Libraries
                        </h2>
                        <p className="text-sm text-zinc-400 mt-0.5">
                            Folders on your drives scanned for local installations and manifests.
                        </p>
                    </div>
                </div>

                <div className="space-y-3 pt-2">
                    {libraryPaths.map((path) => (
                        <div
                            key={path}
                            className="flex items-center gap-4 bg-zinc-950/60 p-3.5 rounded-xl border border-white/5 hover:border-violet-500/30 transition-all group"
                        >
                            <div className="bg-violet-600/10 p-2.5 rounded-lg text-violet-400 border border-violet-500/20">
                                <Folder className="w-4 h-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="font-mono text-xs sm:text-sm text-zinc-200 truncate select-all">{path}</p>
                            </div>
                            <button
                                onClick={() => removePath(path)}
                                className="text-zinc-500 hover:text-red-400 p-2 rounded-lg hover:bg-red-500/10 transition-colors opacity-70 group-hover:opacity-100"
                                title="Remove folder location"
                            >
                                <Trash2 className="w-4 h-4" />
                            </button>
                        </div>
                    ))}

                    {/* Inline Add Folder Form */}
                    {isAddingPath ? (
                        <form onSubmit={handleAddPath} className="p-4 rounded-xl bg-zinc-950/80 border border-violet-500/40 space-y-3">
                            <label className="block text-xs font-semibold text-zinc-300">
                                Enter Absolute Directory Path
                            </label>
                            <input
                                type="text"
                                placeholder="e.g. D:\Games\sh-lab or /mnt/games"
                                value={newPathInput}
                                onChange={(e) => setNewPathInput(e.target.value)}
                                className="w-full px-3 py-2 bg-zinc-900 border border-white/10 rounded-lg text-sm text-white focus:border-violet-500 font-mono transition-colors"
                                autoFocus
                            />
                            <div className="flex items-center justify-end gap-2 pt-1">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setIsAddingPath(false);
                                        setNewPathInput("");
                                    }}
                                    className="px-3 py-1.5 text-xs text-zinc-400 hover:text-white rounded-lg transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-1.5 text-xs font-semibold bg-violet-600 hover:bg-violet-500 text-white rounded-lg transition-colors shadow-md shadow-violet-600/20"
                                >
                                    Save Location
                                </button>
                            </div>
                        </form>
                    ) : (
                        <button
                            onClick={() => setIsAddingPath(true)}
                            className="w-full flex items-center justify-center gap-2 border border-dashed border-white/15 p-3.5 rounded-xl text-zinc-400 hover:text-violet-300 hover:border-violet-500/40 hover:bg-violet-600/5 transition-all text-sm font-medium"
                        >
                            <Plus className="w-4 h-4" />
                            Add Library Location
                        </button>
                    )}
                </div>
            </section>

            {/* Storefront Preferences */}
            <section className="space-y-5 bg-zinc-900/60 p-6 rounded-2xl border border-white/10 shadow-lg">
                <div>
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <ShoppingBag className="w-5 h-5 text-violet-400" />
                        Storefront Preferences
                    </h2>
                    <p className="text-sm text-zinc-400 mt-0.5">
                        Customize catalog browsing and display settings on the main store page.
                    </p>
                </div>

                <div className="pt-1">
                    <div className="flex items-center justify-between p-4 bg-zinc-950/60 rounded-xl border border-white/5 hover:border-violet-500/20 transition-all">
                        <div className="space-y-0.5 pr-4">
                            <span className="text-sm font-semibold text-white">Hide prices on main storefront</span>
                            <p className="text-xs text-zinc-400">
                                Conceals game prices across the main storefront carousels and discovery rows. Prices remain visible in search results, filtered list views, and individual game store pages.
                            </p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer flex-shrink-0">
                            <input
                                type="checkbox"
                                checked={hideStorePrices}
                                onChange={(e) => handleToggleHideStorePrices(e.target.checked)}
                                className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-violet-600"></div>
                        </label>
                    </div>
                </div>
            </section>

            {/* Danger Zone */}
            <section className="space-y-4 bg-red-950/15 p-6 rounded-2xl border border-red-500/20">
                <div className="flex items-start gap-4">
                    <div className="bg-red-500/15 p-2.5 rounded-xl text-red-400 border border-red-500/30">
                        <AlertTriangle className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                        <h2 className="text-lg font-bold text-red-400">Danger Zone</h2>
                        <p className="text-sm text-zinc-400 mt-1 leading-relaxed">
                            Resetting the installed library unlinks games from their installation paths in the database.
                            Metadata and playtime records are retained, but a re-scan will be required to launch installed titles.
                        </p>

                        {confirmReset ? (
                            <div className="mt-4 p-4 rounded-xl bg-red-950/40 border border-red-500/30 space-y-3">
                                <p className="text-sm font-semibold text-red-300">
                                    Are you sure? This action cannot be automatically undone.
                                </p>
                                <div className="flex items-center gap-3">
                                    <button
                                        onClick={handleResetLibrary}
                                        disabled={isResetting}
                                        className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-semibold transition-colors disabled:opacity-50"
                                    >
                                        {isResetting ? "Resetting..." : "Yes, Reset Library"}
                                    </button>
                                    <button
                                        onClick={() => setConfirmReset(false)}
                                        className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium transition-colors"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <button
                                onClick={() => setConfirmReset(true)}
                                className="mt-4 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-lg text-sm font-medium transition-colors"
                            >
                                Reset Installed Library
                            </button>
                        )}
                    </div>
                </div>
            </section>

            {/* About Section */}
            <section className="bg-zinc-900/60 p-6 rounded-2xl border border-white/10 space-y-3">
                <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-violet-400" />
                    <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-400">About sh_lab</h2>
                </div>
                <div className="text-sm text-zinc-300 space-y-1">
                    <p className="font-semibold text-white">sh_lab Client v0.5.0 (Beta)</p>
                    <p className="text-zinc-400">Architecture: Frontend Scanner + Tauri Desktop Core + FastAPI Store</p>
                </div>
            </section>
        </div>
    );
}
