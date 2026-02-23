import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, Play, Info } from "lucide-react";
import { Game, getImageUrl } from "@/lib/api";

interface HeroCarouselProps {
    games: Game[];
    autoPlayInterval?: number;
}

export function HeroCarousel({ games, autoPlayInterval = 6000 }: HeroCarouselProps) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isPaused, setIsPaused] = useState(false);

    const goTo = useCallback((index: number) => {
        setCurrentIndex(index);
    }, []);

    const goNext = useCallback(() => {
        setCurrentIndex((prev) => (prev + 1) % games.length);
    }, [games.length]);

    const goPrev = useCallback(() => {
        setCurrentIndex((prev) => (prev - 1 + games.length) % games.length);
    }, [games.length]);

    // Auto-play
    useEffect(() => {
        if (isPaused || games.length <= 1) return;
        const timer = setInterval(goNext, autoPlayInterval);
        return () => clearInterval(timer);
    }, [isPaused, autoPlayInterval, goNext, games.length]);

    if (games.length === 0) return null;

    const currentGame = games[currentIndex];

    return (
        <section
            className="relative h-[500px] w-full overflow-hidden rounded-2xl"
            onMouseEnter={() => setIsPaused(true)}
            onMouseLeave={() => setIsPaused(false)}
        >
            {/* Background Images - all stacked, only one visible */}
            {games.map((game, idx) => {
                const imgUrl = getImageUrl(game.header_image || game.cover_url);
                return (
                    <div
                        key={game.id}
                        className={`
              absolute inset-0 transition-opacity duration-1000 ease-in-out
              ${idx === currentIndex ? "opacity-100" : "opacity-0"}
            `}
                    >
                        {imgUrl ? (
                            <img
                                src={imgUrl}
                                alt={game.title}
                                className="w-full h-full object-cover"
                            />
                        ) : (
                            <div className="w-full h-full bg-gradient-to-br from-violet-900 to-indigo-900" />
                        )}
                    </div>
                );
            })}

            {/* Gradient Overlays */}
            <div className="absolute inset-0 bg-gradient-to-r from-black/90 via-black/50 to-transparent" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30" />

            {/* Content */}
            <div className="absolute inset-0 flex items-center">
                <div className="max-w-2xl px-12 space-y-6">
                    {/* Tags */}
                    <div className="flex items-center gap-3">
                        {currentGame.genres?.slice(0, 3).map((genre) => (
                            <span
                                key={genre}
                                className="px-3 py-1 text-xs font-medium bg-white/10 backdrop-blur-sm rounded-full text-white/80"
                            >
                                {genre}
                            </span>
                        ))}
                        {currentGame.metacritic_score && (
                            <span className={`
                px-3 py-1 text-xs font-bold rounded-full
                ${currentGame.metacritic_score >= 75 ? "bg-green-600" : "bg-yellow-600"}
              `}>
                                {currentGame.metacritic_score} Metacritic
                            </span>
                        )}
                    </div>

                    {/* Title */}
                    <h1 className="text-5xl font-bold text-white leading-tight tracking-tight">
                        {currentGame.title}
                    </h1>

                    {/* Description */}
                    <p className="text-lg text-zinc-300 line-clamp-3 leading-relaxed">
                        {currentGame.short_description || currentGame.description || "Discover this amazing game in our collection."}
                    </p>

                    {/* Actions */}
                    <div className="flex items-center gap-4 pt-2">
                        <Link
                            to={`/games/${currentGame.id}`}
                            className="
                flex items-center gap-3 px-8 py-4
                bg-gradient-to-r from-violet-600 to-indigo-600
                hover:from-violet-500 hover:to-indigo-500
                text-white font-bold text-lg rounded-xl
                shadow-lg shadow-violet-500/25
                transition-all duration-300 hover:scale-105
              "
                        >
                            <Play className="w-5 h-5 fill-current" />
                            Play Now
                        </Link>
                        <Link
                            to={`/games/${currentGame.id}`}
                            className="
                flex items-center gap-3 px-8 py-4
                bg-white/10 hover:bg-white/20
                backdrop-blur-sm
                text-white font-semibold text-lg rounded-xl
                border border-white/10 hover:border-white/20
                transition-all duration-300
              "
                        >
                            <Info className="w-5 h-5" />
                            More Info
                        </Link>
                    </div>
                </div>
            </div>

            {/* Navigation Arrows */}
            <button
                onClick={goPrev}
                className="
          absolute left-4 top-1/2 -translate-y-1/2
          w-12 h-12 rounded-full
          bg-black/50 hover:bg-black/70 backdrop-blur-sm
          flex items-center justify-center
          text-white opacity-0 group-hover:opacity-100
          hover:opacity-100 transition-opacity
          border border-white/10
        "
            >
                <ChevronLeft className="w-6 h-6" />
            </button>
            <button
                onClick={goNext}
                className="
          absolute right-4 top-1/2 -translate-y-1/2
          w-12 h-12 rounded-full
          bg-black/50 hover:bg-black/70 backdrop-blur-sm
          flex items-center justify-center
          text-white opacity-0 group-hover:opacity-100
          hover:opacity-100 transition-opacity
          border border-white/10
        "
            >
                <ChevronRight className="w-6 h-6" />
            </button>

            {/* Dots Navigation */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2">
                {games.map((_, idx) => (
                    <button
                        key={idx}
                        onClick={() => goTo(idx)}
                        className={`
              h-2 rounded-full transition-all duration-300
              ${idx === currentIndex
                                ? "w-8 bg-violet-500"
                                : "w-2 bg-white/30 hover:bg-white/50"
                            }
            `}
                    />
                ))}
            </div>

            {/* Progress Bar */}
            {!isPaused && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/30">
                    <div
                        className="h-full bg-gradient-to-r from-violet-500 to-indigo-500"
                        style={{
                            animation: `progress ${autoPlayInterval}ms linear`,
                            animationIterationCount: "infinite",
                        }}
                    />
                </div>
            )}

            <style>{`
        @keyframes progress {
          from { width: 0%; }
          to { width: 100%; }
        }
      `}</style>
        </section>
    );
}
