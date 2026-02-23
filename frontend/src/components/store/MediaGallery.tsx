import { useState, useRef, useEffect, useMemo } from "react";
import { X, ChevronLeft, ChevronRight, Play, Maximize2 } from "lucide-react";
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

// Thumbnail Component (Base64)
const MediaThumbnail = ({ url, alt, isActive }: { url?: string, alt: string, isActive: boolean }) => {
    const [b64Src, setB64Src] = useState<string | null>(null);

    useEffect(() => {
        if (!url) return;
        setB64Src(null);

        // Fetch Base64
        const u = `${API_BASE}/store/proxy/image/base64?url=${encodeURIComponent(getSecureUrl(url)!)}`;
        fetch(u)
            .then(res => res.ok ? res.json() : null)
            .then(data => {
                if (data) setB64Src(`data:${data.mime};base64,${data.data}`);
            })
            .catch(console.error);
    }, [url]);

    if (!b64Src) {
        return <div className="w-full h-full bg-black/40 animate-pulse" />;
    }

    return (
        <img
            src={b64Src}
            alt={alt}
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
    // Pass secure URL to proxy
    return `${API_BASE}/store/proxy/video?url=${encodeURIComponent(getSecureUrl(url)!)}`;
};

const MediaViewer = ({ media, title, isPlaying, setIsPlaying, onOpenLightbox }: MediaViewerProps) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const hlsRef = useRef<Hls | null>(null);

    // Base64 State for Images
    const [b64Src, setB64Src] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    // Initial source logic for Video
    const source = useMemo(() => {
        if (media.type !== "video") return null;
        const video = media as Movie;

        // HLS (m3u8) usually handles itself (segments), but if it needs proxying it's harder.
        // Assuming HLS is fine direct if CORS allows. If fails, we might need M3U8 proxy.
        if (video.hls) return { type: 'hls', url: getSecureUrl(video.hls) };

        // MP4/WebM -> Use Streaming Proxy
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

    // Base64 Fetch Logic (Only for Images)
    useEffect(() => {
        if (media.type === "image") {
            const s = media as Screenshot;
            const fullPath = s.path_full;
            if (!fullPath) return;

            setIsLoading(true);
            setB64Src(null);

            // Fetch Base64
            const u = `${API_BASE}/store/proxy/image/base64?url=${encodeURIComponent(getSecureUrl(fullPath)!)}`;
            fetch(u)
                .then(res => {
                    if (!res.ok) throw new Error("Proxy Failed");
                    return res.json();
                })
                .then(data => {
                    setB64Src(`data:${data.mime};base64,${data.data}`);
                    setIsLoading(false);
                })
                .catch(err => {
                    console.error("Image Fetch Error", err);
                    setIsLoading(false);
                });
        }
    }, [media]);

    if (media.type === "video") {
        const video = media as Movie;
        // Also fetch Poster as Base64 to ensure it loads?
        // Reuse MediaThumbnail logic? 
        // Or fetch manually here.
        // For simplicity, let's just use MediaThumbnail component inside?
        // Cannot nest invalidly.
        // I'll inline fetch for poster too.

        return (
            <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden border border-white/5">
                {isPlaying && source ? (
                    <video
                        ref={videoRef}
                        src={source.type !== 'hls' ? source.url : undefined}
                        controls
                        autoPlay
                        muted
                        playsInline
                        crossOrigin="anonymous"
                        className="w-full h-full object-contain"
                    />
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

    // Image Render (Base64)
    return (
        <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden group border border-white/5 flex items-center justify-center">
            {isLoading && (
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
            )}

            {b64Src && (
                <img
                    src={b64Src}
                    alt={`${title} screenshot`}
                    className="w-full h-full object-contain"
                    // Add Lightbox trigger behavior to image itself too?
                    onClick={onOpenLightbox}
                />
            )}

            <button
                onClick={onOpenLightbox}
                className="absolute top-4 right-4 p-2 rounded-lg bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70 backdrop-blur-sm"
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
                            className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80 backdrop-blur-sm"
                        >
                            <ChevronLeft className="w-6 h-6 text-white" />
                        </button>
                        <button
                            onClick={goNext}
                            className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80 backdrop-blur-sm"
                        >
                            <ChevronRight className="w-6 h-6 text-white" />
                        </button>
                    </>
                )}
            </div>

            {/* Thumbnail Strip */}
            {allMedia.length > 1 && (
                <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-2">
                    {allMedia.map((media, idx) => {
                        const isVideo = media.type === "video";
                        const rawThumb = isVideo
                            ? (media as Movie).thumbnail
                            : (media as Screenshot).path_thumbnail;

                        // Use MediaThumbnail for everything
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
            )}

            {/* Lightbox - Uses MediaThumbnail or Image directly via Base64 proxy manually?
                We can reuse MediaViewer inside Lightbox or just Image with Base64 fetch.
                We'll rewrite Lightbox content to perform the fetch.
             */}
            {isLightbox && currentMedia.type === "image" && (
                <div
                    className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
                    onClick={() => setIsLightbox(false)}
                >
                    {/* ... Controls ... */}
                    <button onClick={() => setIsLightbox(false)} className="absolute top-4 right-4 p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors z-50"><X className="w-6 h-6 text-white" /></button>
                    <button onClick={(e) => { e.stopPropagation(); goPrev(); }} className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors z-50"><ChevronLeft className="w-8 h-8 text-white" /></button>
                    <button onClick={(e) => { e.stopPropagation(); goNext(); }} className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors z-50"><ChevronRight className="w-8 h-8 text-white" /></button>

                    <div className="w-[90vw] h-[90vh] flex items-center justify-center" onClick={(e) => e.stopPropagation()}>
                        <MediaThumbnail
                            url={(currentMedia as Screenshot).path_full}
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
