import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { ArrowLeft, ExternalLink, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { storeAPI, getImageUrl, playtimeAPI } from "@/lib/api";
import { MediaGallery } from "@/components/store/MediaGallery";
import { GameInfoPanel } from "@/components/store/GameInfoPanel";
import { ReviewList } from "@/components/reviews/ReviewList";

type Tab = "about" | "requirements" | "achievements" | "reviews";

interface InstallProgress {
    game_id: number;
    current_file: string;
    files_done: number;
    files_total: number;
    bytes_done: number;
    bytes_total: number;
    percent: number;
}

interface LaunchResult {
    success: boolean;
    game_id: number;
    message: string;
    pid?: number;
}

interface PlaytimeUpdate {
    game_id: number;
    session_minutes: number;
    total_minutes: number;
    last_played: string;
}

type GameState = "not_installed" | "installing" | "installed" | "playing";

export function GameDetailsPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState<Tab>("about");
    const [gameState, setGameState] = useState<GameState>("not_installed");
    const [installProgress, setInstallProgress] = useState<InstallProgress | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [revealedAchievements, setRevealedAchievements] = useState<Set<string>>(new Set());

    const { data: game, isLoading, error: fetchError } = useQuery({
        queryKey: ["game", id],
        queryFn: () => storeAPI.getGame(Number(id)),
        enabled: !!id,
    });

    // Get library path from settings
    const getLibraryPath = (): string => {
        try {
            const paths = JSON.parse(localStorage.getItem("library-paths") || "[]");
            return paths[0] || "E:\\Games";
        } catch {
            return "E:\\Games";
        }
    };

    // Listen for install progress events
    useEffect(() => {
        const unlisten = listen<InstallProgress>("install-progress", (event) => {
            setInstallProgress(event.payload);
            if (event.payload.percent >= 100) {
                setGameState("installed");
                setInstallProgress(null);
                setSuccessMessage("Game installed successfully!");
                setTimeout(() => setSuccessMessage(null), 5000);
            }
        });

        return () => {
            unlisten.then((fn) => fn());
        };
    }, []);

    // Check if game is installed on mount
    useEffect(() => {
        const checkInstallStatus = async () => {
            if (!game) return;

            try {
                // Check if game is running
                const isRunning = await invoke<boolean>("is_game_running_command", {
                    gameId: game.id,
                });

                if (isRunning) {
                    setGameState("playing");
                    return;
                }

                // TODO: Check if game is installed by looking for sh_meta.json
                // For now, we'll assume not installed if not running
                // A proper check would scan the library path
            } catch (err) {
                console.error("Failed to check game status:", err);
            }
        };

        checkInstallStatus();
    }, [game]);

    const handleInstall = async () => {
        if (!game) return;
        setError(null);
        setGameState("installing");
        setInstallProgress({
            game_id: game.id,
            current_file: "Preparing...",
            files_done: 0,
            files_total: 0,
            bytes_done: 0,
            bytes_total: 0,
            percent: 0
        });

        try {
            await invoke("install_game_command", {
                backendUrl: "http://localhost:8000",
                gameId: game.id,
                libraryPath: getLibraryPath(),
            });
            setGameState("installed");
            setSuccessMessage("Game installed successfully!");
            setTimeout(() => setSuccessMessage(null), 5000);
        } catch (err) {
            console.error("Install failed:", err);
            setError(err instanceof Error ? err.message : String(err));
            setGameState("not_installed");
        } finally {
            setInstallProgress(null);
        }
    };

    const handleLaunch = async () => {
        if (!game) return;
        setError(null);

        try {
            const libraryPath = getLibraryPath();
            // Game path is typically library_path/game_folder
            const gamePath = `${libraryPath}\\${game.title.replace(/[<>:"/\\|?*]/g, "")}`;

            const result = await invoke<LaunchResult>("launch_game_command", {
                gamePath,
                customArgs: null,
            });

            if (result.success) {
                setGameState("playing");
                setSuccessMessage(result.message);
                setTimeout(() => setSuccessMessage(null), 3000);
            } else {
                setError(result.message);
            }
        } catch (err) {
            console.error("Launch failed:", err);
            setError(err instanceof Error ? err.message : String(err));
        }
    };

    const handleStopGame = async () => {
        if (!game) return;

        try {
            const result = await invoke<PlaytimeUpdate>("stop_game_session_command", {
                gameId: game.id,
            });

            setGameState("installed");
            setSuccessMessage(`Played for ${result.session_minutes} minutes`);
            setTimeout(() => setSuccessMessage(null), 5000);

            // Sync playtime to server
            try {
                await playtimeAPI.syncPlaytime({
                    game_id: game.id,
                    session_minutes: result.session_minutes,
                    total_local_minutes: result.total_minutes,
                    last_played: result.last_played,
                });
            } catch (syncErr) {
                console.error("Failed to sync playtime:", syncErr);
            }
        } catch (err) {
            console.error("Stop game failed:", err);
            setError(err instanceof Error ? err.message : String(err));
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (fetchError || !game) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-center">
                <h2 className="text-2xl font-bold text-white mb-2">Game Not Found</h2>
                <p className="text-zinc-500 mb-6">The game you're looking for doesn't exist.</p>
                <button
                    onClick={() => navigate("/store")}
                    className="px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-lg font-medium transition-colors"
                >
                    Back to Store
                </button>
            </div>
        );
    }

    const backgroundImage = getImageUrl(game.header_image || game.cover_url);

    return (
        <div className="min-h-screen">
            {/* Status Messages */}
            {(error || successMessage) && (
                <div className="fixed top-4 right-4 z-50 max-w-md">
                    {error && (
                        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 shadow-lg backdrop-blur-sm">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <span className="text-sm">{error}</span>
                        </div>
                    )}
                    {successMessage && (
                        <div className="flex items-center gap-3 p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 shadow-lg backdrop-blur-sm">
                            <CheckCircle className="w-5 h-5 flex-shrink-0" />
                            <span className="text-sm">{successMessage}</span>
                        </div>
                    )}
                </div>
            )}

            {/* Install Progress Overlay */}
            {gameState === "installing" && installProgress && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 flex items-center justify-center">
                    <div className="bg-zinc-900 border border-white/10 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
                        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-3">
                            <Loader2 className="w-6 h-6 animate-spin text-violet-400" />
                            Installing {game.title}
                        </h3>

                        <div className="space-y-4">
                            {/* Progress bar */}
                            <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-violet-600 to-indigo-600 transition-all duration-300"
                                    style={{ width: `${installProgress.percent}%` }}
                                />
                            </div>

                            <div className="flex justify-between text-sm">
                                <span className="text-zinc-400 truncate max-w-[200px]">
                                    {installProgress.current_file}
                                </span>
                                <span className="text-white font-medium">
                                    {Math.round(installProgress.percent)}%
                                </span>
                            </div>

                            {installProgress.files_total > 0 && (
                                <p className="text-xs text-zinc-500">
                                    {installProgress.files_done} / {installProgress.files_total} files
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Hero Banner */}
            <div className="relative h-[400px] overflow-hidden">
                {backgroundImage && (
                    <>
                        <img
                            src={backgroundImage}
                            alt=""
                            className="absolute inset-0 w-full h-full object-cover scale-110 blur-sm"
                        />
                        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-background" />
                    </>
                )}

                <button
                    onClick={() => navigate(-1)}
                    className="absolute top-6 left-6 z-10 flex items-center gap-2 px-4 py-2 bg-black/40 hover:bg-black/60 backdrop-blur-sm rounded-lg text-white transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    Back
                </button>

                <div className="absolute bottom-0 left-0 right-0 p-8 z-20">
                    <div className="max-w-5xl">
                        <div className="flex items-center gap-2 mb-4 flex-wrap">
                            {(game.genres || []).slice(0, 3).map((genre) => (
                                <Link
                                    key={genre}
                                    to={`/store?genre=${encodeURIComponent(genre)}`}
                                    className="px-3 py-1 text-xs font-medium bg-white/10 backdrop-blur-sm rounded-full text-white/80 hover:bg-white/20 transition-colors cursor-pointer relative z-50 pointer-events-auto"
                                >
                                    {genre}
                                </Link>
                            ))}
                        </div>

                        <h1 className="text-5xl font-bold text-white mb-3 tracking-tight">
                            {game.title}
                        </h1>

                        {game.developer && (
                            <p className="text-lg text-zinc-400">
                                by <span className="text-white">{game.developer}</span>
                                {game.publisher && game.publisher !== game.developer && (
                                    <> · Published by <span className="text-white">{game.publisher}</span></>
                                )}
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-7xl mx-auto px-6 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Left Column - Media & Content */}
                    <div className="lg:col-span-2 space-y-8">
                        <MediaGallery
                            screenshots={game.screenshots}
                            movies={game.movies}
                            title={game.title}
                        />

                        {/* Tabs */}
                        <div className="border-b border-white/10">
                            <div className="flex gap-1">
                                {(["about", "reviews", "requirements", "achievements"] as Tab[]).map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab)}
                                        className={`
                      px-6 py-3 font-medium capitalize transition-colors
                      ${activeTab === tab
                                                ? "text-violet-400 border-b-2 border-violet-400"
                                                : "text-zinc-500 hover:text-white"
                                            }
                    `}
                                    >
                                        {tab}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Tab Content */}
                        <div className="min-h-[300px]">
                            {activeTab === "about" && (
                                <div className="space-y-6">
                                    {game.short_description && (
                                        <p className="text-lg text-zinc-300 leading-relaxed">
                                            {game.short_description}
                                        </p>
                                    )}

                                    {game.about_the_game && (
                                        <div className="prose prose-invert max-w-none">
                                            <h3 className="text-xl font-semibold text-white mb-4">About This Game</h3>
                                            <div
                                                className="text-zinc-400 leading-relaxed"
                                                dangerouslySetInnerHTML={{ __html: game.about_the_game }}
                                            />
                                        </div>
                                    )}

                                    {!game.about_the_game && game.description && (
                                        <div>
                                            <h3 className="text-xl font-semibold text-white mb-4">Description</h3>
                                            <p className="text-zinc-400 leading-relaxed whitespace-pre-line">
                                                {game.description}
                                            </p>
                                        </div>
                                    )}

                                    {game.steam_app_id && (
                                        <a
                                            href={`https://store.steampowered.com/app/${game.steam_app_id}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors"
                                        >
                                            <ExternalLink className="w-4 h-4" />
                                            View on Steam
                                        </a>
                                    )}
                                </div>
                            )}

                            {activeTab === "requirements" && (
                                <div className="space-y-8">
                                    {((game.platforms?.windows ?? true) || !game.platforms) && game.pc_requirements && (
                                        <div>
                                            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                                                🖥️ Windows
                                            </h3>
                                            <div
                                                className="text-zinc-400 text-sm leading-relaxed bg-zinc-900/50 rounded-lg p-4"
                                                dangerouslySetInnerHTML={{ __html: game.pc_requirements }}
                                            />
                                        </div>
                                    )}

                                    {game.platforms?.mac && game.mac_requirements && (
                                        <div>
                                            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                                                🍎 macOS
                                            </h3>
                                            <div
                                                className="text-zinc-400 text-sm leading-relaxed bg-zinc-900/50 rounded-lg p-4"
                                                dangerouslySetInnerHTML={{ __html: game.mac_requirements }}
                                            />
                                        </div>
                                    )}

                                    {game.platforms?.linux && game.linux_requirements && (
                                        <div>
                                            <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                                                🐧 Linux
                                            </h3>
                                            <div
                                                className="text-zinc-400 text-sm leading-relaxed bg-zinc-900/50 rounded-lg p-4"
                                                dangerouslySetInnerHTML={{ __html: game.linux_requirements }}
                                            />
                                        </div>
                                    )}

                                    {(!game.pc_requirements && (!game.platforms?.mac || !game.mac_requirements) && (!game.platforms?.linux || !game.linux_requirements)) && (
                                        <p className="text-zinc-500">No system requirements available for this game.</p>
                                    )}
                                </div>
                            )}

                            {activeTab === "achievements" && (() => {
                                const achievementsList = (game.achievements && game.achievements.length > 0)
                                    ? game.achievements
                                    : (game.achievements_highlighted || []);
                                const totalAchievements = game.achievements_total || achievementsList.length;

                                if (achievementsList.length === 0) {
                                    return <p className="text-zinc-500">No achievements available for this game.</p>;
                                }

                                return (
                                    <div>
                                        <div className="flex items-center justify-between mb-6">
                                            <p className="text-zinc-400">
                                                This game has <span className="text-white font-semibold">{totalAchievements}</span> achievements.
                                            </p>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {achievementsList.map((achievement: any, index: number) => {
                                                const iconUrl = achievement.icon || achievement.path;
                                                const title = achievement.displayName || achievement.name;
                                                const isHidden = Boolean(achievement.hidden);
                                                const isRevealed = revealedAchievements.has(achievement.name);
                                                const percent = achievement.percent !== undefined ? Number(achievement.percent) : null;

                                                return (
                                                    <div
                                                        key={achievement.name || index}
                                                        className="flex items-start gap-4 p-4 bg-zinc-900/50 border border-white/5 rounded-xl hover:border-white/10 transition-colors"
                                                    >
                                                        {iconUrl ? (
                                                            <img
                                                                src={iconUrl}
                                                                alt={title}
                                                                className="w-14 h-14 rounded-lg object-cover flex-shrink-0 bg-zinc-800"
                                                            />
                                                        ) : (
                                                            <div className="w-14 h-14 rounded-lg bg-zinc-800 flex items-center justify-center flex-shrink-0 text-zinc-500">
                                                                🏆
                                                            </div>
                                                        )}
                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center justify-between gap-2">
                                                                <h4 className="text-white font-semibold truncate text-base">
                                                                    {title}
                                                                </h4>
                                                                {percent !== null && (
                                                                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 border border-violet-500/30 whitespace-nowrap">
                                                                        {percent.toFixed(1)}%
                                                                    </span>
                                                                )}
                                                            </div>

                                                            {isHidden && !isRevealed ? (
                                                                <div className="flex items-center gap-2 mt-1">
                                                                    <span className="text-xs text-zinc-500 italic">
                                                                        Hidden achievement
                                                                    </span>
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => setRevealedAchievements(prev => {
                                                                            const next = new Set(prev);
                                                                            next.add(achievement.name);
                                                                            return next;
                                                                        })}
                                                                        className="text-xs font-medium text-violet-400 hover:text-violet-300 hover:underline px-2 py-0.5 bg-violet-900/30 rounded border border-violet-500/20 transition-colors"
                                                                    >
                                                                        Reveal
                                                                    </button>
                                                                </div>
                                                            ) : (
                                                                <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                                                                    {achievement.description || "No description provided."}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                );
                            })()}

                            {activeTab === "reviews" && (
                                <ReviewList gameId={game.id} />
                            )}
                        </div>
                    </div>

                    {/* Right Column - Info Panel */}
                    <div className="lg:col-span-1">
                        <div className="sticky top-24">
                            <GameInfoPanel
                                game={game}
                                isInstalled={gameState === "installed" || gameState === "playing"}
                                onInstall={gameState === "not_installed" ? handleInstall : undefined}
                                onLaunch={gameState === "playing" ? handleStopGame : handleLaunch}
                            />

                            {/* Playing indicator */}
                            {gameState === "playing" && (
                                <div className="mt-4 p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
                                    <div className="flex items-center gap-3">
                                        <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                                        <span className="text-green-400 font-medium">Currently Playing</span>
                                    </div>
                                    <p className="text-sm text-zinc-400 mt-2">
                                        Click "Play" again to stop tracking session
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
