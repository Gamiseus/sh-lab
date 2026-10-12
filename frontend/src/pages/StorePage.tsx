import { useQuery } from "@tanstack/react-query";
import { Search, Flame, Star, Clock, TrendingUp, Gamepad2, X, Tag, LayoutGrid, List, Sparkles, Percent } from "lucide-react";
import { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { storeAPI, getImageUrl, formatPrice } from "@/lib/api";
import { HeroCarousel } from "@/components/store/HeroCarousel";
import { GameRow } from "@/components/store/GameRow";
import { GameCard } from "@/components/store/GameCard";
import { FilterDropdown } from "@/components/store/FilterDropdown";
import type { Game } from "@/lib/api";

const QUICK_GENRES = [
    "Action",
    "Adventure",
    "RPG",
    "Strategy",
    "Shooter",
    "Indie",
    "Multiplayer",
    "Simulation",
    "Casual"
];

export function StorePage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const [limit, setLimit] = useState(50);
    const [topRatedSort, setTopRatedSort] = useState<"steam_score" | "metacritic" | "igdb">("steam_score");
    const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
    const [hideStorePrices, setHideStorePrices] = useState(false);

    useEffect(() => {
        const saved = localStorage.getItem("sh_hide_store_prices");
        if (saved !== null) {
            setHideStorePrices(saved === "true");
        }
    }, []);

    // Derived state from URL
    const searchQuery = searchParams.get("search") || "";
    const selectedGenres = searchParams.getAll("genre");
    const selectedCategories = searchParams.getAll("category");
    const isDealsFilter = searchParams.get("deals") === "true";
    const activeSection = searchParams.get("section") || "";

    // Fetch discovery data
    const { data: featured = [] } = useQuery<Game[]>({
        queryKey: ["store", "featured"],
        queryFn: () => storeAPI.getFeatured(5),
    });

    // Dedicated backend deals query pulling ALL discounted titles
    const { data: deals = [] } = useQuery<Game[]>({
        queryKey: ["store", "deals"],
        queryFn: () => storeAPI.getDeals(100),
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
        queryKey: ["store", "top-rated", topRatedSort],
        queryFn: () => storeAPI.getTopRated(12, topRatedSort),
    });

    const { data: genres = [] } = useQuery<string[]>({
        queryKey: ["store", "genres"],
        queryFn: () => storeAPI.getGenres(),
    });

    const { data: categories = [] } = useQuery<{ id: number, description: string }[]>({
        queryKey: ["store", "categories"],
        queryFn: () => storeAPI.getCategories(),
    });

    // Fetch all games for browsing (respects active discount and section filters)
    const { data: allGames = [], isLoading, isFetching } = useQuery<Game[]>({
        queryKey: ["store", "games", searchQuery, selectedGenres, selectedCategories, isDealsFilter, activeSection, topRatedSort, limit],
        queryFn: () => {
            if (!searchQuery && selectedGenres.length === 0 && selectedCategories.length === 0) {
                if (isDealsFilter || activeSection === "deals") return storeAPI.getDeals(limit);
                if (activeSection === "trending") return storeAPI.getTrending(limit);
                if (activeSection === "popular") return storeAPI.getPopular(limit);
                if (activeSection === "top_rated") return storeAPI.getTopRated(limit, topRatedSort);
                if (activeSection === "recent") return storeAPI.getRecent(limit);
            }
            return storeAPI.getGames({
                search: searchQuery || undefined,
                genre: selectedGenres.length > 0 ? selectedGenres : undefined,
                category: selectedCategories.length > 0 ? selectedCategories : undefined,
                has_discount: (isDealsFilter || activeSection === "deals") ? true : undefined,
                sort_by: activeSection === "trending" ? "trending"
                    : activeSection === "popular" ? "popular"
                    : activeSection === "top_rated" ? topRatedSort
                    : activeSection === "recent" ? "recent"
                    : undefined,
                limit: limit,
            });
        },
        placeholderData: (previousData) => previousData,
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

    const clearAllFilters = () => {
        setLimit(50);
        setSearchParams(new URLSearchParams(), { replace: true });
    };

    const isFiltering = Boolean(searchQuery || selectedGenres.length > 0 || selectedCategories.length > 0 || isDealsFilter || activeSection);

    const handleOpenSectionView = (section: string) => {
        setLimit(50);
        setViewMode("list");
        setSearchParams(prev => {
            const p = new URLSearchParams(prev);
            if (section === "deals") {
                p.set("deals", "true");
                p.delete("section");
            } else {
                p.set("section", section);
                p.delete("deals");
            }
            return p;
        }, { replace: true });
    };

    const clearSection = () => {
        setLimit(50);
        setSearchParams(prev => {
            const p = new URLSearchParams(prev);
            p.delete("section");
            p.delete("deals");
            return p;
        }, { replace: true });
    };

    return (
        <div className="min-h-screen pb-16 space-y-8 animate-in fade-in duration-300 xl:pr-64">
            {/* Unified Max-Width Canvas */}
            <div className="w-full max-w-[1520px] mx-auto px-4 sm:px-6 lg:px-8 space-y-8">

                {/* Hero Section with smooth collapse/expand transition */}
                <div
                    className={`overflow-hidden transition-all duration-500 ease-in-out ${
                        isFiltering ? "max-h-0 opacity-0 pointer-events-none" : "max-h-[640px] opacity-100"
                    }`}
                >
                    <section className="pt-4">
                        <HeroCarousel games={featured} hidePrice={hideStorePrices} />
                    </section>

                    {/* Popular Genre Quick-Browse Pills */}
                    <div className="pt-6">
                        <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide py-1">
                            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5 mr-1 flex-shrink-0">
                                <Tag className="w-3.5 h-3.5" />
                                Browse by:
                            </span>
                            {QUICK_GENRES.map((genre) => {
                                const isSelected = selectedGenres.includes(genre);
                                return (
                                    <button
                                        key={genre}
                                        onClick={() => toggleGenre(genre)}
                                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 ${
                                            isSelected
                                                ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                                                : "bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-white/10"
                                        }`}
                                    >
                                        {genre}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Search & Filters Sticky Bar */}
                <section className="sticky top-0 z-20 py-4 bg-background/95 backdrop-blur-xl border-y border-white/5 shadow-xl">
                    <div className="space-y-3">
                        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
                            {/* Search Input */}
                            <div className="relative flex-1 group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 group-focus-within:text-violet-400 transition-colors" />
                                <input
                                    type="text"
                                    placeholder="Search games by title, developer, publisher, or tags..."
                                    value={searchQuery}
                                    onChange={(e) => handleSearchChange(e.target.value)}
                                    className="w-full pl-11 pr-10 py-2.5 bg-zinc-900/90 border border-white/10 rounded-xl text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500 transition-all shadow-inner"
                                />
                                {searchQuery && (
                                    <button
                                        onClick={() => handleSearchChange("")}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-zinc-400 hover:text-white"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                )}
                            </div>

                            {/* Filter Dropdowns */}
                            <div className="flex items-center gap-2.5 flex-wrap">
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

                                {isFiltering && (
                                    <button
                                        onClick={clearAllFilters}
                                        className="px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5"
                                        title="Reset all filters"
                                    >
                                        <X className="w-3.5 h-3.5" />
                                        Clear Filters
                                    </button>
                                )}
                            </div>
                        </div>

                        {/* Active Filter Chips */}
                        {isFiltering && (
                            <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
                                <span className="text-zinc-500 font-medium mr-1">Active:</span>

                                {(isDealsFilter || activeSection === "deals") && (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-600/20 border border-emerald-500/30 text-emerald-300 font-semibold">
                                        <Percent className="w-3.5 h-3.5" />
                                        Special Offers (-%)
                                        <button
                                            onClick={clearSection}
                                            className="hover:text-white ml-0.5"
                                            title="Clear deals filter"
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </span>
                                )}

                                {activeSection && activeSection !== "deals" && (
                                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-300 font-semibold">
                                        {activeSection === "trending" && <Flame className="w-3.5 h-3.5 text-orange-400" />}
                                        {activeSection === "popular" && <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />}
                                        {activeSection === "top_rated" && <Star className="w-3.5 h-3.5 text-yellow-400 fill-current" />}
                                        {activeSection === "recent" && <Clock className="w-3.5 h-3.5 text-blue-400" />}
                                        {activeSection === "trending" ? "Trending Now"
                                            : activeSection === "popular" ? "Most Popular"
                                            : activeSection === "top_rated" ? `Top Rated (${topRatedSort === "steam_score" ? "Steam" : topRatedSort === "metacritic" ? "Metacritic" : "IGDB"})`
                                            : "Recently Added"}
                                        <button
                                            onClick={clearSection}
                                            className="hover:text-white ml-0.5"
                                            title="Clear section filter"
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </span>
                                )}

                                {selectedGenres.map(g => (
                                    <span key={g} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-violet-600/20 border border-violet-500/30 text-violet-300">
                                        {g}
                                        <button onClick={() => toggleGenre(g)} className="hover:text-white">
                                            <X className="w-3 h-3" />
                                        </button>
                                    </span>
                                ))}

                                {selectedCategories.map(c => (
                                    <span key={c} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-600/20 border border-emerald-500/30 text-emerald-300">
                                        {c}
                                        <button onClick={() => toggleCategory(c)} className="hover:text-white">
                                            <X className="w-3 h-3" />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                </section>

                {/* Filtered Search / Deals Results View */}
                {isFiltering && (
                    <section className="space-y-6">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-white/5 gap-3">
                            <div>
                                <h2 className="text-2xl font-extrabold text-white flex items-center gap-2">
                                    {(isDealsFilter || activeSection === "deals") ? (
                                        <>
                                            <Percent className="w-6 h-6 text-emerald-400" />
                                            Special Offers & Discounts
                                        </>
                                    ) : activeSection === "trending" ? (
                                        <>
                                            <Flame className="w-6 h-6 text-orange-400" />
                                            Trending Games
                                        </>
                                    ) : activeSection === "popular" ? (
                                        <>
                                            <TrendingUp className="w-6 h-6 text-emerald-400" />
                                            Most Popular Games
                                        </>
                                    ) : activeSection === "top_rated" ? (
                                        <>
                                            <Star className="w-6 h-6 text-yellow-400 fill-current" />
                                            Top Rated Games
                                        </>
                                    ) : activeSection === "recent" ? (
                                        <>
                                            <Clock className="w-6 h-6 text-blue-400" />
                                            Recently Added to Store
                                        </>
                                    ) : searchQuery ? (
                                        `Results for "${searchQuery}"`
                                    ) : (
                                        "Filtered Games"
                                    )}
                                </h2>
                                <p className="text-xs text-zinc-400 mt-0.5">Found {allGames.length} matching titles</p>
                            </div>

                            <div className="flex items-center gap-2.5">
                                {activeSection === "top_rated" && (
                                    <div className="flex items-center gap-1.5 bg-zinc-900/90 p-1 rounded-xl border border-white/10 text-xs">
                                        <span className="text-zinc-500 px-1.5 font-medium hidden md:inline">Sort:</span>
                                        <button
                                            type="button"
                                            onClick={() => setTopRatedSort("steam_score")}
                                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                                topRatedSort === "steam_score"
                                                    ? "bg-violet-600 text-white shadow-sm"
                                                    : "text-zinc-400 hover:text-white"
                                            }`}
                                        >
                                            Steam Score
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setTopRatedSort("metacritic")}
                                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                                topRatedSort === "metacritic"
                                                    ? "bg-emerald-600 text-white shadow-sm"
                                                    : "text-zinc-400 hover:text-white"
                                            }`}
                                        >
                                            Metacritic
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setTopRatedSort("igdb")}
                                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                                topRatedSort === "igdb"
                                                    ? "bg-amber-600 text-white shadow-sm"
                                                    : "text-zinc-400 hover:text-white"
                                            }`}
                                        >
                                            IGDB
                                        </button>
                                    </div>
                                )}

                                {/* View Switcher */}
                                <div className="flex items-center gap-1 bg-zinc-900 p-1 rounded-xl border border-white/10">
                                <button
                                    onClick={() => setViewMode("grid")}
                                    className={`p-1.5 rounded-lg transition-colors ${
                                        viewMode === "grid" ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-white"
                                    }`}
                                    title="Grid View"
                                >
                                    <LayoutGrid className="w-4 h-4" />
                                </button>
                                <button
                                    onClick={() => setViewMode("list")}
                                    className={`p-1.5 rounded-lg transition-colors ${
                                        viewMode === "list" ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-white"
                                    }`}
                                    title="Detailed List View"
                                >
                                    <List className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    </div>

                        {isLoading && allGames.length === 0 ? (
                            <div className="flex items-center justify-center py-20">
                                <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                            </div>
                        ) : allGames.length > 0 ? (
                            <>
                                {viewMode === "grid" ? (
                                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                                        {allGames.map((game) => (
                                            <GameCard key={game.id} game={game} size="md" showPrice />
                                        ))}
                                    </div>
                                ) : (
                                    /* Vertically Expanded List View with Descriptions */
                                    <div className="space-y-3">
                                        {allGames.map((game) => {
                                            const hasDiscount = Boolean(game.discount_percent && game.discount_percent > 0);
                                            const originalPrice = hasDiscount && game.price_cents
                                                ? Math.round(game.price_cents / (1 - (game.discount_percent! / 100)))
                                                : null;

                                            return (
                                                <Link
                                                    key={game.id}
                                                    to={`/games/${game.id}`}
                                                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 sm:p-5 rounded-2xl bg-zinc-900/60 hover:bg-zinc-900/95 border border-white/10 hover:border-violet-500/50 shadow-md hover:shadow-xl hover:shadow-violet-600/10 transition-all duration-200 group"
                                                >
                                                    {/* Left: Thumbnail & Info */}
                                                    <div className="flex items-start sm:items-center gap-4 min-w-0 flex-1">
                                                        {/* Artwork Thumbnail */}
                                                        <div className="relative w-36 sm:w-48 md:w-56 aspect-[16/9] rounded-xl overflow-hidden flex-shrink-0 bg-zinc-950 ring-1 ring-white/10 group-hover:ring-violet-500/40 transition-all">
                                                            <img
                                                                src={getImageUrl(game.header_image || game.cover_url)}
                                                                alt={game.title}
                                                                className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                                                                loading="lazy"
                                                            />
                                                            {hasDiscount && (
                                                                <div className="absolute top-2 left-2 px-2 py-0.5 bg-emerald-500 text-white text-[11px] font-extrabold rounded-md shadow-md">
                                                                    -{game.discount_percent}%
                                                                </div>
                                                            )}
                                                        </div>

                                                        {/* Info & Description */}
                                                        <div className="min-w-0 flex-1 space-y-1.5">
                                                            <h3 className="font-extrabold text-base sm:text-lg text-white group-hover:text-violet-300 transition-colors truncate drop-shadow-sm">
                                                                {game.title}
                                                            </h3>

                                                            {/* Description Snippet */}
                                                            <p className="text-xs sm:text-sm text-zinc-400 line-clamp-2 leading-relaxed font-normal">
                                                                {game.short_description || game.description || "Discover this game in the store catalog with authentic achievements, reviews, and launch support."}
                                                            </p>

                                                            {/* Genres / Tags */}
                                                            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                                                                {game.genres?.slice(0, 4).map((g) => (
                                                                    <span key={g} className="text-[11px] px-2 py-0.5 rounded-md bg-white/5 border border-white/5 text-zinc-400">
                                                                        {g}
                                                                    </span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Right: Scores & Pricing */}
                                                    <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2 sm:gap-1.5 flex-shrink-0 sm:min-w-[130px] sm:pl-4 sm:border-l sm:border-white/5 text-right">
                                                        {game.steam_review_percent !== undefined ? (
                                                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-blue-600/15 border border-blue-500/30 text-blue-400 font-semibold text-xs">
                                                                <Sparkles className="w-3 h-3 fill-current" />
                                                                {game.steam_review_percent}% Positive
                                                            </span>
                                                        ) : game.metacritic_score ? (
                                                            <span className="inline-flex px-2 py-0.5 rounded-md bg-emerald-600/20 text-emerald-400 font-bold text-xs border border-emerald-500/30">
                                                                {game.metacritic_score} Metascore
                                                            </span>
                                                        ) : null}

                                                        <div className="space-y-0.5">
                                                            {originalPrice && (
                                                                <div className="text-xs text-zinc-500 line-through">
                                                                    {formatPrice(originalPrice)}
                                                                </div>
                                                            )}
                                                            <div className="font-extrabold text-white text-base sm:text-lg">
                                                                {formatPrice(game.price_cents)}
                                                            </div>
                                                        </div>

                                                        <span className="hidden sm:inline-flex items-center gap-1 text-xs font-semibold text-violet-400 group-hover:translate-x-0.5 transition-transform mt-0.5">
                                                            View Game →
                                                        </span>
                                                    </div>
                                                </Link>
                                            );
                                        })}
                                    </div>
                                )}

                                {/* Load More Button */}
                                {allGames.length >= limit && (
                                    <div className="pt-8 flex justify-center">
                                        <button
                                            onClick={() => setLimit(l => l + 50)}
                                            disabled={isFetching}
                                            className="px-6 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2 border border-white/10 shadow-lg"
                                        >
                                            {isFetching ? <div className="w-4 h-4 border-2 border-white/50 border-t-transparent rounded-full animate-spin" /> : null}
                                            Load More Games
                                        </button>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="text-center py-20 px-6 rounded-2xl bg-zinc-900/30 border border-white/5 space-y-3 max-w-md mx-auto">
                                <Gamepad2 className="w-12 h-12 mx-auto text-zinc-600" />
                                <h3 className="text-lg font-bold text-white">No games found</h3>
                                <p className="text-xs text-zinc-400">
                                    Try adjusting your keywords or clearing selected genres to see more titles.
                                </p>
                                <button
                                    onClick={clearAllFilters}
                                    className="text-xs text-violet-400 hover:text-violet-300 underline font-semibold"
                                >
                                    Reset Search & Filters
                                </button>
                            </div>
                        )}
                    </section>
                )}

                {/* Standard Discovery Sections (when not actively filtering) */}
                {!isFiltering && (
                    <div className="space-y-12">
                        {/* Special Deals & Discounts Row (Clicking title switches to full deals view) */}
                        {deals.length > 0 && (
                            <GameRow
                                title="Special Offers & Discounts"
                                icon={<Percent className="text-emerald-400 w-5 h-5" />}
                                games={deals.slice(0, 12)}
                                cardSize="md"
                                showPrice={!hideStorePrices}
                                onTitleClick={() => handleOpenSectionView("deals")}
                            />
                        )}

                        {/* Trending Row */}
                        {trending.length > 0 && (
                            <GameRow
                                title="Trending Now"
                                icon={<Flame className="text-orange-500 w-5 h-5" />}
                                games={trending}
                                cardSize="md"
                                showPrice={!hideStorePrices}
                                onTitleClick={() => handleOpenSectionView("trending")}
                            />
                        )}

                        {/* Most Popular */}
                        {popular.length > 0 && (
                            <GameRow
                                title="Most Popular"
                                icon={<TrendingUp className="text-emerald-500 w-5 h-5" />}
                                games={popular}
                                cardSize="md"
                                showPrice={!hideStorePrices}
                                onTitleClick={() => handleOpenSectionView("popular")}
                            />
                        )}

                        {/* Top Rated Row with Sort Metric Selector */}
                        {topRated.length > 0 && (
                            <GameRow
                                title="Top Rated Games"
                                icon={<Star className="text-yellow-400 w-5 h-5 fill-current" />}
                                games={topRated}
                                cardSize="md"
                                showPrice={!hideStorePrices}
                                onTitleClick={() => handleOpenSectionView("top_rated")}
                                headerExtra={
                                    <div className="flex items-center gap-1.5 bg-zinc-900/90 p-1 rounded-xl border border-white/10 text-xs">
                                        <span className="text-zinc-500 px-1.5 font-medium hidden md:inline">Sort:</span>
                                        <button
                                            type="button"
                                            onClick={() => setTopRatedSort("steam_score")}
                                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                                topRatedSort === "steam_score"
                                                    ? "bg-violet-600 text-white shadow-sm"
                                                    : "text-zinc-400 hover:text-white"
                                            }`}
                                        >
                                            Steam Score
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setTopRatedSort("metacritic")}
                                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                                topRatedSort === "metacritic"
                                                    ? "bg-emerald-600 text-white shadow-sm"
                                                    : "text-zinc-400 hover:text-white"
                                            }`}
                                        >
                                            Metacritic
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setTopRatedSort("igdb")}
                                            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                                                topRatedSort === "igdb"
                                                    ? "bg-amber-600 text-white shadow-sm"
                                                    : "text-zinc-400 hover:text-white"
                                            }`}
                                        >
                                            IGDB
                                        </button>
                                    </div>
                                }
                            />
                        )}

                        {/* Recently Added */}
                        {recent.length > 0 && (
                            <GameRow
                                title="Recently Added to Store"
                                icon={<Clock className="text-blue-400 w-5 h-5" />}
                                games={recent}
                                cardSize="md"
                                showPrice={!hideStorePrices}
                                onTitleClick={() => handleOpenSectionView("recent")}
                            />
                        )}

                        {/* Browse All Catalog Section */}
                        <section className="pt-6 border-t border-white/10 space-y-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-2xl font-extrabold text-white flex items-center gap-2">
                                        <Sparkles className="w-5 h-5 text-violet-400" />
                                        Browse Complete Catalog
                                    </h2>
                                    <p className="text-xs text-zinc-400 mt-1">Explore all indexed titles across available genres.</p>
                                </div>

                                {/* View Switcher */}
                                <div className="flex items-center gap-1 bg-zinc-900 p-1 rounded-xl border border-white/10">
                                    <button
                                        onClick={() => setViewMode("grid")}
                                        className={`p-1.5 rounded-lg transition-colors ${
                                            viewMode === "grid" ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-white"
                                        }`}
                                        title="Grid View"
                                    >
                                        <LayoutGrid className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => setViewMode("list")}
                                        className={`p-1.5 rounded-lg transition-colors ${
                                            viewMode === "list" ? "bg-violet-600 text-white" : "text-zinc-400 hover:text-white"
                                        }`}
                                        title="Detailed List View"
                                    >
                                        <List className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>

                            {viewMode === "grid" ? (
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                                    {allGames.map((game) => (
                                        <GameCard key={game.id} game={game} size="md" showPrice={!hideStorePrices} />
                                    ))}
                                </div>
                            ) : (
                                /* Vertically Expanded List View */
                                <div className="space-y-3">
                                    {allGames.map((game) => {
                                        const hasDiscount = Boolean(game.discount_percent && game.discount_percent > 0);
                                        const originalPrice = hasDiscount && game.price_cents
                                            ? Math.round(game.price_cents / (1 - (game.discount_percent! / 100)))
                                            : null;

                                        return (
                                            <Link
                                                key={game.id}
                                                to={`/games/${game.id}`}
                                                className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 sm:p-5 rounded-2xl bg-zinc-900/60 hover:bg-zinc-900/95 border border-white/10 hover:border-violet-500/50 shadow-md hover:shadow-xl hover:shadow-violet-600/10 transition-all duration-200 group"
                                            >
                                                {/* Left: Thumbnail & Info */}
                                                <div className="flex items-start sm:items-center gap-4 min-w-0 flex-1">
                                                    <div className="relative w-36 sm:w-48 md:w-56 aspect-[16/9] rounded-xl overflow-hidden flex-shrink-0 bg-zinc-950 ring-1 ring-white/10 group-hover:ring-violet-500/40 transition-all">
                                                        <img
                                                            src={getImageUrl(game.header_image || game.cover_url)}
                                                            alt={game.title}
                                                            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                                                            loading="lazy"
                                                        />
                                                        {hasDiscount && !hideStorePrices && (
                                                            <div className="absolute top-2 left-2 px-2 py-0.5 bg-emerald-500 text-white text-[11px] font-extrabold rounded-md shadow-md">
                                                                -{game.discount_percent}%
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div className="min-w-0 flex-1 space-y-1.5">
                                                        <h3 className="font-extrabold text-base sm:text-lg text-white group-hover:text-violet-300 transition-colors truncate drop-shadow-sm">
                                                            {game.title}
                                                        </h3>
                                                        <p className="text-xs sm:text-sm text-zinc-400 line-clamp-2 leading-relaxed font-normal">
                                                            {game.short_description || game.description || "Discover this game in the store catalog with authentic achievements, reviews, and launch support."}
                                                        </p>
                                                        <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                                                            {game.genres?.slice(0, 4).map((g) => (
                                                                <span key={g} className="text-[11px] px-2 py-0.5 rounded-md bg-white/5 border border-white/5 text-zinc-400">
                                                                    {g}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Right: Scores & Pricing */}
                                                <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center gap-2 sm:gap-1.5 flex-shrink-0 sm:min-w-[130px] sm:pl-4 sm:border-l sm:border-white/5 text-right">
                                                    {game.steam_review_percent !== undefined ? (
                                                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-blue-600/15 border border-blue-500/30 text-blue-400 font-semibold text-xs">
                                                            <Sparkles className="w-3 h-3 fill-current" />
                                                            {game.steam_review_percent}% Positive
                                                        </span>
                                                    ) : game.metacritic_score ? (
                                                        <span className="inline-flex px-2 py-0.5 rounded-md bg-emerald-600/20 text-emerald-400 font-bold text-xs border border-emerald-500/30">
                                                            {game.metacritic_score} Metascore
                                                        </span>
                                                    ) : null}

                                                    {!hideStorePrices && (
                                                        <div className="space-y-0.5">
                                                            {originalPrice && (
                                                                <div className="text-xs text-zinc-500 line-through">
                                                                    {formatPrice(originalPrice)}
                                                                </div>
                                                            )}
                                                            <div className="font-extrabold text-white text-base sm:text-lg">
                                                                {formatPrice(game.price_cents)}
                                                            </div>
                                                        </div>
                                                    )}

                                                    <span className="hidden sm:inline-flex items-center gap-1 text-xs font-semibold text-violet-400 group-hover:translate-x-0.5 transition-transform mt-0.5">
                                                        View Game →
                                                    </span>
                                                </div>
                                            </Link>
                                        );
                                    })}
                                </div>
                            )}

                            {allGames.length >= limit && (
                                <div className="mt-8 flex justify-center">
                                    <button
                                        onClick={() => setLimit(l => l + 50)}
                                        disabled={isFetching}
                                        className="px-6 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-2 border border-white/10 shadow-lg"
                                    >
                                        {isFetching ? <div className="w-4 h-4 border-2 border-white/50 border-t-transparent rounded-full animate-spin" /> : null}
                                        Load More Games
                                    </button>
                                </div>
                            )}
                        </section>
                    </div>
                )}
            </div>
        </div>
    );
}
