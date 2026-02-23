import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Star, Loader2, MessageSquare } from "lucide-react";
import { ReviewCard } from "./ReviewCard";
import { ReviewForm } from "./ReviewForm";
import { reviewsAPI, ReviewWithUser } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

interface ReviewListProps {
    gameId: number;
}

export function ReviewList({ gameId }: ReviewListProps) {
    const queryClient = useQueryClient();
    const { user } = useAuth();
    const [showForm, setShowForm] = useState(false);
    const [editingReview, setEditingReview] = useState<ReviewWithUser | null>(null);
    const [sortBy, setSortBy] = useState<"recent" | "rating" | "playtime">("recent");

    // Fetch reviews
    const { data: reviews, isLoading: reviewsLoading } = useQuery({
        queryKey: ["reviews", gameId, sortBy],
        queryFn: () => reviewsAPI.getGameReviews(gameId, sortBy),
    });

    // Fetch my review
    const { data: myReview } = useQuery({
        queryKey: ["my-review", gameId],
        queryFn: () => reviewsAPI.getMyReviewForGame(gameId),
        enabled: !!user,
    });

    // Fetch stats
    const { data: stats } = useQuery({
        queryKey: ["review-stats", gameId],
        queryFn: () => reviewsAPI.getGameReviewStats(gameId),
    });

    // Create mutation
    const createMutation = useMutation({
        mutationFn: (data: { content: string; rating: number; isRecommended?: boolean }) =>
            reviewsAPI.createReview({ game_id: gameId, ...data }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["reviews", gameId] });
            queryClient.invalidateQueries({ queryKey: ["my-review", gameId] });
            queryClient.invalidateQueries({ queryKey: ["review-stats", gameId] });
            setShowForm(false);
        },
    });

    // Update mutation
    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: number; data: { content?: string; rating?: number; isRecommended?: boolean } }) =>
            reviewsAPI.updateReview(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["reviews", gameId] });
            queryClient.invalidateQueries({ queryKey: ["my-review", gameId] });
            queryClient.invalidateQueries({ queryKey: ["review-stats", gameId] });
            setEditingReview(null);
        },
    });

    // Delete mutation
    const deleteMutation = useMutation({
        mutationFn: (reviewId: number) => reviewsAPI.deleteReview(reviewId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["reviews", gameId] });
            queryClient.invalidateQueries({ queryKey: ["my-review", gameId] });
            queryClient.invalidateQueries({ queryKey: ["review-stats", gameId] });
        },
    });

    const handleDelete = async (reviewId: number) => {
        if (!confirm("Are you sure you want to delete this review?")) return;
        deleteMutation.mutate(reviewId);
    };

    const hasReviewed = !!myReview;

    return (
        <div className="space-y-6">
            {/* Stats Header */}
            {stats && stats.total_reviews > 0 && (
                <div className="flex items-center gap-6 p-4 bg-zinc-900/50 border border-white/10 rounded-xl">
                    <div className="flex items-center gap-2">
                        <Star className="w-6 h-6 text-yellow-500 fill-current" />
                        <span className="text-2xl font-bold text-white">
                            {stats.average_rating.toFixed(1)}
                        </span>
                        <span className="text-zinc-400">/5</span>
                    </div>
                    <div className="text-zinc-400">
                        {stats.total_reviews} {stats.total_reviews === 1 ? "review" : "reviews"}
                    </div>
                    {stats.recommend_percent !== null && (
                        <div className="text-blue-400">
                            {stats.recommend_percent}% recommend
                        </div>
                    )}
                </div>
            )}

            {/* Controls */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-sm text-zinc-400">Sort by:</span>
                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                        className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                    >
                        <option value="recent">Most Recent</option>
                        <option value="rating">Highest Rating</option>
                        <option value="playtime">Most Playtime</option>
                    </select>
                </div>

                {user && !hasReviewed && !showForm && (
                    <button
                        onClick={() => setShowForm(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white font-medium rounded-lg transition-colors"
                    >
                        <MessageSquare className="w-4 h-4" />
                        Write a Review
                    </button>
                )}
            </div>

            {/* Write Review Form */}
            {showForm && (
                <ReviewForm
                    gameId={gameId}
                    onSubmit={async (data) => {
                        await createMutation.mutateAsync(data);
                    }}
                    onCancel={() => setShowForm(false)}
                />
            )}

            {/* Edit Review Form */}
            {editingReview && (
                <ReviewForm
                    gameId={gameId}
                    isEditing
                    initialValues={{
                        content: editingReview.content,
                        rating: editingReview.rating,
                        isRecommended: editingReview.is_recommended,
                    }}
                    onSubmit={async (data) => {
                        await updateMutation.mutateAsync({ id: editingReview.id, data });
                    }}
                    onCancel={() => setEditingReview(null)}
                />
            )}

            {/* My Review (if exists and not editing) */}
            {myReview && !editingReview && (
                <div className="space-y-2">
                    <h4 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">
                        Your Review
                    </h4>
                    <ReviewCard
                        id={myReview.id}
                        username={myReview.username}
                        displayName={myReview.display_name}
                        avatarUrl={myReview.avatar_url}
                        rating={myReview.rating}
                        isRecommended={myReview.is_recommended}
                        content={myReview.content}
                        playtimeAtReview={myReview.playtime_at_review}
                        createdAt={myReview.created_at}
                        isOwn
                        onEdit={() => setEditingReview(myReview)}
                        onDelete={() => handleDelete(myReview.id)}
                    />
                </div>
            )}

            {/* Reviews List */}
            <div className="space-y-4">
                {reviewsLoading ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
                    </div>
                ) : reviews && reviews.length > 0 ? (
                    reviews
                        .filter((r) => r.user_id !== user?.id) // Don't show own review in main list
                        .map((review) => (
                            <ReviewCard
                                key={review.id}
                                id={review.id}
                                username={review.username}
                                displayName={review.display_name}
                                avatarUrl={review.avatar_url}
                                rating={review.rating}
                                isRecommended={review.is_recommended}
                                content={review.content}
                                playtimeAtReview={review.playtime_at_review}
                                createdAt={review.created_at}
                            />
                        ))
                ) : !myReview ? (
                    <div className="text-center py-12 text-zinc-500">
                        <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No reviews yet. Be the first to review!</p>
                    </div>
                ) : null}
            </div>
        </div>
    );
}
