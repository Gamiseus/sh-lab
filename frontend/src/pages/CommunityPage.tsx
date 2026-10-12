import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Users, Loader2, TrendingUp, Clock, SortAsc, Sparkles, X } from "lucide-react";
import { communityAPI, profilesAPI, UserCardData } from "@/lib/api";
import { UserCard } from "@/components/community/UserCard";
import { useAuth } from "@/contexts/AuthContext";

type SortOption = "recent" | "playtime" | "games" | "name";

export function CommunityPage() {
    const { user } = useAuth();
    const [searchQuery, setSearchQuery] = useState("");
    const [sortBy, setSortBy] = useState<SortOption>("recent");
    const [page, setPage] = useState(1);

    // Fetch own profile for the featured card
    const { data: myProfile } = useQuery({
        queryKey: ["my-profile"],
        queryFn: profilesAPI.getMyProfile,
        enabled: !!user,
    });

    // Fetch community users
    const { data: communityData, isLoading } = useQuery({
        queryKey: ["community-users", page, sortBy],
        queryFn: () => communityAPI.listUsers(page, sortBy),
    });

    // Search users
    const { data: searchResults, isLoading: isSearching } = useQuery({
        queryKey: ["user-search", searchQuery],
        queryFn: () => communityAPI.searchUsers(searchQuery),
        enabled: searchQuery.length >= 2,
    });

    const displayUsers = searchQuery.length >= 2 ? searchResults : communityData?.users;
    const totalPages = communityData ? Math.ceil(communityData.total / communityData.per_page) : 1;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
                        <Users className="w-8 h-8 text-violet-400" />
                        Community Hub
                    </h1>
                    <p className="text-zinc-400 mt-1 text-sm">
                        Discover fellow players, explore shared libraries, and build your gaming network.
                    </p>
                </div>
            </div>

            {/* Own Profile (Featured) */}
            {myProfile && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xs font-bold uppercase tracking-wider text-violet-400 flex items-center gap-2">
                            <Sparkles className="w-3.5 h-3.5 fill-current" />
                            Your Gamer Identity
                        </h2>
                    </div>
                    <UserCard
                        user={{
                            id: myProfile.id,
                            username: myProfile.username,
                            display_name: myProfile.display_name,
                            avatar_url: myProfile.avatar_url,
                            games_count: myProfile.stats.games_count,
                            total_playtime_hours: Math.round(
                                myProfile.stats.total_playtime_minutes / 60
                            ),
                            joined_date: myProfile.stats.joined_date,
                        }}
                        size="large"
                    />
                </div>
            )}

            {/* Search and Filters Toolbar */}
            <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 p-4 rounded-2xl bg-zinc-900/60 border border-white/10 shadow-lg">
                {/* Search */}
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search players by username or display name..."
                        className="w-full pl-10 pr-9 py-2 bg-zinc-950/80 border border-white/10 rounded-xl text-sm text-white placeholder-zinc-500 focus:border-violet-500 focus:outline-none transition-colors"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery("")}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white p-1"
                        >
                            <X className="w-3.5 h-3.5" />
                        </button>
                    )}
                </div>

                {/* Sort Option Pills */}
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 hidden sm:inline">Sort:</span>
                    <div className="flex items-center gap-1 bg-zinc-950/80 border border-white/10 rounded-xl p-1">
                        {[
                            { value: "recent", icon: Clock, label: "Recent" },
                            { value: "playtime", icon: TrendingUp, label: "Top Playtime" },
                            { value: "games", icon: Users, label: "Most Games" },
                            { value: "name", icon: SortAsc, label: "Alphabetical" },
                        ].map(({ value, icon: Icon, label }) => (
                            <button
                                key={value}
                                onClick={() => setSortBy(value as SortOption)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                                    sortBy === value
                                        ? "bg-violet-600 text-white shadow-md shadow-violet-600/30"
                                        : "text-zinc-400 hover:text-white hover:bg-white/5"
                                }`}
                            >
                                <Icon className="w-3.5 h-3.5" />
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Users Grid */}
            {isLoading || isSearching ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                    <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
                    <p className="text-sm text-zinc-500">Loading community members...</p>
                </div>
            ) : displayUsers && displayUsers.length > 0 ? (
                <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {displayUsers
                            .filter((u: UserCardData) => u.id !== user?.id)
                            .map((u: UserCardData) => (
                                <UserCard key={u.id} user={u} />
                            ))}
                    </div>

                    {/* Pagination */}
                    {!searchQuery && totalPages > 1 && (
                        <div className="flex items-center justify-center gap-3 pt-6">
                            <button
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="px-4 py-2 text-xs font-semibold text-zinc-300 bg-zinc-900 border border-white/10 rounded-lg hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                            >
                                Previous
                            </button>
                            <span className="text-xs text-zinc-400 font-medium px-2">
                                Page <span className="text-white font-bold">{page}</span> of {totalPages}
                            </span>
                            <button
                                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="px-4 py-2 text-xs font-semibold text-zinc-300 bg-zinc-900 border border-white/10 rounded-lg hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                            >
                                Next
                            </button>
                        </div>
                    )}
                </>
            ) : (
                <div className="text-center py-20 px-6 rounded-2xl bg-zinc-900/40 border border-white/5 space-y-3 max-w-md mx-auto">
                    <div className="w-14 h-14 rounded-2xl bg-zinc-800/80 border border-white/10 flex items-center justify-center mx-auto text-zinc-500">
                        <Users className="w-7 h-7" />
                    </div>
                    <h3 className="text-lg font-bold text-white">
                        {searchQuery ? `No players matching "${searchQuery}"` : "No public profiles found"}
                    </h3>
                    <p className="text-xs text-zinc-400">
                        {searchQuery
                            ? "Try searching for a different username or clear the search filter."
                            : "As users register and set their profile visibility to public, they will appear here."}
                    </p>
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery("")}
                            className="text-xs text-violet-400 hover:text-violet-300 underline font-medium"
                        >
                            Reset player search
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
