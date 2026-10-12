import { useParams, useNavigate, useSearchParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { ArrowLeft, CheckCircle, AlertCircle } from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { storeAPI, getImageUrl, playtimeAPI } from "@/lib/api";
import { MediaGallery } from "@/components/store/MediaGallery";
import { GameInfoPanel } from "@/components/store/GameInfoPanel";
import { ReviewList } from "@/components/reviews/ReviewList";
import { useLibraryStore, LocalVerificationResult } from "@/stores/LibraryStore";

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
    const [searchParams] = useSearchParams();
    const [activeTab, setActiveTab] = useState<Tab>("about");
    const [gameState, setGameState] = useState<GameState>("not_installed");
    const [installProgress, setInstallProgress] = useState<InstallProgress | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [revealedAchievements, setRevealedAchievements] = useState<Set<string>>(new Set());

    const { isInLibrary, isInstalled, addToLibrary, addInstalledGame } = useLibraryStore();

    const { data: game, isLoading, error: fetchError } = useQuery({
        queryKey: ["game", id],
        queryFn: () => storeAPI.getGame(Number(id)),
        enabled: !!id,
    });

    const gameInLibrary = game ? isInLibrary(game.id) : false;
    const gameIsInstalled = game ? isInstalled(game.id) : false;

    // Standardized library paths reading with fallback (R3 requirement)
    const getConfiguredLibraryPaths = (): string[] => {
        try {
            const stored = localStorage.getItem("sh_library_paths") || localStorage.getItem("library-paths");
            if (stored) {
                const paths = JSON.parse(stored);
                if (Array.isArray(paths) && paths.length > 0) return paths;
            }
        } catch (e) {
            console.warn("Failed to parse library paths from localStorage:", e);
        }
        return [
            "c:\\Users\\Administrator\\Documents\\Projects\\sh-lab\\data\\games",
            "E:\\projects\\sh-lab\\data\\games"
        ];
    };

    const getLibraryPath = (): string => {
        return getConfiguredLibraryPaths()[0] || "c:\\Users\\Administrator\\Documents\\Projects\\sh-lab\\data\\games";
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

    // Check if game is running or installed on mount (R3 pre-flight verification)
    useEffect(() => {
        const checkLocalInstallStatus = async () => {
            if (!game) return;

            try {
                // Check if running
                const isRunning = await invoke<boolean>("is_game_running_command", {
                    gameId: game.id,
                });

                if (isRunning) {
                    setGameState("playing");
                    return;
                }

                // Check store state
                if (gameIsInstalled) {
                    setGameState("installed");
                    return;
                }

                // R3: Pre-flight local disk check across configured library paths
                const verifyResult = await invoke<LocalVerificationResult>("verify_local_game_command", {
                    libraryPaths: getConfiguredLibraryPaths(),
                    gameId: game.id,
                    gameTitle: game.title,
                    steamAppId: game.steam_app_id || null,
                    expectedExe: (game as any).executable_path || null,
                });

                if (verifyResult.found && verifyResult.verified_binary && verifyResult.path) {
                    addInstalledGame({
                        id: game.id,
                        path: verifyResult.path,
                    });
                    setGameState("installed");
                } else if (verifyResult.found && !verifyResult.verified_binary) {
                    console.warn(`Local directory found for "${game.title}" but executable signature check failed (verified_binary: false). Treating as uninstalled.`);
                }
            } catch (err) {
                console.error("Local disk precheck failed:", err);
            }
        };

        checkLocalInstallStatus();
    }, [game, gameIsInstalled]);

    // Handle Add to Library (R2: Records ownership without network transfer)
    const handleAddToLibrary = async () => {
        if (!game) return;
        try {
            await addToLibrary(game.id, {
                id: game.id,
                title: game.title,
                cover_url: game.cover_url,
                header_image: game.header_image,
                background_url: (game as any).background_url || game.header_image,
                description: game.short_description || game.description,
                developer: game.developer,
                publisher: game.publisher,
                release_date: game.release_date,
                rating: game.rating,
                genres: game.genres,
                categories: game.categories?.map((c: any) => typeof c === 'string' ? c : c.description),
                steam_app_id: game.steam_app_id,
                playtime_minutes: game.playtime_minutes || 0,
            });
            setSuccessMessage(`Added "${game.title}" to your library!`);
            setTimeout(() => setSuccessMessage(null), 4000);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        }
    };

    // Handle Install (R2 & R3: Registers ownership AND verifies local disk before network transfer)
    const handleInstall = async () => {
        if (!game) return;
        setError(null);

        // R2: Both registers in library AND dispatches install
        await addToLibrary(game.id, {
            id: game.id,
            title: game.title,
            cover_url: game.cover_url,
            header_image: game.header_image,
            playtime_minutes: game.playtime_minutes || 0
        });

        // R3: Pre-flight local verification before network download
        try {
            const verifyResult = await invoke<LocalVerificationResult>("verify_local_game_command", {
                libraryPaths: getConfiguredLibraryPaths(),
                gameId: game.id,
                gameTitle: game.title,
                steamAppId: game.steam_app_id || null,
                expectedExe: (game as any).executable_path || null,
            });

            if (verifyResult.found && verifyResult.verified_binary && verifyResult.path) {
                addInstalledGame({
                    id: game.id,
                    path: verifyResult.path,
                });
                setGameState("installed");
                setSuccessMessage(`Detected local installation for "${game.title}". Linked as installed!`);
                setTimeout(() => setSuccessMessage(null), 5000);
                return; // SKIP NETWORK DOWNLOAD!
            } else if (verifyResult.found && !verifyResult.verified_binary) {
                console.warn(`Local directory found for "${game.title}" but executable signature check failed. Falling back to network download.`);
            }
        } catch (scanErr) {
            console.warn("Pre-flight local verification check error:", scanErr);
        }

        // Local files not found: Proceed with network installation
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

    // Auto-trigger install if routed with ?install=1
    useEffect(() => {
        if (searchParams.get("install") === "1" && game && gameState === "not_installed") {
            handleInstall();
        }
    }, [searchParams, game, gameState]);

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

            {/* Install Progress Floating Overlay */}
            {installProgress && (
                <div className="fixed bottom-6 right-6 z-50 p-4 rounded-xl bg-zinc-900/95 border border-violet-500/40 text-white shadow-2xl backdrop-blur-md max-w-sm">
                    <div className="flex items-center justify-between gap-4 mb-1.5">
                        <span className="text-xs font-bold text-violet-300">Installing {game.title}</span>
                        <span className="text-xs font-extrabold text-violet-400">{installProgress.percent.toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden mb-1.5">
                        <div
                            className="bg-violet-500 h-full transition-all duration-200"
                            style={{ width: `${installProgress.percent}%` }}
                        />
                    </div>
                    <p className="text-[11px] text-zinc-400 truncate">{installProgress.current_file}</p>
                </div>
            )}

            {/* Back Button */}
            <div className="max-w-7xl mx-auto px-6 pt-6">
                <button
                    onClick={() => navigate(-1)}
                    className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors"
                >
                    <ArrowLeft className="w-4 h-4" />
                    <span>Back</span>
                </button>
            </div>

            {/* Hero Banner */}
            <div className="relative h-[480px] w-full overflow-hidden mt-4">
                {backgroundImage && (
                    <img
                        src={backgroundImage}
                        alt={game.title}
                        className="w-full h-full object-cover"
                    />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/60 to-transparent" />
                <div className="absolute inset-0 bg-gradient-to-r from-zinc-950 via-transparent to-transparent" />

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
                        <div className="space-y-6">
                            {activeTab === "about" && (
                                <div className="space-y-6">
                                    {game.short_description && (
                                        <p className="text-lg text-zinc-300 leading-relaxed font-medium">
                                            {game.short_description}
                                        </p>
                                    )}

                                    {game.description && (
                                        <div
                                            className="text-zinc-400 leading-relaxed space-y-4"
                                            dangerouslySetInnerHTML={{
                                                __html: game.description.replace(/\n/g, "<br/>"),
                                            }}
                                        />
                                    )}

                                    {!game.short_description && !game.description && (
                                        <p className="text-zinc-500 italic">No description available.</p>
                                    )}
                                </div>
                            )}

                            {activeTab === "requirements" && (
                                <div className="space-y-6">
                                    {game.pc_requirements ? (
                                        <div>
                                            <h3 className="text-lg font-semibold text-white mb-3">
                                                PC Requirements
                                            </h3>
                                            <div
                                                className="text-zinc-400 text-sm leading-relaxed bg-zinc-900/50 p-6 rounded-xl border border-white/5"
                                                dangerouslySetInnerHTML={{
                                                    __html: game.pc_requirements,
                                                }}
                                            />
                                        </div>
                                    ) : (
                                        <p className="text-zinc-500 italic">
                                            System requirements not specified.
                                        </p>
                                    )}
                                </div>
                            )}

                            {activeTab === "achievements" && (() => {
                                const list = (game.achievements && game.achievements.length > 0)
                                    ? game.achievements
                                    : (game.achievements_highlighted && game.achievements_highlighted.length > 0)
                                        ? game.achievements_highlighted
                                        : [];

                                if (list.length === 0) {
                                    return (
                                        <p className="text-zinc-500 italic">
                                            No achievements available for this game.
                                        </p>
                                    );
                                }

                                return (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between text-sm text-zinc-400 pb-2 border-b border-white/5">
                                            <span>{list.length} total achievements</span>
                                        </div>

                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                            {list.map((achievement: any, index: number) => {
                                                const iconUrl = achievement.icon || achievement.icon_gray;
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
                                isInstalled={gameState === "installed" || gameState === "playing" || gameIsInstalled}
                                isInLibrary={gameInLibrary}
                                onInstall={gameState === "not_installed" ? handleInstall : undefined}
                                onLaunch={gameState === "playing" ? handleStopGame : handleLaunch}
                                onAddToLibrary={handleAddToLibrary}
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
