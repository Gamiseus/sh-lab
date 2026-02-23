import { useState, useEffect } from "react";
import { Plus, Trash, Folder, AlertTriangle } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

export function SettingsPage() {
    const queryClient = useQueryClient();
    // Local State for Library Paths (persisted in localStorage)
    const [libraryPaths, setLibraryPaths] = useState<string[]>([]);

    useEffect(() => {
        const saved = localStorage.getItem("sh_library_paths");
        if (saved) {
            setLibraryPaths(JSON.parse(saved));
        } else {
            // Default path for first run
            setLibraryPaths(["E:\\projects\\sh-lab\\data\\games"]);
        }
    }, []);

    const savePaths = (paths: string[]) => {
        setLibraryPaths(paths);
        localStorage.setItem("sh_library_paths", JSON.stringify(paths));
    };

    const addPath = () => {
        // In a real app, this would open a native dialog
        const newPath = prompt("Enter full path to library folder:");
        if (newPath && !libraryPaths.includes(newPath)) {
            savePaths([...libraryPaths, newPath]);
        }
    };

    const removePath = (pathToRemove: string) => {
        savePaths(libraryPaths.filter(p => p !== pathToRemove));
    };

    const handleResetLibrary = async () => {
        if (confirm("Are you sure? This will mark all games as Uninstalled in the database. You will need to Scan again to find them.")) {
            try {
                await fetch("http://localhost:8000/api/v1/store/reset", { method: "POST" });
                alert("Library reset complete.");
                queryClient.invalidateQueries({ queryKey: ['games'] });
            } catch (e) {
                alert("Failed to reset library");
            }
        }
    };

    return (
        <div className="p-8 max-w-2xl mx-auto space-y-8">
            <div>
                <h2 className="text-3xl font-bold mb-2">Settings</h2>
                <p className="text-zinc-400">Manage your library locations and preferences.</p>
            </div>

            {/* Local Libraries Management */}
            <section className="space-y-4 bg-zinc-900/50 p-6 rounded-xl border border-white/5">
                <div className="flex items-center justify-between">
                    <div>
                        <h3 className="text-xl font-semibold">Local Game Libraries</h3>
                        <p className="text-sm text-zinc-500">
                            Manage where your games are installed.
                        </p>
                    </div>
                </div>

                <div className="space-y-3 pt-4">
                    {libraryPaths.map((path) => (
                        <div key={path} className="flex items-center gap-4 bg-black/40 p-4 rounded-lg border border-white/5 group">
                            <div className="bg-zinc-800 p-2 rounded text-zinc-400">
                                <Folder className="w-5 h-5" />
                            </div>
                            <div className="flex-1">
                                <h4 className="font-medium text-sm text-zinc-200 font-mono">{path}</h4>
                            </div>
                            <button
                                onClick={() => removePath(path)}
                                className="text-zinc-600 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity p-2"
                            >
                                <Trash className="w-4 h-4" />
                            </button>
                        </div>
                    ))}

                    <button
                        onClick={addPath}
                        className="w-full flex items-center justify-center gap-2 border border-dashed border-white/10 p-4 rounded-lg text-zinc-500 hover:text-zinc-300 hover:border-white/20 hover:bg-white/5 transition-all text-sm font-medium"
                    >
                        <Plus className="w-4 h-4" />
                        Add Library Location
                    </button>
                </div>
            </section>

            <section className="space-y-4 bg-red-900/10 p-6 rounded-xl border border-red-500/20">
                <div className="flex items-start gap-4">
                    <div className="bg-red-500/10 p-2 rounded text-red-500">
                        <AlertTriangle className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                        <h3 className="text-xl font-semibold text-red-500">Danger Zone</h3>
                        <p className="text-sm text-zinc-500 mt-1">
                            Resetting the library will disconnect all games from their folders.
                            Metadata will be kept, but you must Rescan to play.
                        </p>
                        <button
                            onClick={handleResetLibrary}
                            className="mt-4 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 rounded-lg text-sm font-medium transition-colors"
                        >
                            Reset Installed Library
                        </button>
                    </div>
                </div>
            </section>

            <section className="space-y-4 bg-zinc-900/50 p-6 rounded-xl border border-white/5">
                <h3 className="text-xl font-semibold">About sh_lab</h3>
                <p className="text-sm text-zinc-500">
                    Version 0.5.0 (Beta)<br />
                    Architecture: Frontend Scanner + Backend Store
                </p>
            </section>
        </div>
    );
}
