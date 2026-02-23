import { useState } from "react";
import { Star, ThumbsUp, ThumbsDown, Loader2, X } from "lucide-react";

interface ReviewFormProps {
    gameId: number;
    initialValues?: {
        content: string;
        rating: number;
        isRecommended?: boolean;
    };
    isEditing?: boolean;
    onSubmit: (data: { content: string; rating: number; isRecommended?: boolean }) => Promise<void>;
    onCancel?: () => void;
}

export function ReviewForm({
    initialValues,
    isEditing = false,
    onSubmit,
    onCancel,
}: ReviewFormProps) {
    const [content, setContent] = useState(initialValues?.content || "");
    const [rating, setRating] = useState(initialValues?.rating || 0);
    const [isRecommended, setIsRecommended] = useState<boolean | undefined>(
        initialValues?.isRecommended
    );
    const [hoverRating, setHoverRating] = useState(0);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!content.trim()) {
            setError("Please write a review");
            return;
        }
        if (rating === 0) {
            setError("Please select a rating");
            return;
        }

        setIsSubmitting(true);
        try {
            await onSubmit({ content, rating, isRecommended });
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to submit review");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="bg-zinc-900/50 border border-white/10 rounded-xl p-6 space-y-6">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white">
                    {isEditing ? "Edit Your Review" : "Write a Review"}
                </h3>
                {onCancel && (
                    <button
                        type="button"
                        onClick={onCancel}
                        className="p-2 text-zinc-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                )}
            </div>

            {/* Star Rating */}
            <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">Rating</label>
                <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                        <button
                            key={star}
                            type="button"
                            onClick={() => setRating(star)}
                            onMouseEnter={() => setHoverRating(star)}
                            onMouseLeave={() => setHoverRating(0)}
                            className="p-1 transition-transform hover:scale-110"
                        >
                            <Star
                                className={`w-8 h-8 transition-colors ${star <= (hoverRating || rating)
                                        ? "text-yellow-500 fill-current"
                                        : "text-zinc-600"
                                    }`}
                            />
                        </button>
                    ))}
                    {rating > 0 && (
                        <span className="ml-3 text-sm text-zinc-400">
                            {rating === 1
                                ? "Poor"
                                : rating === 2
                                    ? "Fair"
                                    : rating === 3
                                        ? "Good"
                                        : rating === 4
                                            ? "Great"
                                            : "Excellent"}
                        </span>
                    )}
                </div>
            </div>

            {/* Recommend Toggle */}
            <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">
                    Do you recommend this game?
                </label>
                <div className="flex items-center gap-3">
                    <button
                        type="button"
                        onClick={() => setIsRecommended(true)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${isRecommended === true
                                ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                                : "bg-zinc-800 text-zinc-400 hover:text-white"
                            }`}
                    >
                        <ThumbsUp className="w-5 h-5" />
                        Yes
                    </button>
                    <button
                        type="button"
                        onClick={() => setIsRecommended(false)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${isRecommended === false
                                ? "bg-red-500/20 text-red-400 border border-red-500/30"
                                : "bg-zinc-800 text-zinc-400 hover:text-white"
                            }`}
                    >
                        <ThumbsDown className="w-5 h-5" />
                        No
                    </button>
                    {isRecommended !== undefined && (
                        <button
                            type="button"
                            onClick={() => setIsRecommended(undefined)}
                            className="text-xs text-zinc-500 hover:text-zinc-400"
                        >
                            Clear
                        </button>
                    )}
                </div>
            </div>

            {/* Content */}
            <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">
                    Your Review
                </label>
                <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    rows={6}
                    placeholder="Share your thoughts about this game..."
                    className="w-full px-4 py-3 bg-zinc-800/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent resize-y min-h-[120px]"
                />
                <p className="text-xs text-zinc-500">
                    {content.length} characters
                </p>
            </div>

            {/* Error */}
            {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                    {error}
                </div>
            )}

            {/* Submit */}
            <div className="flex items-center gap-3 pt-2">
                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isSubmitting ? (
                        <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Submitting...
                        </>
                    ) : isEditing ? (
                        "Update Review"
                    ) : (
                        "Submit Review"
                    )}
                </button>
                {onCancel && (
                    <button
                        type="button"
                        onClick={onCancel}
                        className="px-6 py-3 text-zinc-400 hover:text-white font-medium rounded-lg hover:bg-white/5 transition-colors"
                    >
                        Cancel
                    </button>
                )}
            </div>
        </form>
    );
}
