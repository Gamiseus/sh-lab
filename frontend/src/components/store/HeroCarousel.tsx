import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, Play, Info } from "lucide-react";
import { Game, getImageUrl } from "@/lib/api";

interface HeroCarouselProps {
    games: Game[];
    autoPlayInterval?: number;
}

export function HeroCarousel({ games, autoPlayInterval = 8000 }: HeroCarouselProps) {
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

    // Auto-advance interval comfortably paced at 8000ms
    useEffect(() => {
        if (isPaused || games.length <= 1) return;
        const timer = setInterval(goNext, autoPlayInterval);
        return () => clearInterval(timer);
    }, [isPaused, autoPlayInterval, goNext, games.length]);

    if (!games || games.length === 0) return null;

    const currentGame = games[currentIndex];
    const prevIndex = (currentIndex - 1 + games.length) % games.length;
    const nextIndex = (currentIndex + 1) % games.length;

    const prevGame = games[prevIndex];
    const nextGame = games[nextIndex];

    return (
        <section
            className="group relative w-full overflow-hidden rounded-2xl py-2 select-none"
            onMouseEnter={() => setIsPaused(true)}
            onMouseLeave={() => setIsPaused(false)}
        >
            {/* 3D Card-Slot Carousel Layout */}
            <div className="relative h-[480px] w-full flex items-center justify-center">
                {/* Left Side Background Preview Card */}
                {games.length > 1 && (
                    <div
                        onClick={goPrev}
                        className="absolute left-0 w-[24%] h-[82%] rounded-2xl overflow-hidden scale-95 opacity-40 hover:opacity-75 transition-all duration-500 cursor-pointer hidden md:block z-10 border border-white/5 shadow-xl"
                    >
                        <img
                            src={getImageUrl(prevGame.header_image || prevGame.cover_url)}
                            alt={`Previous: ${prevGame.title}`}
                            className="w-full h-full object-cover filter blur-[1px]"
                        />
                        <div className="absolute inset-0 bg-black/60 hover:bg-black/30 transition-colors" />
                        <div className="absolute bottom-4 left-4 right-4 text-xs font-semibold text-white/80 truncate">
                            {prevGame.title}
                        </div>
                    </div>
                )}

                {/* Center Active Featured Card */}
                <div className="relative w-full md:w-[82%] h-full rounded-2xl overflow-hidden border border-white/10 shadow-2xl z-20 bg-zinc-950">
                    {/* Background Artwork */}
                    {games.map((game, idx) => {
                        const imgUrl = getImageUrl(game.header_image || game.cover_url);
                        return (
                            <div
                                key={game.id}
                                className={`
                                    absolute inset-0 transition-opacity duration-700 ease-in-out
                                    ${idx === currentIndex ? "opacity-100" : "opacity-0 pointer-events-none"}
                                `}
                            >
                                {imgUrl ? (
                                    <img
                                        src={imgUrl}
                                        alt={game.title}
                                        className="w-full h-full object-cover"
                                    />
                                ) : (
                                    <div className="w-full h-full bg-gradient-to-br from-violet-950 via-zinc-900 to-indigo-950" />
                                )}
                            </div>
                        );
                    })}

                    {/* Top Subtle Vignette */}
                    <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-black/60 to-transparent z-10" />

                    {/* Top Right Badges */}
                    <div className="absolute top-6 right-6 z-20 flex items-center gap-2">
                        {currentGame.metacritic_score && (
                            <span className={`
                                px-3 py-1 text-xs font-bold rounded-lg shadow-lg
                                ${currentGame.metacritic_score >= 75 ? "bg-green-600 text-white" : "bg-yellow-600 text-white"}
                            `}>
                                {currentGame.metacritic_score} Metacritic
                            </span>
                        )}
                        {currentGame.steam_review_percent !== undefined && (
                            <span className="px-3 py-1 text-xs font-bold rounded-lg bg-blue-600/90 text-white shadow-lg backdrop-blur-sm">
                                {currentGame.steam_review_percent}% Steam
                            </span>
                        )}
                    </div>

                    {/* Compact Bottom Overlay for Game Details */}
                    <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/95 via-black/80 to-transparent p-6 md:p-8 z-20">
                        <div className="max-w-4xl space-y-3">
                            {/* Tags & Genres */}
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className="px-2.5 py-0.5 text-xs font-bold tracking-wider uppercase bg-violet-600 text-white rounded">
                                    Featured
                                </span>
                                {currentGame.genres?.slice(0, 3).map((genre) => (
                                    <span
                                        key={genre}
                                        className="px-2.5 py-0.5 text-xs font-medium bg-white/10 backdrop-blur-md rounded text-white/90"
                                    >
                                        {genre}
                                    </span>
                                ))}
                            </div>

                            {/* Game Title */}
                            <h1 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight truncate drop-shadow-md">
                                {currentGame.title}
                            </h1>

                            {/* Short Description */}
                            <p className="text-sm md:text-base text-zinc-300 line-clamp-2 leading-relaxed drop-shadow">
                                {currentGame.short_description || currentGame.description || "Discover this featured title in our collection."}
                            </p>

                            {/* Actions Row */}
                            <div className="flex items-center gap-4 pt-1">
                                <Link
                                    to={`/games/${currentGame.id}`}
                                    className="
                                        flex items-center gap-2.5 px-6 py-3
                                        bg-gradient-to-r from-violet-600 to-indigo-600
                                        hover:from-violet-500 hover:to-indigo-500
                                        text-white font-bold text-sm md:text-base rounded-xl
                                        shadow-lg shadow-violet-600/30
                                        transition-all duration-300 hover:scale-[1.02]
                                    "
                                >
                                    <Play className="w-4 h-4 fill-current" />
                                    Play Now
                                </Link>
                                <Link
                                    to={`/games/${currentGame.id}`}
                                    className="
                                        flex items-center gap-2 px-5 py-3
                                        bg-white/10 hover:bg-white/20
                                        backdrop-blur-md
                                        text-white font-medium text-sm md:text-base rounded-xl
                                        border border-white/10 hover:border-white/20
                                        transition-all duration-300
                                    "
                                >
                                    <Info className="w-4 h-4" />
                                    More Info
                                </Link>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Side Background Preview Card */}
                {games.length > 1 && (
                    <div
                        onClick={goNext}
                        className="absolute right-0 w-[24%] h-[82%] rounded-2xl overflow-hidden scale-95 opacity-40 hover:opacity-75 transition-all duration-500 cursor-pointer hidden md:block z-10 border border-white/5 shadow-xl"
                    >
                        <img
                            src={getImageUrl(nextGame.header_image || nextGame.cover_url)}
                            alt={`Next: ${nextGame.title}`}
                            className="w-full h-full object-cover filter blur-[1px]"
                        />
                        <div className="absolute inset-0 bg-black/60 hover:bg-black/30 transition-colors" />
                        <div className="absolute bottom-4 left-4 right-4 text-xs font-semibold text-white/80 truncate text-right">
                            {nextGame.title}
                        </div>
                    </div>
                )}
            </div>

            {/* Navigation Arrows */}
            <button
                onClick={goPrev}
                aria-label="Previous featured game"
                className="
                    absolute left-2 md:left-4 top-1/2 -translate-y-1/2 z-30
                    w-12 h-12 rounded-full
                    bg-black/70 hover:bg-violet-600/90 backdrop-blur-md
                    flex items-center justify-center
                    text-white opacity-80 group-hover:opacity-100
                    hover:scale-110 transition-all shadow-xl
                    border border-white/15
                "
            >
                <ChevronLeft className="w-6 h-6" />
            </button>
            <button
                onClick={goNext}
                aria-label="Next featured game"
                className="
                    absolute right-2 md:right-4 top-1/2 -translate-y-1/2 z-30
                    w-12 h-12 rounded-full
                    bg-black/70 hover:bg-violet-600/90 backdrop-blur-md
                    flex items-center justify-center
                    text-white opacity-80 group-hover:opacity-100
                    hover:scale-110 transition-all shadow-xl
                    border border-white/15
                "
            >
                <ChevronRight className="w-6 h-6" />
            </button>

            {/* Dots Navigation */}
            <div className="flex items-center justify-center gap-2 mt-4">
                {games.map((_, idx) => (
                    <button
                        key={idx}
                        onClick={() => goTo(idx)}
                        aria-label={`Go to slide ${idx + 1}`}
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
            {!isPaused && games.length > 1 && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/40">
                    <div
                        className="h-full bg-gradient-to-r from-violet-500 to-indigo-500"
                        style={{
                            animation: `carouselProgress ${autoPlayInterval}ms linear infinite`,
                        }}
                    />
                </div>
            )}

            <style>{`
                @keyframes carouselProgress {
                    from { width: 0%; }
                    to { width: 100%; }
                }
            `}</style>
        </section>
    );
}
