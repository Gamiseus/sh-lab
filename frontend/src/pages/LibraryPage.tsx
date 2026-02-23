import { useState } from "react";
import { RefreshCw, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { invoke } from "@tauri-apps/api/core";
import { useLibraryStore, LocalGameData, GameMetadata } from "../stores/LibraryStore";

export function LibraryPage() {
  const [isScanning, setIsScanning] = useState(false);
  const { setInstalledGames, setGameMetadata, removeGame, getLibrary } = useLibraryStore();

  const games = getLibrary();

  const handleScan = async () => {
    setIsScanning(true);
    try {
      const pathsJson = localStorage.getItem("sh_library_paths");
      const paths: string[] = pathsJson ? JSON.parse(pathsJson) : ["E:\\projects\\sh-lab\\data\\games"];

      const allFoundGames: LocalGameData[] = [];

      // 1. Scan Rust Side
      for (const path of paths) {
        console.log("Scanning path:", path);
        try {
          // invoke returns ScanResult[]
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
        const response = await fetch("http://localhost:8000/api/v1/store/metadata/batch", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(ids)
        });

        if (response.ok) {
          const metadata: GameMetadata[] = await response.json();
          setGameMetadata(metadata);
        }
      }

    } catch (err) {
      console.error("Scan failed:", err);
      alert("Scan failed check console");
    } finally {
      setIsScanning(false);
    }
  };

  const handleRemoveGame = async (e: React.MouseEvent, gameId: number) => {
    e.preventDefault();
    e.stopPropagation();

    if (confirm("UNINSTALL GAME? This will permanently delete the game files from your disk.")) {
      try {
        const game = games.find(g => g.id === gameId);
        if (!game || !game.install_path) {
          alert("Could not determine installation path.");
          return;
        }

        await invoke("uninstall_game_command", { path: game.install_path });
        removeGame(gameId);
        alert("Game uninstalled successfully.");
      } catch (err) {
        console.error("Uninstall failed:", err);
        alert(`Uninstall failed: ${err}`);
      }
    }
  };

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Library</h2>
        <div className="flex gap-2">
          <button
            onClick={handleScan}
            disabled={isScanning}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
            {isScanning ? 'Scanning Drives...' : 'Scan Library'}
          </button>
        </div>
      </div>

      {!games?.length ? (
        <div className="text-center py-20 text-zinc-500">
          No games found. Configure your folders in Settings and click Scan.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {games.map((game) => (
            <Link
              to={`/games/${game.id}`}
              key={game.id}
              className="group relative aspect-[3/4] bg-zinc-900 rounded-xl overflow-hidden border border-white/5 hover:border-blue-500/50 transition-all duration-300 hover:shadow-[0_0_30px_-5px_rgba(37,99,235,0.2)] block"
              onContextMenu={(e) => handleRemoveGame(e, game.id)}
            >
              <div className="absolute inset-0 bg-zinc-800">
                {game.cover_url ? (
                  <img
                    src={`http://localhost:8000${game.cover_url}`}
                    alt={game.title}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-zinc-800 text-zinc-700 font-bold text-4xl select-none">
                    {game.title.charAt(0)}
                  </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent opacity-60" />
              </div>

              <div className="absolute bottom-0 left-0 right-0 p-4">
                <h3 className="font-medium text-white truncate">{game.title}</h3>
                <p className="text-xs text-zinc-400">{Math.round(game.playtime_minutes / 60)}h played</p>
              </div>

              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20 backdrop-blur-[2px] gap-2">
                <button
                  onClick={(e) => { e.preventDefault(); }}
                  className="bg-blue-600 hover:bg-blue-500 text-white p-3 rounded-full shadow-lg transform scale-90 group-hover:scale-100 transition-transform"
                  title="Play"
                >
                  <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                </button>
              </div>

              <button
                onClick={(e) => handleRemoveGame(e, game.id)}
                className="absolute top-2 right-2 p-2 bg-black/50 hover:bg-red-500/80 rounded-full opacity-0 group-hover:opacity-100 transition-all z-10"
                title="Uninstall Game"
              >
                <Trash2 className="w-4 h-4 text-white" />
              </button>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
