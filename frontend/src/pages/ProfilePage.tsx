import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
    User,
    Calendar,
    Clock,
    Gamepad2,
    Star,
    Edit2,
    UserPlus,
    UserCheck,
    Loader2,
    Lock,
    Users,
    Sparkles,
    ArrowUpRight,
} from "lucide-react";
import {
    profilesAPI,
    friendsAPI,
    formatPlaytime,
    getImageUrl,
} from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { ProfileEditModal } from "@/components/profile/ProfileEditModal";
import { FavoritesManager } from "@/components/profile/FavoritesManager";

export function ProfilePage() {
    const { userId } = useParams<{ userId: string }>();
    const { user: currentUser } = useAuth();
    const queryClient = useQueryClient();
    const [showEditModal, setShowEditModal] = useState(false);
    const [showFavoritesManager, setShowFavoritesManager] = useState(false);

    const isOwnProfile = !userId || (currentUser && parseInt(userId) === currentUser.id);
    const profileId = userId ? parseInt(userId) : currentUser?.id;

    // Fetch profile
    const { data: profile, isLoading: profileLoading, error: profileError } = useQuery({
        queryKey: ["profile", profileId],
        queryFn: () =>
            isOwnProfile ? profilesAPI.getMyProfile() : profilesAPI.getProfile(profileId!),
        enabled: !!profileId,
    });

    // Fetch recent activity
    const { data: recentActivity } = useQuery({
        queryKey: ["recent-activity", profileId],
        queryFn: () => profilesAPI.getRecentActivity(profileId!, 6),
        enabled: !!profileId && (isOwnProfile || profile?.privacy_level === "public"),
    });

    // Fetch user reviews
    const { data: reviews } = useQuery({
        queryKey: ["user-reviews", profileId],
        queryFn: () => profilesAPI.getUserReviews(profileId!, 6),
        enabled: !!profileId && (isOwnProfile || profile?.privacy_level === "public"),
    });

    // Friend request mutation
    const sendRequestMutation = useMutation({
        mutationFn: (id: number) => friendsAPI.addFriend(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["profile", profileId] });
        },
    });

    // Update favorites mutation
    const updateFavoritesMutation = useMutation({
        mutationFn: (ids: number[]) => profilesAPI.updateFavorites(ids),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["profile", profileId] });
            setShowFavoritesManager(false);
        },
    });

    if (profileLoading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[500px] gap-3">
                <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
                <p className="text-sm text-zinc-500">Loading player profile...</p>
            </div>
        );
    }

    if (profileError || !profile) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[500px] text-zinc-500 space-y-3">
                <div className="w-16 h-16 rounded-2xl bg-zinc-900 border border-white/10 flex items-center justify-center">
                    <User className="w-8 h-8 text-zinc-600" />
                </div>
                <h2 className="text-xl font-bold text-white">Player Not Found</h2>
                <p className="text-sm text-zinc-400">The requested profile does not exist or may have been removed.</p>
                <Link
                    to="/community"
                    className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-semibold transition-colors mt-2"
                >
                    Back to Community
                </Link>
            </div>
        );
    }

    const isPrivate = profile.privacy_level === "private" && !isOwnProfile;

    return (
        <div className="min-h-screen pb-16 animate-in fade-in duration-300">
            {/* Header Banner */}
            <div
                className="h-64 sm:h-80 md:h-96 relative bg-gradient-to-br from-violet-900/40 via-purple-950/20 to-zinc-950"
                style={
                    profile.background_url
                        ? {
                            backgroundImage: `url(${getImageUrl(profile.background_url)})`,
                            backgroundSize: "cover",
                            backgroundPosition: "center",
                        }
                        : undefined
                }
            >
                {/* Vignettes for smooth content blending */}
                <div className="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent" />
                <div className="absolute inset-0 bg-black/30 backdrop-blur-[1px]" />
            </div>

            {/* Profile Identity Bar */}
            <div className="max-w-6xl mx-auto px-6 -mt-20 md:-mt-24 relative z-10 space-y-6">
                <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-6 pb-6 border-b border-white/10">
                    {/* Avatar & Player Names */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-end gap-5">
                        <div className="relative group">
                            {profile.avatar_url ? (
                                <img
                                    src={getImageUrl(profile.avatar_url)}
                                    alt={profile.display_name || profile.username}
                                    className="w-28 h-28 sm:w-36 sm:h-36 rounded-2xl border-4 border-background object-cover shadow-2xl ring-2 ring-violet-500/40"
                                />
                            ) : (
                                <div className="w-28 h-28 sm:w-36 sm:h-36 rounded-2xl border-4 border-background bg-gradient-to-br from-violet-600 via-indigo-600 to-purple-600 flex items-center justify-center text-4xl sm:text-5xl font-extrabold text-white shadow-2xl ring-2 ring-violet-500/40">
                                    {(profile.display_name || profile.username)[0].toUpperCase()}
                                </div>
                            )}

                            {/* Privacy Badge */}
                            {profile.privacy_level !== "public" && (
                                <div
                                    className="absolute -bottom-2 -right-2 p-1.5 bg-zinc-900 rounded-xl border border-white/10 shadow-lg"
                                    title={`Visibility: ${profile.privacy_level}`}
                                >
                                    {profile.privacy_level === "friends" ? (
                                        <Users className="w-4 h-4 text-blue-400" />
                                    ) : (
                                        <Lock className="w-4 h-4 text-amber-400" />
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="space-y-1">
                            <div className="flex items-center gap-2.5 flex-wrap">
                                <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
                                    {profile.display_name || profile.username}
                                </h1>
                                {currentUser?.is_admin && isOwnProfile && (
                                    <span className="px-2 py-0.5 rounded-md bg-violet-600/20 border border-violet-500/30 text-violet-400 text-xs font-bold uppercase tracking-wider">
                                        Admin
                                    </span>
                                )}
                            </div>
                            <p className="text-sm sm:text-base text-zinc-400">@{profile.username}</p>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-3 w-full sm:w-auto">
                        {isOwnProfile ? (
                            <button
                                onClick={() => setShowEditModal(true)}
                                className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl text-sm font-semibold transition-all border border-white/10 shadow-md"
                            >
                                <Edit2 className="w-4 h-4 text-violet-400" />
                                Edit Profile
                            </button>
                        ) : (
                            <>
                                {profile.friend_status === "accepted" ? (
                                    <span className="flex items-center gap-2 px-4 py-2.5 bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 rounded-xl text-sm font-semibold">
                                        <UserCheck className="w-4 h-4" />
                                        Friends
                                    </span>
                                ) : profile.friend_status === "pending" ? (
                                    <span className="flex items-center gap-2 px-4 py-2.5 bg-amber-500/15 border border-amber-500/30 text-amber-400 rounded-xl text-sm font-semibold">
                                        <Clock className="w-4 h-4" />
                                        Request Pending
                                    </span>
                                ) : profile.friend_status === "sent" ? (
                                    <span className="flex items-center gap-2 px-4 py-2.5 bg-blue-500/15 border border-blue-500/30 text-blue-400 rounded-xl text-sm font-semibold">
                                        <Clock className="w-4 h-4" />
                                        Request Sent
                                    </span>
                                ) : (
                                    <button
                                        onClick={() => sendRequestMutation.mutate(profile.id)}
                                        disabled={sendRequestMutation.isPending}
                                        className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg shadow-violet-600/25 disabled:opacity-50"
                                    >
                                        {sendRequestMutation.isPending ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <UserPlus className="w-4 h-4" />
                                        )}
                                        Add Friend
                                    </button>
                                )}
                            </>
                        )}
                    </div>
                </div>

                {/* Bio Snippet */}
                {profile.bio && !isPrivate && (
                    <div className="p-4 rounded-xl bg-zinc-900/50 border border-white/5 text-sm sm:text-base text-zinc-300 leading-relaxed max-w-3xl">
                        {profile.bio}
                    </div>
                )}

                {/* Stats Grid */}
                {!isPrivate && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                        <div className="p-4 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center gap-3.5">
                            <div className="p-2.5 rounded-lg bg-violet-600/10 text-violet-400 border border-violet-500/20">
                                <Gamepad2 className="w-5 h-5" />
                            </div>
                            <div>
                                <p className="text-xl sm:text-2xl font-bold text-white leading-tight">
                                    {profile.stats.games_count}
                                </p>
                                <p className="text-xs text-zinc-400 uppercase tracking-wider font-medium">Games Owned</p>
                            </div>
                        </div>

                        <div className="p-4 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center gap-3.5">
                            <div className="p-2.5 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
                                <Clock className="w-5 h-5" />
                            </div>
                            <div>
                                <p className="text-xl sm:text-2xl font-bold text-white leading-tight">
                                    {formatPlaytime(profile.stats.total_playtime_minutes)}
                                </p>
                                <p className="text-xs text-zinc-400 uppercase tracking-wider font-medium">Total Played</p>
                            </div>
                        </div>

                        <div className="p-4 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center gap-3.5">
                            <div className="p-2.5 rounded-lg bg-amber-600/10 text-amber-400 border border-amber-500/20">
                                <Star className="w-5 h-5" />
                            </div>
                            <div>
                                <p className="text-xl sm:text-2xl font-bold text-white leading-tight">
                                    {profile.stats.reviews_count}
                                </p>
                                <p className="text-xs text-zinc-400 uppercase tracking-wider font-medium">Reviews Written</p>
                            </div>
                        </div>

                        <div className="p-4 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center gap-3.5">
                            <div className="p-2.5 rounded-lg bg-emerald-600/10 text-emerald-400 border border-emerald-500/20">
                                <Calendar className="w-5 h-5" />
                            </div>
                            <div>
                                <p className="text-sm sm:text-base font-bold text-white leading-tight mt-0.5">
                                    {profile.stats.joined_date
                                        ? new Date(profile.stats.joined_date).toLocaleDateString("en-US", {
                                            month: "short",
                                            year: "numeric",
                                        })
                                        : "Recent"}
                                </p>
                                <p className="text-xs text-zinc-400 uppercase tracking-wider font-medium">Member Since</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Featured Games Showcase */}
                {(!isPrivate && ((profile.favorite_games?.length || 0) > 0 || isOwnProfile)) && (
                    <div className="space-y-4 pt-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                <Sparkles className="w-5 h-5 text-yellow-500 fill-current" />
                                Featured Favorites
                            </h2>
                            {isOwnProfile && (
                                <button
                                    onClick={() => setShowFavoritesManager(true)}
                                    className="text-xs text-violet-400 hover:text-violet-300 font-semibold"
                                >
                                    Manage Favorites
                                </button>
                            )}
                        </div>

                        {(profile.favorite_games?.length || 0) > 0 ? (
                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                                {(profile.favorite_games || []).map((game: any) => (
                                    <Link
                                        to={`/games/${game.id}`}
                                        key={game.id}
                                        className="group relative block aspect-[2/3] bg-zinc-900 rounded-xl overflow-hidden border border-white/10 hover:border-violet-500 transition-all shadow-lg hover:shadow-violet-500/20 hover:-translate-y-1"
                                    >
                                        {game.cover_url ? (
                                            <img
                                                src={getImageUrl(game.cover_url)}
                                                alt={game.title}
                                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                                loading="lazy"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-zinc-700 bg-zinc-800">
                                                <Gamepad2 className="w-8 h-8" />
                                            </div>
                                        )}
                                        <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3">
                                            <p className="text-white font-semibold text-xs line-clamp-2 leading-tight mb-2">
                                                {game.title}
                                            </p>
                                            <div className="flex items-center justify-between text-[11px] text-zinc-300">
                                                <span className="flex items-center gap-1 bg-black/60 px-1.5 py-0.5 rounded">
                                                    <Clock className="w-3 h-3 text-indigo-400" />
                                                    {formatPlaytime(game.total_minutes)}
                                                </span>
                                                {game.user_rating && (
                                                    <span className="flex items-center gap-0.5 text-yellow-400 bg-black/60 px-1.5 py-0.5 rounded">
                                                        <Star className="w-3 h-3 fill-current" />
                                                        {game.user_rating}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <div className="bg-zinc-900/30 border border-dashed border-white/10 rounded-2xl p-8 text-center space-y-3">
                                <Gamepad2 className="w-10 h-10 mx-auto text-zinc-600" />
                                <p className="text-sm text-zinc-400">Pin your crowning games to highlight them on your profile.</p>
                                <button
                                    onClick={() => setShowFavoritesManager(true)}
                                    className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-semibold transition-colors"
                                >
                                    Select Favorites
                                </button>
                            </div>
                        )}
                    </div>
                )}

                {/* Content: Activity & Reviews */}
                {isPrivate ? (
                    <div className="p-12 text-center rounded-2xl bg-zinc-900/30 border border-white/5 space-y-3">
                        <Lock className="w-12 h-12 mx-auto text-zinc-600" />
                        <h3 className="text-lg font-bold text-white">This Profile is Private</h3>
                        <p className="text-sm text-zinc-500">Only authorized friends can view gameplay activity and reviews.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
                        {/* Recent Activity */}
                        <div className="bg-zinc-900/50 border border-white/10 rounded-2xl p-6 space-y-4">
                            <h2 className="text-base font-bold text-white flex items-center justify-between">
                                <span>Recent Activity</span>
                                <Clock className="w-4 h-4 text-zinc-500" />
                            </h2>
                            {recentActivity && recentActivity.length > 0 ? (
                                <div className="space-y-2">
                                    {recentActivity.map((game) => (
                                        <Link
                                            key={game.id}
                                            to={`/games/${game.id}`}
                                            className="flex items-center gap-3.5 p-2.5 rounded-xl hover:bg-white/5 transition-all group"
                                        >
                                            {game.cover_url ? (
                                                <img
                                                    src={getImageUrl(game.cover_url)}
                                                    alt={game.title}
                                                    className="w-12 h-14 object-cover rounded-lg flex-shrink-0"
                                                    loading="lazy"
                                                />
                                            ) : (
                                                <div className="w-12 h-14 bg-zinc-800 rounded-lg flex items-center justify-center flex-shrink-0">
                                                    <Gamepad2 className="w-6 h-6 text-zinc-600" />
                                                </div>
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-semibold text-white group-hover:text-violet-300 transition-colors truncate">
                                                    {game.title}
                                                </p>
                                                <p className="text-xs text-zinc-400 mt-0.5">
                                                    {formatPlaytime(game.total_minutes)} played total
                                                </p>
                                            </div>
                                            <ArrowUpRight className="w-4 h-4 text-zinc-600 group-hover:text-violet-400 transition-colors flex-shrink-0" />
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-zinc-500 py-6 text-center">No recent activity recorded.</p>
                            )}
                        </div>

                        {/* Recent Reviews */}
                        <div className="bg-zinc-900/50 border border-white/10 rounded-2xl p-6 space-y-4">
                            <h2 className="text-base font-bold text-white flex items-center justify-between">
                                <span>Recent Reviews</span>
                                <Star className="w-4 h-4 text-zinc-500" />
                            </h2>
                            {reviews && reviews.length > 0 ? (
                                <div className="space-y-3">
                                    {reviews.map((review) => (
                                        <Link
                                            key={review.id}
                                            to={`/games/${review.game_id}`}
                                            className="block p-3.5 rounded-xl bg-zinc-950/40 border border-white/5 hover:border-violet-500/30 transition-all"
                                        >
                                            <div className="flex items-center justify-between gap-2 mb-1.5">
                                                <span className="text-sm font-semibold text-white truncate">
                                                    {review.game_title}
                                                </span>
                                                <div className="flex items-center gap-0.5 flex-shrink-0">
                                                    {[1, 2, 3, 4, 5].map((star) => (
                                                        <Star
                                                            key={star}
                                                            className={`w-3 h-3 ${
                                                                star <= review.rating
                                                                    ? "text-yellow-400 fill-current"
                                                                    : "text-zinc-700"
                                                            }`}
                                                        />
                                                    ))}
                                                </div>
                                            </div>
                                            <p className="text-xs text-zinc-400 line-clamp-2 leading-relaxed">
                                                "{review.content}"
                                            </p>
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-zinc-500 py-6 text-center">No reviews submitted yet.</p>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Edit Modal */}
            {showEditModal && profile && (
                <ProfileEditModal
                    profile={profile}
                    onClose={() => setShowEditModal(false)}
                    onSaved={() => {
                        setShowEditModal(false);
                        queryClient.invalidateQueries({ queryKey: ["profile", profileId] });
                    }}
                />
            )}

            {/* Favorites Manager */}
            {showFavoritesManager && profile && (
                <FavoritesManager
                    currentFavorites={profile.favorite_games || []}
                    onClose={() => setShowFavoritesManager(false)}
                    onSave={async (ids) => {
                        await updateFavoritesMutation.mutateAsync(ids);
                    }}
                />
            )}
        </div>
    );
}
