import { Star, ThumbsUp, ThumbsDown, Clock, Edit2, Trash2 } from "lucide-react";
import { formatPlaytime } from "@/lib/api";

interface ReviewCardProps {
    id: number;
    username: string;
    displayName?: string;
    avatarUrl?: string;
    rating: number;
    isRecommended?: boolean;
    content: string;
    playtimeAtReview?: number;
    createdAt?: string;
    isOwn?: boolean;
    onEdit?: () => void;
    onDelete?: () => void;
}

export function ReviewCard({
    username,
    displayName,
    avatarUrl,
    rating,
    isRecommended,
    content,
    playtimeAtReview,
    createdAt,
    isOwn = false,
    onEdit,
    onDelete,
}: ReviewCardProps) {
    const displayDate = createdAt
        ? new Date(createdAt).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
        })
        : null;

    return (
        <div className="bg-zinc-900/50 border border-white/10 rounded-xl p-6 space-y-4">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                    {/* Avatar */}
                    {avatarUrl ? (
                        <img
                            src={avatarUrl}
                            alt={displayName || username}
                            className="w-10 h-10 rounded-full object-cover"
                        />
                    ) : (
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-bold">
                            {(displayName || username)[0].toUpperCase()}
                        </div>
                    )}

                    {/* User Info */}
                    <div>
                        <p className="font-medium text-white">
                            {displayName || username}
                        </p>
                        <div className="flex items-center gap-3 text-xs text-zinc-500">
                            {playtimeAtReview !== undefined && playtimeAtReview > 0 && (
                                <span className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {formatPlaytime(playtimeAtReview)} at review
                                </span>
                            )}
                            {displayDate && <span>{displayDate}</span>}
                        </div>
                    </div>
                </div>

                {/* Recommendation Badge */}
                {isRecommended !== undefined && (
                    <div
                        className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-sm font-medium ${isRecommended
                            ? "bg-blue-500/10 text-blue-400"
                            : "bg-red-500/10 text-red-400"
                            }`}
                    >
                        {isRecommended ? (
                            <>
                                <ThumbsUp className="w-4 h-4" />
                                Recommended
                            </>
                        ) : (
                            <>
                                <ThumbsDown className="w-4 h-4" />
                                Not Recommended
                            </>
                        )}
                    </div>
                )}
            </div>

            {/* Rating */}
            <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                    <Star
                        key={star}
                        className={`w-4 h-4 ${star <= rating
                            ? "text-yellow-500 fill-current"
                            : "text-zinc-600"
                            }`}
                    />
                ))}
                <span className="ml-2 text-sm text-zinc-400">{rating}/5</span>
            </div>

            {/* Content */}
            <div className="text-zinc-300 leading-relaxed whitespace-pre-line">
                {content}
            </div>

            {/* Own Review Actions */}
            {isOwn && (onEdit || onDelete) && (
                <div className="flex items-center gap-2 pt-4 border-t border-white/5">
                    {onEdit && (
                        <button
                            onClick={onEdit}
                            className="flex items-center gap-2 px-3 py-1.5 text-sm text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                        >
                            <Edit2 className="w-4 h-4" />
                            Edit
                        </button>
                    )}
                    {onDelete && (
                        <button
                            onClick={onDelete}
                            className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                        >
                            <Trash2 className="w-4 h-4" />
                            Delete
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
