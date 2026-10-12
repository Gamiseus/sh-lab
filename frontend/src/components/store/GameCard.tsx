import { Link } from "react-router-dom";
import { Game, getImageUrl, formatPrice } from "@/lib/api";
import { Play, Download, Star } from "lucide-react";

interface GameCardProps {
    game: Game;
    size?: "sm" | "md" | "lg";
    showPrice?: boolean;
    className?: string;
}

export function GameCard({ game, size = "md", showPrice = false, className = "" }: GameCardProps) {
    const imageUrl = getImageUrl(game.header_image || game.cover_url);

    const sizeClasses = {
        sm: "w-40",
        md: "w-56",
        lg: "w-72",
    };

    const aspectClasses = {
        sm: "aspect-[2/3]",
        md: "aspect-video",
        lg: "aspect-video",
    };

    return (
        <Link
            to={`/games/${game.id}`}
            className={`
        group relative block rounded-xl overflow-hidden
        bg-gradient-to-b from-zinc-800/50 to-zinc-900/80
        border border-white/5 hover:border-violet-500/50
        transition-all duration-300 ease-out
        hover:scale-[1.02] hover:shadow-xl hover:shadow-violet-500/10
        ${sizeClasses[size]} ${className}
      `}
        >
            {/* Image Container */}
            <div className={`relative ${aspectClasses[size]} overflow-hidden`}>
                {imageUrl ? (
                    <img
                        src={imageUrl}
                        alt={game.title}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                        loading="lazy"
                    />
                ) : (
                    <div className="w-full h-full bg-gradient-to-br from-violet-900/30 to-indigo-900/30 flex items-center justify-center">
                        <span className="text-2xl font-bold text-white/20">{game.title[0]}</span>
                    </div>
                )}

                {/* Gradient Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-60 group-hover:opacity-80 transition-opacity" />

                {/* Hover Actions */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <div className="flex gap-2">
                        <button className="p-3 rounded-full bg-violet-600 hover:bg-violet-500 text-white shadow-lg transform scale-90 group-hover:scale-100 transition-all">
                            <Play className="w-5 h-5 fill-current" />
                        </button>
                        <button className="p-3 rounded-full bg-white/10 hover:bg-white/20 text-white backdrop-blur-sm shadow-lg transform scale-90 group-hover:scale-100 transition-all delay-75">
                            <Download className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Discount Badge */}
                {Boolean(game.discount_percent && game.discount_percent > 0) && (
                    <div className="absolute top-2 right-2 px-2 py-1 bg-green-500 text-white text-xs font-bold rounded">
                        -{game.discount_percent}%
                    </div>
                )}

                {/* Metacritic Score */}
                {game.metacritic_score && (
                    <div className={`
            absolute top-2 left-2 px-2 py-1 rounded text-xs font-bold
            ${game.metacritic_score >= 75 ? "bg-green-600" : game.metacritic_score >= 50 ? "bg-yellow-600" : "bg-red-600"}
          `}>
                        {game.metacritic_score}
                    </div>
                )}
            </div>

            {/* Content */}
            <div className="p-3">
                <h3 className="font-semibold text-sm text-white truncate group-hover:text-violet-300 transition-colors">
                    {game.title}
                </h3>

                {size !== "sm" && (
                    <div className="flex items-center gap-2 mt-1">
                        {game.genres && game.genres.length > 0 && (
                            <span className="text-xs text-zinc-500 truncate">
                                {game.genres.slice(0, 2).join(", ")}
                            </span>
                        )}
                    </div>
                )}

                {showPrice && (
                    <div className="flex items-center justify-between mt-2">
                        {game.rating && (
                            <div className="flex items-center gap-1 text-yellow-500">
                                <Star className="w-3 h-3 fill-current" />
                                <span className="text-xs">{game.rating > 10 ? (game.rating / 10).toFixed(1) : game.rating.toFixed(1)}</span>
                            </div>
                        )}
                        <div className="flex items-center gap-2">
                            {Boolean(game.discount_percent && game.discount_percent > 0 && game.price_cents) && (
                                <span className="text-xs text-zinc-500 line-through">
                                    {formatPrice(Math.round(game.price_cents! / (1 - (game.discount_percent! / 100))))}
                                </span>
                            )}
                            <span className="text-sm font-bold text-violet-400">
                                {formatPrice(game.price_cents)}
                            </span>
                        </div>
                    </div>
                )}
            </div>
        </Link>
    );
}
