import { Link } from "react-router-dom";
import { Game, getImageUrl, formatPrice } from "@/lib/api";
import { getPrimaryRatingBadge } from "@/lib/ratings";
import { Play, Star, Sparkles } from "lucide-react";

interface GameCardProps {
    game: Game;
    size?: "sm" | "md" | "lg";
    showPrice?: boolean;
    className?: string;
}

// Sentiment color indicator classes for Steam ratings:
// >= 70%: emerald (Positive)
// 40-69%: amber (Mixed)
// < 40%: red (Negative)

export function GameCard({ game, size = "md", showPrice = true, className = "" }: GameCardProps) {
    const imageUrl = getImageUrl(game.header_image || game.cover_url);

    // Aspect ratio: landscape for header artwork
    const aspectClasses = {
        sm: "aspect-[16/10]",
        md: "aspect-video",
        lg: "aspect-video",
    };

    const hasDiscount = Boolean(game.discount_percent && game.discount_percent > 0);
    const originalPrice = hasDiscount && game.price_cents
        ? Math.round(game.price_cents / (1 - (game.discount_percent! / 100)))
        : null;

    // R1: Primary rating badge hierarchy: Steam % -> Metacritic -> IGDB -> null
    const ratingBadge = getPrimaryRatingBadge(game);

    return (
        <Link
            to={`/games/${game.id}`}
            className={`
                group relative block w-full rounded-2xl overflow-hidden
                bg-zinc-900/60 hover:bg-zinc-900/90
                border border-white/10 hover:border-violet-500/50
                transition-all duration-300 ease-out
                hover:-translate-y-1 hover:shadow-2xl hover:shadow-violet-600/15
                ${className}
            `}
        >
            {/* Image Artwork Container */}
            <div className={`relative ${aspectClasses[size]} w-full overflow-hidden bg-zinc-950`}>
                {imageUrl ? (
                    <img
                        src={imageUrl}
                        alt={game.title}
                        className="w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
                        loading="lazy"
                    />
                ) : (
                    <div className="w-full h-full bg-gradient-to-br from-violet-950/40 via-zinc-900 to-indigo-950/30 flex items-center justify-center">
                        <span className="text-3xl font-extrabold text-white/20">{game.title.charAt(0)}</span>
                    </div>
                )}

                {/* Subtle vignette gradient */}
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-950/90 via-transparent to-black/30 opacity-70 group-hover:opacity-50 transition-opacity" />

                {/* Discount Badge */}
                {hasDiscount && (
                    <div className="absolute top-2.5 right-2.5 px-2 py-0.5 bg-emerald-500 text-white text-[11px] font-extrabold rounded-md shadow-md z-10">
                        -{game.discount_percent}%
                    </div>
                )}

                {/* Primary Rating Badge (Steam % -> Metacritic -> IGDB) */}
                {ratingBadge && (
                    <div
                        className={`absolute top-2.5 left-2.5 px-2 py-0.5 rounded-md text-[11px] font-bold shadow-md z-10 border border-white/10 flex items-center gap-1 ${ratingBadge.bgClass}`}
                        title={ratingBadge.title}
                        data-testid="primary-rating-badge"
                        data-rating-source={ratingBadge.source}
                    >
                        {ratingBadge.source === "steam" && (
                            <Sparkles className="w-2.5 h-2.5 fill-current flex-shrink-0" />
                        )}
                        {ratingBadge.source === "igdb" && (
                            <Star className="w-2.5 h-2.5 fill-current flex-shrink-0" />
                        )}
                        <span>{ratingBadge.label}</span>
                    </div>
                )}

                {/* Quick Play / Action Icon Overlay */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-black/40 backdrop-blur-[1px] z-10">
                    <div className="p-3 rounded-full bg-violet-600 text-white shadow-xl transform scale-90 group-hover:scale-100 transition-transform duration-200">
                        <Play className="w-4 h-4 fill-current translate-x-0.5" />
                    </div>
                </div>
            </div>

            {/* Card Content & Metadata */}
            <div className="p-3.5 space-y-2">
                <div>
                    <h3 className="font-bold text-sm text-white truncate group-hover:text-violet-300 transition-colors drop-shadow-sm">
                        {game.title}
                    </h3>

                    {/* Genres / Tags */}
                    {game.genres && game.genres.length > 0 && (
                        <p className="text-[11px] text-zinc-400 truncate mt-0.5">
                            {game.genres.slice(0, 2).join(" • ")}
                        </p>
                    )}
                </div>

                {/* Ratings & Price Footer */}
                {showPrice && (
                    <div className="flex items-center justify-between pt-1 border-t border-white/5 text-xs">
                        {/* Rating or Review Status */}
                        {game.steam_review_desc ? (
                            <div className="flex items-center gap-1 text-blue-400 font-medium text-[11px] truncate max-w-[130px]" title={game.steam_review_desc}>
                                <Sparkles className="w-3 h-3 fill-current flex-shrink-0" />
                                <span className="truncate">{game.steam_review_desc}</span>
                            </div>
                        ) : game.steam_review_percent !== undefined ? (
                            <div className="flex items-center gap-1 text-blue-400 font-medium text-[11px]">
                                <Sparkles className="w-3 h-3 fill-current" />
                                <span>{game.steam_review_percent}%</span>
                            </div>
                        ) : game.rating ? (
                            <div className="flex items-center gap-1 text-yellow-400 font-medium text-[11px]">
                                <Star className="w-3 h-3 fill-current" />
                                <span>{game.rating > 10 ? (game.rating / 10).toFixed(1) : game.rating.toFixed(1)}</span>
                            </div>
                        ) : (
                            <span className="text-[11px] text-zinc-500">Steam Game</span>
                        )}

                        {/* Price & Sale Display */}
                        <div className="flex items-center gap-1.5">
                            {originalPrice && (
                                <span className="text-[11px] text-zinc-500 line-through">
                                    {formatPrice(originalPrice)}
                                </span>
                            )}
                            <span className="font-extrabold text-white">
                                {formatPrice(game.price_cents)}
                            </span>
                        </div>
                    </div>
                )}
            </div>
        </Link>
    );
}
