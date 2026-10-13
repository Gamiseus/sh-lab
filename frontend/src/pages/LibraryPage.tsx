import { useState, useMemo, useEffect } from "react";
import { RefreshCw, Trash2, Search, SlidersHorizontal, Gamepad2, Settings, ShoppingBag, Play, Download } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { invoke } from "@tauri-apps/api/core";
import { useLibraryStore, LocalGameData, GameMetadata, LibraryGame, LocalVerificationResult } from "../stores/LibraryStore";
import { useDownloadStore } from "@/stores/DownloadStore";
import { api, getImageUrl } from "@/lib/api";

export function LibraryPage() {
  const navigate = useNavigate();
  const [isScanning, setIsScanning] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<"title" | "playtime">("title");
  const { setInstalledGames, setGameMetadata, removeGame, removeFromLibrary, addInstalledGame, getLibrary, syncUserLibrary } = useLibraryStore();

  const games = getLibrary();

  // Sync user library from server on mount
  useEffect(() => {
    syncUserLibrary();
  }, [syncUserLibrary]);

  const installedCount = games.filter(g => g.is_installed).length;
  const uninstalledCount = games.length - installedCount;

  const handleScan = async () => {
    setIsScanning(true);
    try {
      const pathsJson = localStorage.getItem("sh_library_paths") || localStorage.getItem("library-paths");
      const paths: string[] = pathsJson
        ? JSON.parse(pathsJson)
        : ["c:\\Users\\Administrator\\Documents\\Projects\\sh-lab\\data\\games", "E:\\projects\\sh-lab\\data\\games"];

      const allFoundGames: LocalGameData[] = [];

      // 1. Scan Rust Side
      for (const path of paths) {
        console.log("Scanning path:", path);
        try {
          const results = await invoke<any[]>("scan_library_path", { path });
          results.forEach(r => {
            allFoundGames.push({
              id: r.game.id,
              path: r.path
            });
          });
        } catch (e) {
          console.error(`Failed to scan ${path}:`, e);
        }
      }

      // 2. Update Local Store
      setInstalledGames(allFoundGames);

      // 3. Fetch Metadata for these IDs from Backend
      if (allFoundGames.length > 0) {
        const ids = allFoundGames.map(g => g.id);
        const response = await api.post<GameMetadata[]>("/store/metadata/batch", ids);
        if (response.data) {
          setGameMetadata(response.data);
        }
      }
    } catch (err) {
      console.error("Scan failed:", err);
      alert("Scan failed. Check console for details.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleRemoveGame = async (e: React.MouseEvent, game: LibraryGame) => {
    e.preventDefault();
    e.stopPropagation();

    if (game.is_installed) {
      if (confirm("UNINSTALL GAME? This will permanently delete the game files from your disk.")) {
        try {
          if (!game.install_path) {
            alert("Could not determine installation path.");
            return;
          }

          await invoke("uninstall_game_command", { path: game.install_path });
          removeGame(game.id);
        } catch (err) {
          console.error("Uninstall failed:", err);
          alert(`Uninstall failed: ${err}`);
        }
      }
    } else {
      if (confirm(`Remove "${game.title}" from your library?`)) {
        await removeFromLibrary(game.id);
      }
    }
  };

  const handlePlayGame = async (e: React.MouseEvent, game: LibraryGame) => {
    e.preventDefault();
    e.stopPropagation();

    if (game.install_path) {
      try {
        await invoke("launch_game_command", {
          gamePath: game.install_path,
          customArgs: null,
        });
      } catch (err) {
        console.error("Failed to launch game directly:", err);
        navigate(`/games/${game.id}`);
      }
    } else {
      navigate(`/games/${game.id}`);
    }
  };

  const handleInstallGame = async (e: React.MouseEvent, game: LibraryGame) => {
    e.preventDefault();
    e.stopPropagation();

    // R3: Pre-check local disk before initiating network install
    try {
      const pathsJson = localStorage.getItem("sh_library_paths") || localStorage.getItem("library-paths");
      const configuredPaths: string[] = pathsJson
        ? JSON.parse(pathsJson)
        : ["c:\\Users\\Administrator\\Documents\\Projects\\sh-lab\\data\\games", "E:\\projects\\sh-lab\\data\\games"];

      const verifyResult = await invoke<LocalVerificationResult>("verify_local_game_command", {
        libraryPaths: configuredPaths,
        gameId: game.id,
        gameTitle: game.title,
        steamAppId: game.steam_app_id || null,
        expectedExe: null,
      });

      if (verifyResult.found && verifyResult.verified_binary && verifyResult.path) {
        addInstalledGame({
          id: game.id,
          path: verifyResult.path,
        });
        return;
      } else if (verifyResult.found && !verifyResult.verified_binary) {
        console.warn(`Local directory found for "${game.title}" but executable signature check failed. Redirecting to network installer.`);
      }
    } catch (err) {
      console.warn("Pre-flight check in LibraryPage:", err);
    }

    // Dispatch download to download queue and route to Downloads page
    await useDownloadStore.getState().enqueueDownload({
      id: game.id,
      title: game.title,
      cover_url: game.cover_url,
      header_image: (game as any).header_image,
      autoStart: true,
    });
    navigate("/downloads");
  };

  const filteredGames = useMemo(() => {
    const list = games.filter(g =>
      g.title.toLowerCase().includes(searchQuery.toLowerCase().trim())
    );

    return list.sort((a, b) => {
      if (sortBy === "playtime") {
        return (b.playtime_minutes || 0) - (a.playtime_minutes || 0);
      }
      return a.title.localeCompare(b.title);
    });
  }, [games, searchQuery, sortBy]);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header section with search, sort, and scan */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-extrabold tracking-tight text-white">Library</h2>
          <p className="text-sm text-zinc-400 mt-1">
            {games.length} {games.length === 1 ? "game" : "games"}
            {games.length > 0 && (
              <span className="text-zinc-500 ml-1.5">
                ({installedCount} installed{uninstalledCount > 0 ? `, ${uninstalledCount} uninstalled` : ""})
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Search box */}
          <div className="relative min-w-[200px] sm:min-w-[240px]">
            <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search library..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-zinc-900/80 border border-white/10 rounded-lg text-sm text-white placeholder-zinc-500 focus:border-violet-500 transition-colors"
            />
          </div>

          {/* Sort selector */}
          <div className="flex items-center gap-2 bg-zinc-900/80 border border-white/10 px-3 py-2 rounded-lg text-sm text-zinc-400">
            <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-500" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "title" | "playtime")}
              className="bg-transparent text-sm text-white focus:outline-none cursor-pointer"
            >
              <option value="title" className="bg-zinc-900 text-white">Sort by Name</option>
              <option value="playtime" className="bg-zinc-900 text-white">Sort by Playtime</option>
            </select>
          </div>

          {/* Scan button */}
          <button
            onClick={handleScan}
            disabled={isScanning}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-semibold transition-all duration-200 shadow-lg shadow-violet-600/20 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isScanning ? "animate-spin" : ""}`} />
            {isScanning ? "Scanning Drives..." : "Scan Library"}
          </button>
        </div>
      </div>

      {/* Content section */}
      {!games?.length ? (
        <div className="text-center py-20 px-6 rounded-2xl bg-zinc-900/40 border border-white/5 flex flex-col items-center justify-center max-w-xl mx-auto space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
            <Gamepad2 className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-bold text-white">Your library is empty</h3>
          <p className="text-sm text-zinc-400 max-w-md">
            Scan your configured storage drives to link local games, or explore the store catalog to discover and add new titles.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={handleScan}
              disabled={isScanning}
              className="flex items-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isScanning ? "animate-spin" : ""}`} />
              Scan Now
            </button>
            <Link
              to="/store"
              className="flex items-center gap-2 px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors border border-white/10"
            >
              <ShoppingBag className="w-4 h-4 text-violet-400" />
              Browse Store
            </Link>
            <Link
              to="/settings"
              className="flex items-center gap-2 px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm font-medium transition-colors border border-white/10"
            >
              <Settings className="w-4 h-4 text-zinc-400" />
              Settings
            </Link>
          </div>
        </div>
      ) : filteredGames.length === 0 ? (
        <div className="text-center py-16 px-4 rounded-xl bg-zinc-900/30 border border-white/5 space-y-2">
          <p className="text-zinc-400">No games found matching "{searchQuery}"</p>
          <button
            onClick={() => setSearchQuery("")}
            className="text-xs text-violet-400 hover:text-violet-300 underline"
          >
            Clear search filter
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
          {filteredGames.map((game) => {
            const isInstalled = game.is_installed;

            return (
              <Link
                to={`/games/${game.id}`}
                key={game.id}
                className={`group relative aspect-[3/4] bg-zinc-900 rounded-xl overflow-hidden border transition-all duration-300 block ${
                  isInstalled
                    ? "border-white/10 hover:border-violet-500/50 hover:shadow-[0_0_30px_-5px_rgba(124,58,237,0.3)]"
                    : "border-zinc-800/80 opacity-65 grayscale contrast-90 brightness-85 hover:opacity-100 hover:grayscale-0 hover:contrast-100 hover:brightness-100 hover:border-zinc-700"
                }`}
                onContextMenu={(e) => handleRemoveGame(e, game)}
              >
                <div className="absolute inset-0 bg-zinc-800">
                  {game.cover_url ? (
                    <img
                      src={getImageUrl(game.cover_url)}
                      alt={game.title}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-zinc-800 text-zinc-600 font-bold text-4xl select-none">
                      {game.title.charAt(0)}
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent opacity-80" />
                </div>

                {/* Steam-style Uninstalled Badge */}
                {!isInstalled && (
                  <span className="absolute top-2 left-2 z-20 px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase bg-black/75 text-zinc-300 border border-white/10 rounded backdrop-blur-sm shadow">
                    Not Installed
                  </span>
                )}

                <div className="absolute bottom-0 left-0 right-0 p-3.5 z-10">
                  <h3 className="font-semibold text-sm text-white truncate drop-shadow-sm">{game.title}</h3>
                  <p className="text-xs text-zinc-400 mt-0.5">
                    {isInstalled
                      ? `${Math.round((game.playtime_minutes || 0) / 60)}h played`
                      : "In Library • Uninstalled"}
                  </p>
                </div>

                {/* Hover actions */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40 backdrop-blur-[2px] gap-3 z-20">
                  {isInstalled ? (
                    <button
                      onClick={(e) => handlePlayGame(e, game)}
                      className="bg-violet-600 hover:bg-violet-500 text-white p-3.5 rounded-full shadow-xl transform scale-90 group-hover:scale-100 transition-transform duration-200"
                      title="Launch Game"
                    >
                      <Play className="w-5 h-5 fill-current translate-x-0.5" />
                    </button>
                  ) : (
                    <button
                      onClick={(e) => handleInstallGame(e, game)}
                      className="flex items-center gap-1.5 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-xs font-bold rounded-lg shadow-xl transform scale-90 group-hover:scale-100 transition-all duration-200 hover:scale-105"
                      title="Install Game"
                    >
                      <Download className="w-4 h-4" />
                      <span>Install</span>
                    </button>
                  )}
                </div>

                <button
                  onClick={(e) => handleRemoveGame(e, game)}
                  className="absolute top-2 right-2 p-2 bg-black/60 hover:bg-red-600 rounded-full opacity-0 group-hover:opacity-100 transition-all z-20 text-white"
                  title={isInstalled ? "Uninstall Game" : "Remove from Library"}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
