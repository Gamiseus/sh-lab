import { useState, useRef, useEffect, useMemo } from "react";
import { X, ChevronLeft, ChevronRight, Play, Maximize2, Volume2, VolumeX } from "lucide-react";
import { Screenshot, Movie, API_BASE } from "@/lib/api";
import Hls from "hls.js";

interface MediaGalleryProps {
    screenshots?: Screenshot[];
    movies?: Movie[];
    title: string;
}

const getSecureUrl = (url?: string) => {
    if (!url) return undefined;
    if (url.startsWith("http:")) return url.replace("http:", "https:");
    return url;
};

const getScreenshotFull = (s?: any): string | undefined => {
    if (!s) return undefined;
    return s.path_full || s.full || s.path;
};

const getScreenshotThumb = (s?: any): string | undefined => {
    if (!s) return undefined;
    return s.path_thumbnail || s.thumbnail || s.path;
};

// Thumbnail Component (Base64 + Direct Proxy Fallback)
const MediaThumbnail = ({ url, alt, isActive }: { url?: string, alt: string, isActive: boolean }) => {
    const [b64Src, setB64Src] = useState<string | null>(null);
    const [useDirect, setUseDirect] = useState(false);

    const directProxyUrl = useMemo(() => {
        if (!url) return undefined;
        return `${API_BASE}/store/proxy/image?url=${encodeURIComponent(getSecureUrl(url)!)}`;
    }, [url]);

    useEffect(() => {
        if (!url) return;
        setB64Src(null);
        setUseDirect(false);

        // Fetch Base64
        const u = `${API_BASE}/store/proxy/image/base64?url=${encodeURIComponent(getSecureUrl(url)!)}`;
        fetch(u)
            .then(res => res.ok ? res.json() : null)
            .then(data => {
                if (data && data.data) {
                    setB64Src(`data:${data.mime};base64,${data.data}`);
                } else {
                    setUseDirect(true);
                }
            })
            .catch(() => setUseDirect(true));
    }, [url]);

    if (!url) {
        return <div className="w-full h-full bg-zinc-800 flex items-center justify-center text-xs text-zinc-600">No Image</div>;
    }

    if (!b64Src && !useDirect) {
        return <div className="w-full h-full bg-black/40 animate-pulse" />;
    }

    return (
        <img
            src={b64Src || directProxyUrl}
            alt={alt}
            onError={() => {
                if (!useDirect && directProxyUrl) setUseDirect(true);
            }}
            className={`w-full h-full object-cover transition-opacity duration-300 ${isActive ? 'opacity-100' : 'opacity-70 group-hover:opacity-100'}`}
        />
    );
};

interface MediaViewerProps {
    media: (Movie & { type: "video" }) | (Screenshot & { type: "image" });
    title: string;
    isPlaying: boolean;
    setIsPlaying: (v: boolean) => void;
    onOpenLightbox: () => void;
}

// Video Proxy (Streaming)
const getProxyVideoUrl = (url?: string) => {
    if (!url) return undefined;
    return `${API_BASE}/store/proxy/video?url=${encodeURIComponent(getSecureUrl(url)!)}`;
};

const MediaViewer = ({ media, title, isPlaying, setIsPlaying, onOpenLightbox }: MediaViewerProps) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const hlsRef = useRef<Hls | null>(null);

    // Audio State for Videos
    const [isMuted, setIsMuted] = useState(false);
    const [_volume, setVolume] = useState(1.0);

    // Image State
    const [b64Src, setB64Src] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    // Initial source logic for Video
    const source = useMemo(() => {
        if (media.type !== "video") return null;
        const video = media as Movie;

        if (video.hls) return { type: 'hls', url: getSecureUrl(video.hls) };

        if (video.mp4) {
            const src = typeof video.mp4 === 'string' ? video.mp4 : (video.mp4.max || video.mp4["480"]);
            if (src) return { type: 'mp4', url: getProxyVideoUrl(src) };
        }
        if (video.webm) {
            const src = typeof video.webm === 'string' ? video.webm : (video.webm.max || video.webm["480"]);
            if (src) return { type: 'webm', url: getProxyVideoUrl(src) };
        }
        return null;
    }, [media]);

    // Cleanup HLS
    useEffect(() => {
        return () => {
            if (hlsRef.current) hlsRef.current.destroy();
        };
    }, [media]);

    // HLS Logic
    useEffect(() => {
        if (!isPlaying || media.type !== "video" || !source || source.type !== 'hls' || !videoRef.current) {
            return;
        }

        if (Hls.isSupported()) {
            if (hlsRef.current) hlsRef.current.destroy();
            const hls = new Hls();
            hlsRef.current = hls;
            hls.loadSource(source.url!);
            hls.attachMedia(videoRef.current);
            hls.on(Hls.Events.MANIFEST_PARSED, () => videoRef.current?.play().catch(console.error));
        } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
            videoRef.current.src = source.url!;
            videoRef.current.play().catch(console.error);
        }
    }, [isPlaying, media, source]);

    // Image Fetch Logic (Both Base64 & Direct Proxy Fallback)
    useEffect(() => {
        if (media.type === "image") {
            const fullPath = getScreenshotFull(media);
            if (!fullPath) return;

            setIsLoading(true);
            setB64Src(null);

            const u = `${API_BASE}/store/proxy/image/base64?url=${encodeURIComponent(getSecureUrl(fullPath)!)}`;
            fetch(u)
                .then(res => {
                    if (!res.ok) throw new Error("Base64 Proxy Failed");
                    return res.json();
                })
                .then(data => {
                    if (data && data.data) {
                        setB64Src(`data:${data.mime};base64,${data.data}`);
                    } else {
                        setB64Src(`${API_BASE}/store/proxy/image?url=${encodeURIComponent(getSecureUrl(fullPath)!)}`);
                    }
                    setIsLoading(false);
                })
                .catch(() => {
                    setB64Src(`${API_BASE}/store/proxy/image?url=${encodeURIComponent(getSecureUrl(fullPath)!)}`);
                    setIsLoading(false);
                });
        }
    }, [media]);

    if (media.type === "video") {
        const video = media as Movie;

        return (
            <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden border border-white/5">
                {isPlaying && source ? (
                    <div className="relative w-full h-full">
                        <video
                            ref={videoRef}
                            src={source.type !== 'hls' ? source.url : undefined}
                            controls
                            autoPlay
                            muted={isMuted}
                            playsInline
                            crossOrigin="anonymous"
                            className="w-full h-full object-contain"
                            onVolumeChange={(e) => {
                                setIsMuted(e.currentTarget.muted);
                                setVolume(e.currentTarget.volume);
                            }}
                        />
                        {/* Audio control floating badge/toggle */}
                        <button
                            type="button"
                            onClick={() => {
                                if (videoRef.current) {
                                    videoRef.current.muted = !isMuted;
                                    setIsMuted(!isMuted);
                                }
                            }}
                            className="absolute top-4 left-4 z-20 px-3 py-1.5 bg-black/70 hover:bg-black/90 backdrop-blur-md rounded-lg text-white text-xs font-medium flex items-center gap-2 border border-white/10 transition-colors shadow-lg"
                        >
                            {isMuted ? (
                                <>
                                    <VolumeX className="w-4 h-4 text-red-400" />
                                    <span>Unmute</span>
                                </>
                            ) : (
                                <>
                                    <Volume2 className="w-4 h-4 text-green-400" />
                                    <span>Mute</span>
                                </>
                            )}
                        </button>
                    </div>
                ) : (
                    <>
                        {/* Poster Image */}
                        <div className="absolute inset-0">
                            <MediaThumbnail url={video.thumbnail} alt={video.name || ""} isActive={true} />
                        </div>

                        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                        <button
                            onClick={() => setIsPlaying(true)}
                            className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/40 transition-colors group"
                        >
                            <div className="w-20 h-20 rounded-full bg-violet-600/90 flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform backdrop-blur-sm">
                                <Play className="w-8 h-8 text-white fill-current ml-1" />
                            </div>
                        </button>
                    </>
                )}
            </div>
        );
    }

    // Image Render
    const fullPath = getScreenshotFull(media);

    return (
        <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden group border border-white/5 flex items-center justify-center">
            {isLoading && (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
            )}

            {b64Src ? (
                <img
                    src={b64Src}
                    alt={`${title} screenshot`}
                    className="w-full h-full object-contain cursor-pointer"
                    onClick={onOpenLightbox}
                    onError={() => {
                        if (fullPath && !b64Src.includes("/store/proxy/image?url=")) {
                            setB64Src(`${API_BASE}/store/proxy/image?url=${encodeURIComponent(getSecureUrl(fullPath)!)}`);
                        }
                    }}
                />
            ) : !isLoading && fullPath ? (
                <img
                    src={`${API_BASE}/store/proxy/image?url=${encodeURIComponent(getSecureUrl(fullPath)!)}`}
                    alt={`${title} screenshot`}
                    className="w-full h-full object-contain cursor-pointer"
                    onClick={onOpenLightbox}
                />
            ) : null}

            <button
                onClick={onOpenLightbox}
                className="absolute top-4 right-4 p-2 rounded-lg bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70 backdrop-blur-sm"
                aria-label="Open Lightbox"
            >
                <Maximize2 className="w-5 h-5 text-white" />
            </button>
        </div>
    );
};

export function MediaGallery({ screenshots = [], movies = [], title }: MediaGalleryProps) {
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [isLightbox, setIsLightbox] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const stripRef = useRef<HTMLDivElement>(null);

    // Combine movies and screenshots
    const allMedia = useMemo(() => [
        ...movies.map((m) => ({ type: "video" as const, ...m })),
        ...screenshots.map((s) => ({ type: "image" as const, ...s })),
    ], [movies, screenshots]);

    if (allMedia.length === 0) return null;

    const currentMedia = allMedia[selectedIndex];

    const goNext = () => {
        setSelectedIndex((prev) => (prev + 1) % allMedia.length);
        setIsPlaying(false);
    };

    const goPrev = () => {
        setSelectedIndex((prev) => (prev - 1 + allMedia.length) % allMedia.length);
        setIsPlaying(false);
    };

    const scrollThumbnails = (direction: "left" | "right") => {
        if (stripRef.current) {
            const offset = direction === "left" ? -250 : 250;
            stripRef.current.scrollBy({ left: offset, behavior: "smooth" });
        }
    };

    return (
        <div className="space-y-4">
            {/* Main Display */}
            <div className="relative group">
                <MediaViewer
                    media={currentMedia}
                    title={title}
                    isPlaying={isPlaying}
                    setIsPlaying={setIsPlaying}
                    onOpenLightbox={() => setIsLightbox(true)}
                />

                {/* Navigation Arrows */}
                {allMedia.length > 1 && (
                    <>
                        <button
                            onClick={goPrev}
                            aria-label="Previous Media"
                            className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80 backdrop-blur-sm"
                        >
                            <ChevronLeft className="w-6 h-6 text-white" />
                        </button>
                        <button
                            onClick={goNext}
                            aria-label="Next Media"
                            className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80 backdrop-blur-sm"
                        >
                            <ChevronRight className="w-6 h-6 text-white" />
                        </button>
                    </>
                )}
            </div>

            {/* Thumbnail Strip with visible horizontal scrollbar and navigation */}
            {allMedia.length > 1 && (
                <div className="relative group/strip">
                    <button
                        onClick={() => scrollThumbnails("left")}
                        aria-label="Scroll thumbnails left"
                        className="absolute left-1 top-1/2 -translate-y-1/2 z-10 w-7 h-10 rounded bg-black/70 hover:bg-black/90 text-white flex items-center justify-center opacity-0 group-hover/strip:opacity-100 transition-opacity border border-white/10"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    <div
                        ref={stripRef}
                        className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-zinc-700 hover:scrollbar-thumb-zinc-500 scrollbar-track-zinc-900/60"
                    >
                        {allMedia.map((media, idx) => {
                            const isVideo = media.type === "video";
                            const rawThumb = isVideo
                                ? (media as Movie).thumbnail
                                : getScreenshotThumb(media);

                            return (
                                <button
                                    key={idx}
                                    onClick={() => {
                                        setSelectedIndex(idx);
                                        setIsPlaying(false);
                                    }}
                                    className={`
                                        relative flex-shrink-0 w-24 h-14 rounded-lg overflow-hidden
                                        border-2 transition-all group
                                        ${idx === selectedIndex
                                            ? "border-violet-500 ring-2 ring-violet-500/30"
                                            : "border-transparent hover:border-white/30"
                                        }
                                    `}
                                >
                                    <MediaThumbnail
                                        url={rawThumb}
                                        alt="thumbnail"
                                        isActive={idx === selectedIndex}
                                    />
                                    {isVideo && (
                                        <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                                            <Play className="w-4 h-4 text-white fill-current" />
                                        </div>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                    <button
                        onClick={() => scrollThumbnails("right")}
                        aria-label="Scroll thumbnails right"
                        className="absolute right-1 top-1/2 -translate-y-1/2 z-10 w-7 h-10 rounded bg-black/70 hover:bg-black/90 text-white flex items-center justify-center opacity-0 group-hover/strip:opacity-100 transition-opacity border border-white/10"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            )}

            {/* Lightbox */}
            {isLightbox && currentMedia.type === "image" && (
                <div
                    className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
                    onClick={() => setIsLightbox(false)}
                >
                    <button onClick={() => setIsLightbox(false)} aria-label="Close Lightbox" className="absolute top-4 right-4 p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors z-50"><X className="w-6 h-6 text-white" /></button>
                    <button onClick={(e) => { e.stopPropagation(); goPrev(); }} aria-label="Previous" className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors z-50"><ChevronLeft className="w-8 h-8 text-white" /></button>
                    <button onClick={(e) => { e.stopPropagation(); goNext(); }} aria-label="Next" className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors z-50"><ChevronRight className="w-8 h-8 text-white" /></button>

                    <div className="w-[90vw] h-[90vh] flex items-center justify-center" onClick={(e) => e.stopPropagation()}>
                        <MediaThumbnail
                            url={getScreenshotFull(currentMedia)}
                            alt="Lightbox"
                            isActive={true}
                        />
                    </div>

                    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-white/60 text-sm">
                        {selectedIndex + 1} / {allMedia.length}
                    </div>
                </div>
            )}
        </div>
    );
}
