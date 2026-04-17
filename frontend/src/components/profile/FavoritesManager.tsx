import { useState, useEffect } from "react";
import { X, Search, Plus, ArrowUp, ArrowDown, Trash2, Loader2, Save } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { storeAPI, FavoriteGameDisplay, getImageUrl } from "@/lib/api";

interface FavoritesManagerProps {
    currentFavorites: FavoriteGameDisplay[];
    onSave: (ids: number[]) => Promise<void>;
    onClose: () => void;
}

// Minimal game info needed for the list
interface GameItem {
    id: number;
    title: string;
    cover_url?: string;
}

export function FavoritesManager({ currentFavorites, onSave, onClose }: FavoritesManagerProps) {
    const [selectedGames, setSelectedGames] = useState<GameItem[]>([]);
    const [searchQuery, setSearchQuery] = useState("");
    const [isSaving, setIsSaving] = useState(false);

    // Initialize state from props
    useEffect(() => {
        setSelectedGames(
            currentFavorites.map(f => ({
                id: f.game_id,
                title: f.title,
                cover_url: f.cover_url || undefined
            }))
        );
    }, [currentFavorites]);

    // Search query
    const { data: searchResults, isLoading: isSearching } = useQuery({
        queryKey: ["game-search", searchQuery],
        queryFn: () => storeAPI.getGames({ search: searchQuery, limit: 20 }),
        enabled: searchQuery.length >= 2,
    });

    const handleAdd = (game: GameItem) => {
        if (selectedGames.length >= 12) return;
        if (selectedGames.some(g => g.id === game.id)) return;
        setSelectedGames([...selectedGames, game]);
    };

    const handleRemove = (id: number) => {
        setSelectedGames(selectedGames.filter(g => g.id !== id));
    };

    const handleMove = (index: number, direction: 'up' | 'down') => {
        const newList = [...selectedGames];
        const targetIndex = direction === 'up' ? index - 1 : index + 1;

        if (targetIndex < 0 || targetIndex >= newList.length) return;

        [newList[index], newList[targetIndex]] = [newList[targetIndex], newList[index]];
        setSelectedGames(newList);
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await onSave(selectedGames.map(g => g.id));
            onClose();
        } catch (e) {
            console.error(e);
            alert("Failed to save favorites");
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="bg-zinc-900 border border-white/10 rounded-xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-white/10">
                    <div>
                        <h2 className="text-xl font-bold text-white">Manage Favorite Games</h2>
                        <p className="text-zinc-400 text-sm mt-1">
                            Select up to 12 games to feature on your profile
                        </p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg transition-colors">
                        <X className="w-5 h-5 text-zinc-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
                    {/* Left: Search */}
                    <div className="flex-1 flex flex-col p-6 border-b md:border-b-0 md:border-r border-white/10 min-h-[300px]">
                        <div className="relative mb-4">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search library..."
                                className="w-full pl-9 pr-4 py-2 bg-black/50 border border-white/10 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
                                autoFocus
                            />
                        </div>

                        <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                            {searchQuery.length < 2 ? (
                                <div className="text-center py-12 text-zinc-500">
                                    Type to search for games
                                </div>
                            ) : isSearching ? (
                                <div className="flex justify-center py-12">
                                    <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
                                </div>
                            ) : searchResults && searchResults.length > 0 ? (
                                searchResults.map(game => {
                                    const isSelected = selectedGames.some(g => g.id === game.id);
                                    return (
                                        <div
                                            key={game.id}
                                            className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${isSelected ? 'opacity-50 cursor-not-allowed' : 'hover:bg-white/5 cursor-pointer'
                                                }`}
                                            onClick={() => !isSelected && handleAdd(game)}
                                        >
                                            {game.cover_url ? (
                                                <img src={getImageUrl(game.cover_url)} alt="" className="w-10 h-14 object-cover rounded bg-zinc-800" />
                                            ) : (
                                                <div className="w-10 h-14 bg-zinc-800 rounded flex items-center justify-center text-xs text-zinc-500">
                                                    Img
                                                </div>
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <div className="text-white font-medium truncate">{game.title}</div>
                                                <div className="text-xs text-zinc-500 truncate">{game.developer}</div>
                                            </div>
                                            {!isSelected && (
                                                <button className="p-1.5 bg-white/10 hover:bg-white/20 rounded-md text-white">
                                                    <Plus className="w-4 h-4" />
                                                </button>
                                            )}
                                        </div>
                                    );
                                })
                            ) : (
                                <div className="text-center py-12 text-zinc-500">
                                    No games found
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right: Selected */}
                    <div className="flex-1 flex flex-col p-6 bg-black/20">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="font-medium text-white">Selected Games</h3>
                            <span className={`text-sm font-medium ${selectedGames.length === 12 ? 'text-red-400' : 'text-zinc-400'}`}>
                                {selectedGames.length} / 12
                            </span>
                        </div>

                        <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar">
                            {selectedGames.length === 0 ? (
                                <div className="text-center py-12 text-zinc-500 border-2 border-dashed border-white/5 rounded-xl">
                                    No games selected
                                </div>
                            ) : (
                                selectedGames.map((game, index) => (
                                    <div key={game.id} className="flex items-center gap-3 p-2 bg-zinc-900/50 border border-white/5 rounded-lg group">
                                        <div className="flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={() => handleMove(index, 'up')}
                                                disabled={index === 0}
                                                className="p-1 hover:bg-white/10 rounded text-zinc-400 hover:text-white disabled:opacity-30"
                                            >
                                                <ArrowUp className="w-3 h-3" />
                                            </button>
                                            <button
                                                onClick={() => handleMove(index, 'down')}
                                                disabled={index === selectedGames.length - 1}
                                                className="p-1 hover:bg-white/10 rounded text-zinc-400 hover:text-white disabled:opacity-30"
                                            >
                                                <ArrowDown className="w-3 h-3" />
                                            </button>
                                        </div>

                                        {game.cover_url ? (
                                            <img src={getImageUrl(game.cover_url)} alt="" className="w-10 h-14 object-cover rounded bg-zinc-800" />
                                        ) : (
                                            <div className="w-10 h-14 bg-zinc-800 rounded flex items-center justify-center text-xs text-zinc-500">
                                                Img
                                            </div>
                                        )}

                                        <div className="flex-1 min-w-0">
                                            <div className="text-white font-medium truncate">{game.title}</div>
                                        </div>

                                        <button
                                            onClick={() => handleRemove(game.id)}
                                            className="p-2 hover:bg-red-500/20 text-zinc-500 hover:text-red-400 rounded-lg transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-white/10 flex justify-end gap-3 bg-black/20">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-white transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={isSaving}
                        className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        {isSaving ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Save className="w-4 h-4" />
                        )}
                        Save Changes
                    </button>
                </div>
            </div>
        </div>
    );
}
