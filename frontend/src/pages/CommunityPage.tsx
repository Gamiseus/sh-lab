import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Users, Loader2, TrendingUp, Clock, SortAsc } from "lucide-react";
import { communityAPI, profilesAPI } from "@/lib/api";
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
        <div className="p-6 space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white">Community</h1>
                    <p className="text-zinc-400 mt-1">Discover and connect with other players</p>
                </div>
            </div>

            {/* Own Profile (Featured) */}
            {myProfile && (
                <div className="space-y-2">
                    <h2 className="text-sm font-medium text-zinc-500 uppercase tracking-wider">
                        Your Profile
                    </h2>
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

            {/* Search and Filters */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                {/* Search */}
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search users..."
                        className="w-full pl-10 pr-4 py-2.5 bg-zinc-900/50 border border-white/10 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500"
                    />
                </div>

                {/* Sort */}
                <div className="flex items-center gap-2">
                    <span className="text-sm text-zinc-500">Sort by:</span>
                    <div className="flex gap-1 bg-zinc-900/50 border border-white/10 rounded-lg p-1">
                        {[
                            { value: "recent", icon: Clock, label: "Recent" },
                            { value: "playtime", icon: TrendingUp, label: "Playtime" },
                            { value: "games", icon: Users, label: "Games" },
                            { value: "name", icon: SortAsc, label: "Name" },
                        ].map(({ value, icon: Icon, label }) => (
                            <button
                                key={value}
                                onClick={() => setSortBy(value as SortOption)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors ${sortBy === value
                                    ? "bg-violet-600 text-white"
                                    : "text-zinc-400 hover:text-white"
                                    }`}
                            >
                                <Icon className="w-4 h-4" />
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Users Grid */}
            {isLoading || isSearching ? (
                <div className="flex items-center justify-center py-16">
                    <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
                </div>
            ) : displayUsers && displayUsers.length > 0 ? (
                <>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {displayUsers
                            .filter((u) => u.id !== user?.id) // Don't show own profile in grid
                            .map((u) => (
                                <UserCard key={u.id} user={u} />
                            ))}
                    </div>

                    {/* Pagination */}
                    {!searchQuery && totalPages > 1 && (
                        <div className="flex items-center justify-center gap-2 pt-4">
                            <button
                                onClick={() => setPage((p) => Math.max(1, p - 1))}
                                disabled={page === 1}
                                className="px-4 py-2 text-sm text-zinc-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Previous
                            </button>
                            <span className="text-sm text-zinc-500">
                                Page {page} of {totalPages}
                            </span>
                            <button
                                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                disabled={page === totalPages}
                                className="px-4 py-2 text-sm text-zinc-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Next
                            </button>
                        </div>
                    )}
                </>
            ) : (
                <div className="text-center py-16 text-zinc-500">
                    <Users className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">
                        {searchQuery ? "No users found" : "No public profiles yet"}
                    </p>
                </div>
            )}
        </div>
    );
}
