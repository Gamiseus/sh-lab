import { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronLeft, ChevronRight, Play, Info, Star, Sparkles, Download } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { Game, getImageUrl, formatPrice } from "@/lib/api";
import { useLibraryStore, LocalVerificationResult } from "@/stores/LibraryStore";

interface HeroCarouselProps {
    games: Game[];
    autoPlayInterval?: number;
    hidePrice?: boolean;
}

export function HeroCarousel({ games, autoPlayInterval = 8000, hidePrice = false }: HeroCarouselProps) {
    const navigate = useNavigate();
    const { installedGames, addToLibrary, addInstalledGame } = useLibraryStore();
    const [currentIndex, setCurrentIndex] = useState(0);
    const [activeScreenshotIdx, setActiveScreenshotIdx] = useState<number | null>(null);
    const [isPaused, setIsPaused] = useState(false);

    const goTo = useCallback((index: number) => {
        setCurrentIndex(index);
        setActiveScreenshotIdx(null);
    }, []);

    const goNext = useCallback(() => {
        setCurrentIndex((prev) => (prev + 1) % games.length);
        setActiveScreenshotIdx(null);
    }, [games.length]);

    const goPrev = useCallback(() => {
        setCurrentIndex((prev) => (prev - 1 + games.length) % games.length);
        setActiveScreenshotIdx(null);
    }, [games.length]);

    // Auto-advance interval comfortably paced
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

    // Determine current display artwork (either hovered screenshot thumbnail or game header/cover)
    const screenshots: string[] = (currentGame.screenshots || [])
        .slice(0, 4)
        .map((s: any) => {
            if (typeof s === "string") return s;
            return s.path_full || s.full || s.path_thumbnail || s.thumbnail || "";
        })
        .filter(Boolean);

    const activeImageSrc = activeScreenshotIdx !== null && screenshots[activeScreenshotIdx]
        ? getImageUrl(screenshots[activeScreenshotIdx])
        : getImageUrl(currentGame.header_image || currentGame.cover_url);

    // Calculate original price if discounted
    const hasDiscount = Boolean(currentGame.discount_percent && currentGame.discount_percent > 0);
    const originalPrice = hasDiscount && currentGame.price_cents
        ? Math.round(currentGame.price_cents / (1 - (currentGame.discount_percent! / 100)))
        : null;

    // Supported platforms list
    const platformList: string[] = [];
    if (currentGame.platforms?.windows) platformList.push("Windows");
    if (currentGame.platforms?.mac) platformList.push("macOS");
    if (currentGame.platforms?.linux) platformList.push("Linux");

    const isInstalled = Boolean(currentGame && installedGames[currentGame.id]);

    const handlePlayGame = async (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        const localGame = installedGames[currentGame.id];
        if (localGame?.path) {
            try {
                await invoke("launch_game_command", {
                    gamePath: localGame.path,
                    customArgs: null,
                });
                return;
            } catch (err) {
                console.error("Failed to launch game directly:", err);
            }
        }
        navigate(`/games/${currentGame.id}`);
    };

    const handleDownload = async (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!currentGame) return;

        // 1. Register in user's library (R2 requirement)
        await addToLibrary(currentGame.id, {
            id: currentGame.id,
            title: currentGame.title,
            cover_url: currentGame.cover_url,
            header_image: currentGame.header_image,
            background_url: (currentGame as any).background_url || currentGame.header_image,
            description: currentGame.short_description || currentGame.description,
            developer: currentGame.developer,
            publisher: currentGame.publisher,
            release_date: currentGame.release_date,
            rating: currentGame.rating,
            genres: currentGame.genres,
            steam_app_id: currentGame.steam_app_id,
            playtime_minutes: currentGame.playtime_minutes || 0,
        });

        // 2. Pre-flight check on local disk (R3 requirement)
        try {
            const configuredPaths: string[] = JSON.parse(
                localStorage.getItem("sh_library_paths") ||
                localStorage.getItem("library-paths") ||
                '["c:\\\\Users\\\\Administrator\\\\Documents\\\\Projects\\\\sh-lab\\\\data\\\\games", "E:\\\\projects\\\\sh-lab\\\\data\\\\games"]'
            );
            const verifyResult = await invoke<LocalVerificationResult>("verify_local_game_command", {
                libraryPaths: configuredPaths,
                gameId: currentGame.id,
                gameTitle: currentGame.title,
                steamAppId: currentGame.steam_app_id || null,
                expectedExe: (currentGame as any).executable_path || null,
            });

            if (verifyResult.found && verifyResult.verified_binary && verifyResult.path) {
                addInstalledGame({
                    id: currentGame.id,
                    path: verifyResult.path,
                });
                navigate(`/games/${currentGame.id}`);
                return;
            } else if (verifyResult.found && !verifyResult.verified_binary) {
                console.warn(`Local directory found for "${currentGame.title}" but executable signature check failed. Redirecting to network installer.`);
            }
        } catch (err) {
            console.warn("Pre-flight check in HeroCarousel:", err);
        }

        // 3. Dispatch installation request by routing to GameDetails with ?install=1
        navigate(`/games/${currentGame.id}?install=1`);
    };

    return (
        <section
            className="group relative w-full overflow-hidden rounded-3xl py-2 select-none"
            onMouseEnter={() => setIsPaused(true)}
            onMouseLeave={() => {
                setIsPaused(false);
                setActiveScreenshotIdx(null);
            }}
            aria-label="Featured Games Carousel"
        >
            {/* 3D Multi-Card Track with Looping Desaturated Side Cards */}
            <div className="relative min-h-[460px] md:min-h-[480px] w-full flex items-center justify-center">

                {/* Left Side Background Preview Card (Desaturated) */}
                {games.length > 1 && (
                    <div
                        onClick={goPrev}
                        className="
                            absolute left-0 w-[22%] lg:w-[24%] h-[82%]
                            rounded-2xl overflow-hidden cursor-pointer hidden md:block z-10
                            border border-white/10 shadow-2xl transition-all duration-500
                            filter grayscale-[60%] opacity-40 hover:opacity-85 hover:grayscale-0 hover:scale-[1.02]
                        "
                        title={`Previous: ${prevGame.title}`}
                    >
                        <img
                            src={getImageUrl(prevGame.header_image || prevGame.cover_url)}
                            alt={prevGame.title}
                            className="w-full h-full object-cover filter blur-[0.5px]"
                        />
                        <div className="absolute inset-0 bg-black/60 hover:bg-black/25 transition-colors" />
                        <div className="absolute bottom-4 left-4 right-4 text-xs font-bold text-white/90 truncate drop-shadow-md">
                            {prevGame.title}
                        </div>
                    </div>
                )}

                {/* Center Active Featured Card (Sharp Contained Split Layout) */}
                <div className="relative w-full md:w-[78%] lg:w-[74%] h-full rounded-2xl overflow-hidden border border-white/10 bg-zinc-950/95 shadow-2xl z-20 backdrop-blur-xl">
                    <div className="flex flex-col md:flex-row h-full min-h-[460px]">

                        {/* Left: Constrained Media Area (Prevents Low-Res Stretch) */}
                        <div className="relative md:w-[60%] aspect-video md:aspect-auto md:min-h-[460px] overflow-hidden bg-black flex items-center justify-center">
                            {/* Ambient Blurred Backdrop for mood & aspect safety */}
                            {activeImageSrc && (
                                <img
                                    src={activeImageSrc}
                                    alt=""
                                    aria-hidden="true"
                                    className="absolute inset-0 w-full h-full object-cover filter blur-3xl opacity-25 scale-125 transform pointer-events-none"
                                />
                            )}

                            {/* Foreground Sharp Image */}
                            {activeImageSrc ? (
                                <img
                                    key={activeImageSrc}
                                    src={activeImageSrc}
                                    alt={currentGame.title}
                                    className="relative z-10 w-full h-full object-cover transition-opacity duration-300 ease-out"
                                />
                            ) : (
                                <div className="relative z-10 w-full h-full bg-gradient-to-br from-violet-950 via-zinc-900 to-indigo-950 flex items-center justify-center">
                                    <span className="text-4xl font-extrabold text-white/30">{currentGame.title}</span>
                                </div>
                            )}

                            {/* Top Shadow Vignette */}
                            <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-black/80 via-black/30 to-transparent z-20 pointer-events-none" />

                            {/* Bottom Shadow Vignette */}
                            <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-zinc-950 via-zinc-950/50 to-transparent z-20 pointer-events-none" />

                            {/* Floating Rating Badges */}
                            <div className="absolute top-4 left-4 z-30 flex items-center gap-2">
                                <span className="flex items-center gap-1.5 px-3 py-1 bg-violet-600 text-white text-xs font-bold rounded-lg shadow-lg tracking-wide uppercase">
                                    <Sparkles className="w-3.5 h-3.5 fill-current" />
                                    Featured
                                </span>
                            </div>

                            <div className="absolute top-4 right-4 z-30 flex items-center gap-2">
                                {currentGame.metacritic_score && (
                                    <span
                                        className={`px-2.5 py-1 text-xs font-bold rounded-lg shadow-md border border-white/10 ${
                                            currentGame.metacritic_score >= 75
                                                ? "bg-emerald-600/90 text-white"
                                                : "bg-yellow-600/90 text-white"
                                        }`}
                                        title="Metacritic Score"
                                    >
                                        {currentGame.metacritic_score} Metascore
                                    </span>
                                )}
                                {currentGame.steam_review_percent !== undefined && (
                                    <span
                                        className="px-2.5 py-1 text-xs font-bold rounded-lg bg-blue-600/90 text-white shadow-md border border-white/10 backdrop-blur-sm"
                                        title="Steam Positive Reviews"
                                    >
                                        {currentGame.steam_review_percent}% Steam
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* Right: Info, Preview Strip & Actions Panel */}
                        <div className="md:w-[40%] p-6 md:p-7 flex flex-col justify-between bg-zinc-900/60 border-t md:border-t-0 md:border-l border-white/10 z-20">
                            <div className="space-y-3.5">
                                {/* Genre Chips */}
                                <div className="flex flex-wrap items-center gap-1.5">
                                    {currentGame.genres?.slice(0, 3).map((genre) => (
                                        <span
                                            key={genre}
                                            className="px-2.5 py-0.5 text-xs font-medium rounded-md bg-white/10 text-zinc-300 border border-white/5"
                                        >
                                            {genre}
                                        </span>
                                    ))}
                                </div>

                                {/* Title */}
                                <div>
                                    <h2 className="text-2xl lg:text-3xl font-extrabold text-white tracking-tight line-clamp-2">
                                        {currentGame.title}
                                    </h2>
                                    {currentGame.steam_review_desc && (
                                        <p className="text-xs font-semibold text-blue-400 mt-1 flex items-center gap-1">
                                            <Star className="w-3.5 h-3.5 fill-current" />
                                            {currentGame.steam_review_desc} Reviews
                                        </p>
                                    )}
                                </div>

                                {/* Summary */}
                                <p className="text-xs lg:text-sm text-zinc-400 line-clamp-3 leading-relaxed">
                                    {currentGame.short_description || currentGame.description || "Discover this highlighted title in the store catalog with authentic achievements and updates."}
                                </p>

                                {/* Gameplay Previews (Steam-style) */}
                                {screenshots.length > 0 && (
                                    <div className="space-y-1.5 pt-1">
                                        <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">
                                            Gameplay Previews
                                        </p>
                                        <div className="grid grid-cols-4 gap-2">
                                            {screenshots.map((s, idx) => (
                                                <button
                                                    key={idx}
                                                    type="button"
                                                    onMouseEnter={() => setActiveScreenshotIdx(idx)}
                                                    onClick={() => setActiveScreenshotIdx(idx)}
                                                    className={`relative aspect-video rounded-lg overflow-hidden border transition-all ${
                                                        activeScreenshotIdx === idx
                                                            ? "border-violet-500 ring-2 ring-violet-500/40 scale-105"
                                                            : "border-white/10 hover:border-white/40 opacity-70 hover:opacity-100"
                                                    }`}
                                                >
                                                    <img
                                                        src={getImageUrl(s)}
                                                        alt={`Screenshot ${idx + 1}`}
                                                        className="w-full h-full object-cover"
                                                        loading="lazy"
                                                    />
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Pricing & CTA Buttons */}
                            <div className="pt-5 mt-3 border-t border-white/5 space-y-3">
                                {!hidePrice && (
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            {hasDiscount && (
                                                <span className="px-2 py-0.5 text-xs font-extrabold bg-emerald-500 text-white rounded">
                                                    -{currentGame.discount_percent}%
                                                </span>
                                            )}
                                            <div className="flex items-baseline gap-1.5">
                                                {originalPrice && (
                                                    <span className="text-xs text-zinc-500 line-through">
                                                        {formatPrice(originalPrice)}
                                                    </span>
                                                )}
                                                <span className="text-lg font-extrabold text-white">
                                                    {formatPrice(currentGame.price_cents)}
                                                </span>
                                            </div>
                                        </div>

                                        {platformList.length > 0 && (
                                            <div className="text-xs text-zinc-500">
                                                {platformList.join(" • ")}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {hidePrice && platformList.length > 0 && (
                                    <div className="flex items-center justify-end text-xs text-zinc-500">
                                        {platformList.join(" • ")}
                                    </div>
                                )}

                                <div className="flex items-center gap-2.5">
                                    {isInstalled ? (
                                        <button
                                            type="button"
                                            onClick={handlePlayGame}
                                            className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-emerald-600/25 transition-all duration-200 hover:scale-[1.02]"
                                            title="Play Game"
                                        >
                                            <Play className="w-4 h-4 fill-current" />
                                            Play Now
                                        </button>
                                    ) : (
                                        <button
                                            type="button"
                                            onClick={handleDownload}
                                            className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-violet-600/25 transition-all duration-200 hover:scale-[1.02]"
                                            title="Download & Install"
                                        >
                                            <Download className="w-4 h-4" />
                                            Download
                                        </button>
                                    )}

                                    <Link
                                        to={`/games/${currentGame.id}`}
                                        className="flex items-center justify-center gap-1.5 px-4 py-2.5 bg-zinc-800/90 hover:bg-zinc-700 text-zinc-200 hover:text-white rounded-xl border border-white/10 text-sm font-semibold transition-all hover:scale-[1.02]"
                                        title="View Store Page"
                                    >
                                        <Info className="w-4 h-4 text-zinc-400 group-hover:text-white" />
                                        <span>Store Page</span>
                                    </Link>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right Side Background Preview Card (Desaturated) */}
                {games.length > 1 && (
                    <div
                        onClick={goNext}
                        className="
                            absolute right-0 w-[22%] lg:w-[24%] h-[82%]
                            rounded-2xl overflow-hidden cursor-pointer hidden md:block z-10
                            border border-white/10 shadow-2xl transition-all duration-500
                            filter grayscale-[60%] opacity-40 hover:opacity-85 hover:grayscale-0 hover:scale-[1.02]
                        "
                        title={`Next: ${nextGame.title}`}
                    >
                        <img
                            src={getImageUrl(nextGame.header_image || nextGame.cover_url)}
                            alt={nextGame.title}
                            className="w-full h-full object-cover filter blur-[0.5px]"
                        />
                        <div className="absolute inset-0 bg-black/60 hover:bg-black/25 transition-colors" />
                        <div className="absolute bottom-4 left-4 right-4 text-xs font-bold text-white/90 truncate text-right drop-shadow-md">
                            {nextGame.title}
                        </div>
                    </div>
                )}
            </div>

            {/* Navigation Arrows */}
            <button
                onClick={goPrev}
                aria-label="Previous featured game"
                className="absolute left-2 md:left-4 top-1/2 -translate-y-1/2 z-30 w-11 h-11 rounded-full bg-zinc-900/90 hover:bg-violet-600 text-white flex items-center justify-center shadow-xl border border-white/15 hover:border-violet-500 transition-all duration-200 hover:scale-110"
            >
                <ChevronLeft className="w-5 h-5" />
            </button>
            <button
                onClick={goNext}
                aria-label="Next featured game"
                className="absolute right-2 md:right-4 top-1/2 -translate-y-1/2 z-30 w-11 h-11 rounded-full bg-zinc-900/90 hover:bg-violet-600 text-white flex items-center justify-center shadow-xl border border-white/15 hover:border-violet-500 transition-all duration-200 hover:scale-110"
            >
                <ChevronRight className="w-5 h-5" />
            </button>

            {/* Dots Indicator */}
            <div className="flex items-center justify-center gap-2 mt-4">
                {games.map((_, idx) => (
                    <button
                        key={idx}
                        onClick={() => goTo(idx)}
                        aria-label={`Go to featured slide ${idx + 1}`}
                        className={`h-1.5 rounded-full transition-all duration-300 ${
                            idx === currentIndex
                                ? "w-8 bg-violet-500 shadow-md shadow-violet-500/50"
                                : "w-2.5 bg-white/20 hover:bg-white/40"
                        }`}
                    />
                ))}
            </div>
        </section>
    );
}
