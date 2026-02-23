import { useQuery } from "@tanstack/react-query";
import { Search, Flame, Star, Clock, TrendingUp, Gamepad2, X } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { storeAPI } from "@/lib/api";
import { HeroCarousel } from "@/components/store/HeroCarousel";
import { GameRow } from "@/components/store/GameRow";
import { GameCard } from "@/components/store/GameCard";
import { FilterDropdown } from "@/components/store/FilterDropdown";
import type { Game } from "@/lib/api";

export function StorePage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [limit, setLimit] = useState(50);

    // Derived state from URL
    const searchQuery = searchParams.get("search") || "";
    // getAll returns all values for key 'genre'
    const selectedGenres = searchParams.getAll("genre");
    const selectedCategories = searchParams.getAll("category");

    // Fetch discovery data
    const { data: featured = [] } = useQuery<Game[]>({
        queryKey: ["store", "featured"],
        queryFn: () => storeAPI.getFeatured(5),
    });

    const { data: trending = [] } = useQuery<Game[]>({
        queryKey: ["store", "trending"],
        queryFn: () => storeAPI.getTrending(12),
    });

    const { data: popular = [] } = useQuery<Game[]>({
        queryKey: ["store", "popular"],
        queryFn: () => storeAPI.getPopular(12),
    });

    const { data: recent = [] } = useQuery<Game[]>({
        queryKey: ["store", "recent"],
        queryFn: () => storeAPI.getRecent(12),
    });

    const { data: topRated = [] } = useQuery<Game[]>({
        queryKey: ["store", "top-rated"],
        queryFn: () => storeAPI.getTopRated(12),
    });

    const { data: genres = [] } = useQuery<string[]>({
        queryKey: ["store", "genres"],
        queryFn: () => storeAPI.getGenres(),
    });

    const { data: categories = [] } = useQuery<{ id: number, description: string }[]>({
        queryKey: ["store", "categories"],
        queryFn: () => storeAPI.getCategories(),
    });

    // Fetch all games for browsing
    const { data: allGames = [], isLoading, isFetching } = useQuery<Game[]>({
        queryKey: ["store", "games", searchQuery, selectedGenres, selectedCategories, limit],
        queryFn: () => storeAPI.getGames({
            search: searchQuery || undefined,
            genre: selectedGenres.length > 0 ? selectedGenres : undefined,
            category: selectedCategories.length > 0 ? selectedCategories : undefined,
            limit: limit,
        }),
    });

    const toggleGenre = (genre: string) => {
        setLimit(50);
        setSearchParams(prev => {
            const newParams = new URLSearchParams(prev);
            const current = newParams.getAll("genre");
            newParams.delete("genre");
            if (current.includes(genre)) {
                current.filter(g => g !== genre).forEach(g => newParams.append("genre", g));
            } else {
                [...current, genre].forEach(g => newParams.append("genre", g));
            }
            return newParams;
        }, { replace: true });
    };

    const toggleCategory = (category: string) => {
        setLimit(50);
        setSearchParams(prev => {
            const newParams = new URLSearchParams(prev);
            const current = newParams.getAll("category");
            newParams.delete("category");
            if (current.includes(category)) {
                current.filter(c => c !== category).forEach(c => newParams.append("category", c));
            } else {
                [...current, category].forEach(c => newParams.append("category", c));
            }
            return newParams;
        }, { replace: true });
    };

    const handleSearchChange = (val: string) => {
        setLimit(50);
        setSearchParams(prev => {
            const newParams = new URLSearchParams(prev);
            if (val) newParams.set("search", val);
            else newParams.delete("search");
            return newParams;
        }, { replace: true });
    };

    const isFiltering = searchQuery || selectedGenres.length > 0 || selectedCategories.length > 0;

    return (
        <div className="min-h-screen pb-12">
            {/* Hero Section */}
            {!isFiltering && (
                <section className="px-6 pt-6">
                    <HeroCarousel games={featured} />
                </section>
            )}

            {/* Search & Filters Bar */}
            <section className="sticky top-0 z-20 px-6 py-6 bg-background/90 backdrop-blur-xl border-b border-white/5 shadow-2xl shadow-black/20">
                <div className="max-w-7xl mx-auto flex flex-col md:flex-row gap-4 items-start md:items-center">
                    {/* Search - Flexible Width */}
                    <div className="relative flex-1 w-full group">
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-violet-600 to-indigo-600 rounded-2xl opacity-20 group-hover:opacity-40 transition duration-500 blur"></div>
                        <div className="relative">
                            <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-zinc-400 group-focus-within:text-violet-400 transition-colors" />
                            <input
                                type="text"
                                placeholder="Search games by title, developer, or publisher..."
                                value={searchQuery}
                                onChange={(e) => handleSearchChange(e.target.value)}
                                className="
                                    w-full pl-14 pr-6 py-4 text-lg
                                    bg-[#18181b] border border-white/10
                                    rounded-xl text-white placeholder-zinc-500
                                    focus:outline-none focus:ring-0
                                    transition-all shadow-xl
                                "
                            />
                        </div>
                    </div>

                    {/* Filter Row */}
                    <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                        <FilterDropdown
                            label="Genres"
                            options={genres}
                            selected={selectedGenres}
                            onToggle={toggleGenre}
                            onClear={() => {
                                setLimit(50);
                                setSearchParams(prev => {
                                    const p = new URLSearchParams(prev);
                                    p.delete("genre");
                                    return p;
                                }, { replace: true });
                            }}
                            color="violet"
                            align="right"
                        />

                        <FilterDropdown
                            label="Features"
                            options={categories.map(c => ({ id: c.id, label: c.description, value: c.description }))}
                            selected={selectedCategories}
                            onToggle={toggleCategory}
                            onClear={() => {
                                setLimit(50);
                                setSearchParams(prev => {
                                    const p = new URLSearchParams(prev);
                                    p.delete("category");
                                    return p;
                                }, { replace: true });
                            }}
                            color="emerald"
                            align="right"
                        />

                        {(selectedGenres.length > 0 || selectedCategories.length > 0 || searchQuery) && (
                            <button
                                onClick={() => {
                                    setLimit(50);
                                    setSearchParams(new URLSearchParams(), { replace: true });
                                }}
                                className="h-14 w-14 flex flex-shrink-0 items-center justify-center text-zinc-500 hover:text-white hover:bg-white/5 rounded-xl border border-transparent hover:border-white/10 transition-all"
                                title="Reset Filters"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        )}
                    </div>
                </div>
            </section>

            {/* Search Results (when filtering) */}
            {isFiltering && (
                <section className="px-6 py-8">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-bold text-white">
                            {searchQuery ? `Results for "${searchQuery}"` : "Filtered Games"}
                        </h2>
                        <span className="text-zinc-500">{allGames.length} games</span>
                    </div>

                    {isLoading && allGames.length === 0 ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                        </div>
                    ) : allGames.length > 0 ? (
                        <>
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                                {allGames.map((game) => (
                                    <GameCard key={game.id} game={game} size="md" showPrice />
                                ))}
                            </div>

                            {/* Load More Button */}
                            {allGames.length >= limit && (
                                <div className="mt-8 flex justify-center">
                                    <button
                                        onClick={() => setLimit(l => l + 50)}
                                        disabled={isFetching}
                                        className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {isFetching ? <div className="w-4 h-4 border-2 border-white/50 border-t-transparent rounded-full animate-spin" /> : null}
                                        Load More
                                    </button>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="text-center py-12 text-zinc-500">
                            <Gamepad2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                            <p>No games found matching your search.</p>
                        </div>
                    )}
                </section>
            )}

            {/* Discovery Sections (when not filtering) */}
            {!isFiltering && (
                <div className="space-y-10 px-6 pt-8">
                    {/* Trending */}
                    {trending.length > 0 && (
                        <GameRow
                            title="Trending Now"
                            icon={<Flame className="text-orange-500" />}
                            games={trending}
                            cardSize="md"
                        />
                    )}

                    {/* Popular */}
                    {popular.length > 0 && (
                        <GameRow
                            title="Most Popular"
                            icon={<TrendingUp className="text-green-500" />}
                            games={popular}
                            cardSize="md"
                        />
                    )}

                    {/* Top Rated */}
                    {topRated.length > 0 && (
                        <GameRow
                            title="Top Rated"
                            icon={<Star className="text-yellow-500" />}
                            games={topRated}
                            cardSize="md"
                            showPrice
                        />
                    )}

                    {/* Recently Added */}
                    {recent.length > 0 && (
                        <GameRow
                            title="Recently Added"
                            icon={<Clock className="text-blue-500" />}
                            games={recent}
                            cardSize="md"
                        />
                    )}

                    {/* Browse All Section - Now with Load More */}
                    <section className="pt-4">
                        <h2 className="text-2xl font-bold text-white mb-6">Browse All Games</h2>
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
                            {allGames.map((game) => (
                                <GameCard key={game.id} game={game} size="md" />
                            ))}
                        </div>
                        {allGames.length >= limit && (
                            <div className="mt-8 flex justify-center">
                                <button
                                    onClick={() => setLimit(l => l + 50)}
                                    disabled={isFetching}
                                    className="px-6 py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                                >
                                    {isFetching ? <div className="w-4 h-4 border-2 border-white/50 border-t-transparent rounded-full animate-spin" /> : null}
                                    Load More
                                </button>
                            </div>
                        )}
                    </section>
                </div>
            )}
        </div>
    );
}
