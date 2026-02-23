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
        queryFn: () => profilesAPI.getRecentActivity(profileId!, 5),
        enabled: !!profileId && (isOwnProfile || profile?.privacy_level === "public"),
    });

    // Fetch user reviews
    const { data: reviews } = useQuery({
        queryKey: ["user-reviews", profileId],
        queryFn: () => profilesAPI.getUserReviews(profileId!, 5),
        enabled: !!profileId && (isOwnProfile || profile?.privacy_level === "public"),
    });

    // Friend request mutation
    const sendRequestMutation = useMutation({
        mutationFn: (id: number) => friendsAPI.sendRequest(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["profile", profileId] });
        },
    });

    const [showFavoritesManager, setShowFavoritesManager] = useState(false);

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
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
            </div>
        );
    }

    if (profileError || !profile) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] text-zinc-500">
                <User className="w-16 h-16 mb-4 opacity-50" />
                <p>User not found</p>
            </div>
        );
    }

    const isPrivate = profile.privacy_level === "private" && !isOwnProfile;

    return (
        <div className="min-h-screen">
            {/* Banner */}
            <div
                className="h-80 md:h-96 relative bg-gradient-to-br from-violet-600/30 to-indigo-800/30"
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
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 to-transparent" />
            </div>

            {/* Profile Header */}
            <div className="max-w-5xl mx-auto px-6 -mt-20 relative z-10">
                <div className="flex flex-col md:flex-row items-start gap-6">
                    {/* Avatar */}
                    <div className="relative">
                        {profile.avatar_url ? (
                            <img
                                src={getImageUrl(profile.avatar_url)}
                                alt={profile.display_name || profile.username}
                                className="w-32 h-32 rounded-2xl border-4 border-zinc-900 object-cover shadow-xl"
                            />
                        ) : (
                            <div className="w-32 h-32 rounded-2xl border-4 border-zinc-900 bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-4xl font-bold text-white shadow-xl">
                                {(profile.display_name || profile.username)[0].toUpperCase()}
                            </div>
                        )}
                        {profile.privacy_level !== "public" && (
                            <div className="absolute -bottom-2 -right-2 p-1.5 bg-zinc-800 rounded-lg border border-zinc-700">
                                {profile.privacy_level === "friends" ? (
                                    <Users className="w-4 h-4 text-blue-400" />
                                ) : (
                                    <Lock className="w-4 h-4 text-yellow-400" />
                                )}
                            </div>
                        )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 pt-4">
                        <div className="flex items-start justify-between">
                            <div>
                                <h1 className="text-3xl font-bold text-white">
                                    {profile.display_name || profile.username}
                                </h1>
                                <p className="text-zinc-500">@{profile.username}</p>
                            </div>

                            {/* Actions */}
                            <div className="flex items-center gap-2">
                                {isOwnProfile ? (
                                    <button
                                        onClick={() => setShowEditModal(true)}
                                        className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition-colors"
                                    >
                                        <Edit2 className="w-4 h-4" />
                                        Edit Profile
                                    </button>
                                ) : (
                                    <>
                                        {profile.friend_status === "accepted" ? (
                                            <span className="flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400 rounded-lg">
                                                <UserCheck className="w-4 h-4" />
                                                Friends
                                            </span>
                                        ) : profile.friend_status === "pending" ? (
                                            <span className="flex items-center gap-2 px-4 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg">
                                                <Clock className="w-4 h-4" />
                                                Request Pending
                                            </span>
                                        ) : profile.friend_status === "sent" ? (
                                            <span className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg">
                                                <Clock className="w-4 h-4" />
                                                Request Sent
                                            </span>
                                        ) : (
                                            <button
                                                onClick={() => sendRequestMutation.mutate(profile.id)}
                                                disabled={sendRequestMutation.isPending}
                                                className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg transition-colors disabled:opacity-50"
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

                        {/* Bio */}
                        {profile.bio && !isPrivate && (
                            <p className="mt-4 text-zinc-300 leading-relaxed max-w-2xl">
                                {profile.bio}
                            </p>
                        )}

                        {/* Stats */}
                        {!isPrivate && (
                            <div className="flex items-center gap-6 mt-6">
                                <div className="flex items-center gap-2 text-zinc-400">
                                    <Gamepad2 className="w-4 h-4" />
                                    <span className="text-white font-medium">
                                        {profile.stats.games_count}
                                    </span>
                                    games
                                </div>
                                <div className="flex items-center gap-2 text-zinc-400">
                                    <Clock className="w-4 h-4" />
                                    <span className="text-white font-medium">
                                        {formatPlaytime(profile.stats.total_playtime_minutes)}
                                    </span>
                                    played
                                </div>
                                <div className="flex items-center gap-2 text-zinc-400">
                                    <Star className="w-4 h-4" />
                                    <span className="text-white font-medium">
                                        {profile.stats.reviews_count}
                                    </span>
                                    reviews
                                </div>
                                {profile.stats.joined_date && (
                                    <div className="flex items-center gap-2 text-zinc-400">
                                        <Calendar className="w-4 h-4" />
                                        Joined{" "}
                                        {new Date(profile.stats.joined_date).toLocaleDateString(
                                            "en-US",
                                            { month: "short", year: "numeric" }
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Featured Games */}
            {(!isPrivate && (profile.favorite_games?.length > 0 || isOwnProfile)) && (
                <div className="max-w-5xl mx-auto px-6 mt-12 mb-4">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <Star className="w-5 h-5 text-yellow-500 fill-current" />
                            Featured Games
                        </h2>
                        {isOwnProfile && (
                            <button
                                onClick={() => setShowFavoritesManager(true)}
                                className="text-sm text-violet-400 hover:text-violet-300 font-medium"
                            >
                                Manage Favorites
                            </button>
                        )}
                    </div>

                    {profile.favorite_games?.length > 0 ? (
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                            {profile.favorite_games.map(game => (
                                <Link to={`/store/${game.id}`} key={game.id} className="group relative block aspect-[2/3] bg-zinc-900 rounded-xl overflow-hidden ring-1 ring-white/10 hover:ring-violet-500 transition-all shadow-lg hover:shadow-violet-500/20">
                                    {game.cover_url ? (
                                        <img src={getImageUrl(game.cover_url)} alt={game.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-zinc-700 bg-zinc-800">
                                            <Gamepad2 className="w-8 h-8" />
                                        </div>
                                    )}
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end p-3">
                                        <p className="text-white font-medium text-sm line-clamp-2 leading-tight mb-2">{game.title}</p>
                                        <div className="flex items-center justify-between text-xs text-zinc-300">
                                            <span className="flex items-center gap-1 bg-black/50 px-1.5 py-0.5 rounded">
                                                <Clock className="w-3 h-3" />
                                                {formatPlaytime(game.total_minutes)}
                                            </span>
                                            {game.user_rating && (
                                                <span className="flex items-center gap-1 text-yellow-400 bg-black/50 px-1.5 py-0.5 rounded">
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
                        <div className="bg-zinc-900/30 border border-dashed border-zinc-800 rounded-xl p-8 text-center">
                            <Gamepad2 className="w-10 h-10 mx-auto text-zinc-700 mb-3" />
                            <p className="text-zinc-500 mb-4">Showcase your top games here!</p>
                            <button
                                onClick={() => setShowFavoritesManager(true)}
                                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg text-sm transition-colors"
                            >
                                Select Favorites
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Content */}
            {isPrivate ? (
                <div className="max-w-5xl mx-auto px-6 py-12 text-center">
                    <Lock className="w-16 h-16 mx-auto mb-4 text-zinc-600" />
                    <p className="text-zinc-500 text-lg">This profile is private</p>
                </div>
            ) : (
                <div className="max-w-5xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Recent Activity */}
                    <div className="bg-zinc-900/50 border border-white/10 rounded-xl p-6">
                        <h2 className="text-lg font-semibold text-white mb-4">
                            Recent Activity
                        </h2>
                        {recentActivity && recentActivity.length > 0 ? (
                            <div className="space-y-3">
                                {recentActivity.map((game) => (
                                    <Link
                                        key={game.id}
                                        to={`/store/${game.id}`}
                                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors"
                                    >
                                        {game.cover_url ? (
                                            <img
                                                src={getImageUrl(game.cover_url)}
                                                alt={game.title}
                                                className="w-12 h-16 object-cover rounded"
                                            />
                                        ) : (
                                            <div className="w-12 h-16 bg-zinc-800 rounded flex items-center justify-center">
                                                <Gamepad2 className="w-6 h-6 text-zinc-600" />
                                            </div>
                                        )}
                                        <div className="flex-1 min-w-0">
                                            <p className="text-white font-medium truncate">
                                                {game.title}
                                            </p>
                                            <p className="text-sm text-zinc-500">
                                                {formatPlaytime(game.total_minutes)} played
                                            </p>
                                        </div>
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <p className="text-zinc-500">No recent activity</p>
                        )}
                    </div>

                    {/* Reviews */}
                    <div className="bg-zinc-900/50 border border-white/10 rounded-xl p-6">
                        <h2 className="text-lg font-semibold text-white mb-4">
                            Recent Reviews
                        </h2>
                        {reviews && reviews.length > 0 ? (
                            <div className="space-y-4">
                                {reviews.map((review) => (
                                    <Link
                                        key={review.id}
                                        to={`/store/${review.game_id}`}
                                        className="block p-3 rounded-lg hover:bg-white/5 transition-colors"
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-white font-medium">
                                                {review.game_title}
                                            </span>
                                            <div className="flex items-center gap-0.5">
                                                {[1, 2, 3, 4, 5].map((star) => (
                                                    <Star
                                                        key={star}
                                                        className={`w-3 h-3 ${star <= review.rating
                                                            ? "text-yellow-500 fill-current"
                                                            : "text-zinc-600"
                                                            }`}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                        <p className="text-sm text-zinc-400 line-clamp-2">
                                            {review.content}
                                        </p>
                                    </Link>
                                ))}
                            </div>
                        ) : (
                            <p className="text-zinc-500">No reviews yet</p>
                        )}
                    </div>
                </div>
            )}

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
