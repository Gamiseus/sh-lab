import { Game, formatPrice, formatPlaytime } from "@/lib/api";
import {
    Download,
    Play,
    Calendar,
    Building2,
    Users,
    Star,
    Trophy,
    Monitor,
    Apple,
    Terminal
} from "lucide-react";
import { Link } from "react-router-dom";

interface GameInfoPanelProps {
    game: Game;
    isInstalled?: boolean;
    onInstall?: () => void;
    onLaunch?: () => void;
}

export function GameInfoPanel({ game, isInstalled = false, onInstall, onLaunch }: GameInfoPanelProps) {
    return (
        <div className="bg-zinc-900/50 border border-white/10 rounded-xl overflow-hidden">
            {/* Main CTA */}
            <div className="p-6 border-b border-white/5">
                {/* Price */}
                {game.price_cents !== undefined && (
                    <div className="flex items-center gap-3 mb-4">
                        {game.discount_percent && game.discount_percent > 0 && (
                            <>
                                <span className="px-2 py-1 bg-green-600 text-white text-sm font-bold rounded">
                                    -{game.discount_percent}%
                                </span>
                                <span className="text-zinc-500 line-through text-lg">
                                    ${(game.price_cents / 100).toFixed(2)}
                                </span>
                            </>
                        )}
                        <span className="text-2xl font-bold text-white">
                            {formatPrice(game.price_cents, game.discount_percent)}
                        </span>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="space-y-3">
                    {isInstalled ? (
                        <button
                            onClick={onLaunch}
                            className="
                w-full py-4 rounded-xl font-bold text-lg
                bg-gradient-to-r from-green-600 to-emerald-600
                hover:from-green-500 hover:to-emerald-500
                text-white shadow-lg shadow-green-500/20
                flex items-center justify-center gap-3
                transition-all duration-300 hover:scale-[1.02]
              "
                        >
                            <Play className="w-5 h-5 fill-current" />
                            Play
                        </button>
                    ) : (
                        <button
                            onClick={onInstall}
                            className="
                w-full py-4 rounded-xl font-bold text-lg
                bg-gradient-to-r from-violet-600 to-indigo-600
                hover:from-violet-500 hover:to-indigo-500
                text-white shadow-lg shadow-violet-500/20
                flex items-center justify-center gap-3
                transition-all duration-300 hover:scale-[1.02]
              "
                        >
                            <Download className="w-5 h-5" />
                            Install
                        </button>
                    )}
                </div>
            </div>

            {/* Scores & Reviews */}
            <div className="p-6 border-b border-white/5 space-y-4">
                {/* Metacritic */}
                {game.metacritic_score && (
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-400">Metacritic</span>
                        <a
                            href={game.metacritic_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`
                px-3 py-1 rounded font-bold text-lg
                ${game.metacritic_score >= 75
                                    ? "bg-green-600"
                                    : game.metacritic_score >= 50
                                        ? "bg-yellow-600"
                                        : "bg-red-600"
                                }
              `}
                        >
                            {game.metacritic_score}
                        </a>
                    </div>
                )}

                {/* Steam Reviews */}
                {game.steam_review_percent !== undefined && game.steam_review_count && (
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-400">User Reviews</span>
                        <div className="text-right">
                            <div className={`font-semibold ${game.steam_review_percent >= 70
                                ? "text-blue-400"
                                : game.steam_review_percent >= 40
                                    ? "text-yellow-400"
                                    : "text-red-400"
                                }`}>
                                {game.steam_review_percent >= 70
                                    ? "Very Positive"
                                    : game.steam_review_percent >= 40
                                        ? "Mixed"
                                        : "Negative"}
                            </div>
                            <div className="text-xs text-zinc-500">
                                {game.steam_review_count.toLocaleString()} reviews
                            </div>
                        </div>
                    </div>
                )}

                {/* IGDB Rating */}
                {game.rating && (
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-400">Rating</span>
                        <div className="flex items-center gap-2">
                            <Star className="w-4 h-4 text-yellow-500 fill-current" />
                            <span className="font-semibold">{game.rating.toFixed(1)}</span>
                        </div>
                    </div>
                )}
            </div>

            {/* Game Info */}
            <div className="p-6 space-y-4">
                {/* Platforms */}
                {game.platforms && (
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-400">Platforms</span>
                        <div className="flex items-center gap-2">
                            {game.platforms.windows && (
                                <Monitor className="w-5 h-5 text-zinc-300" />
                            )}
                            {game.platforms.mac && (
                                <Apple className="w-5 h-5 text-zinc-300" />
                            )}
                            {game.platforms.linux && (
                                <Terminal className="w-5 h-5 text-zinc-300" />
                            )}
                        </div>
                    </div>
                )}

                {/* Release Date */}
                {game.release_date && (
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-400 flex items-center gap-2">
                            <Calendar className="w-4 h-4" />
                            Release Date
                        </span>
                        <span className="text-white">{game.release_date}</span>
                    </div>
                )}

                {/* Developer */}
                {game.developer && (
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-400 flex items-center gap-2">
                            <Building2 className="w-4 h-4" />
                            Developer
                        </span>
                        <span className="text-white truncate ml-4">{game.developer}</span>
                    </div>
                )}

                {/* Publisher */}
                {game.publisher && (
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-400 flex items-center gap-2">
                            <Users className="w-4 h-4" />
                            Publisher
                        </span>
                        <span className="text-white truncate ml-4">{game.publisher}</span>
                    </div>
                )}

                {/* Achievements */}
                {game.achievements_total && game.achievements_total > 0 && (
                    <div className="flex items-center justify-between">
                        <span className="text-zinc-400 flex items-center gap-2">
                            <Trophy className="w-4 h-4" />
                            Achievements
                        </span>
                        <span className="text-white">{game.achievements_total}</span>
                    </div>
                )}

                {/* Playtime */}
                {game.playtime_minutes > 0 && (
                    <div className="flex items-center justify-between pt-4 border-t border-white/5">
                        <span className="text-zinc-400">Your Playtime</span>
                        <span className="text-violet-400 font-semibold">
                            {formatPlaytime(game.playtime_minutes)}
                        </span>
                    </div>
                )}
            </div>

            {/* Genres & Categories */}
            {(game.genres?.length || game.categories?.length) && (
                <div className="p-6 border-t border-white/5 space-y-4">
                    {game.genres && game.genres.length > 0 && (
                        <div>
                            <span className="text-xs text-zinc-500 uppercase tracking-wider">Genres</span>
                            <div className="flex flex-wrap gap-2 mt-2">
                                {game.genres.map((genre) => (
                                    <Link
                                        key={genre}
                                        to={`/store?genre=${encodeURIComponent(genre)}`}
                                        className="px-2 py-1 text-xs bg-zinc-800 text-zinc-300 rounded hover:bg-zinc-700 transition-colors"
                                    >
                                        {genre}
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {game.categories && game.categories.length > 0 && (
                        <div>
                            <span className="text-xs text-zinc-500 uppercase tracking-wider">Features</span>
                            <div className="flex flex-wrap gap-2 mt-2">
                                {game.categories.slice(0, 6).map((cat) => (
                                    <Link
                                        key={cat.id}
                                        to={`/store?category=${encodeURIComponent(cat.description)}`}
                                        className="px-2 py-1 text-xs bg-zinc-800 text-zinc-300 rounded hover:bg-zinc-700 transition-colors"
                                    >
                                        {cat.description}
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
