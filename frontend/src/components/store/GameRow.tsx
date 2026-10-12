import { useRef, useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Game } from "@/lib/api";
import { GameCard } from "./GameCard";

interface GameRowProps {
    title: string;
    icon?: React.ReactNode;
    games: Game[];
    seeAllLink?: string;
    onTitleClick?: () => void;
    cardSize?: "sm" | "md" | "lg";
    showPrice?: boolean;
    headerExtra?: React.ReactNode;
}

export function GameRow({
    title,
    icon,
    games,
    seeAllLink,
    onTitleClick,
    cardSize = "md",
    showPrice = false,
    headerExtra
}: GameRowProps) {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [canScrollLeft, setCanScrollLeft] = useState(false);
    const [canScrollRight, setCanScrollRight] = useState(true);

    const checkScroll = () => {
        if (!scrollRef.current) return;
        const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
        setCanScrollLeft(scrollLeft > 0);
        setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 10);
    };

    useEffect(() => {
        checkScroll();
        const el = scrollRef.current;
        if (el) {
            el.addEventListener("scroll", checkScroll);
            return () => el.removeEventListener("scroll", checkScroll);
        }
    }, [games]);

    const scroll = (direction: "left" | "right") => {
        if (!scrollRef.current) return;
        const scrollAmount = scrollRef.current.clientWidth * 0.8;
        scrollRef.current.scrollBy({
            left: direction === "left" ? -scrollAmount : scrollAmount,
            behavior: "smooth",
        });
    };

    if (games.length === 0) return null;

    return (
        <section className="relative group/section">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 px-1 gap-2">
                <div
                    className={`flex items-center gap-3 ${onTitleClick ? "cursor-pointer group/title select-none" : ""}`}
                    onClick={onTitleClick}
                >
                    {icon && <span className="text-xl">{icon}</span>}
                    <h2 className={`text-xl font-bold text-white ${onTitleClick ? "group-hover/title:text-violet-400 transition-colors" : ""}`}>
                        {title}
                    </h2>
                    <span className="text-sm text-zinc-500">({games.length})</span>
                </div>
                <div className="flex items-center gap-3">
                    {headerExtra}
                    {seeAllLink ? (
                        <Link
                            to={seeAllLink}
                            className="text-sm text-violet-400 hover:text-violet-300 transition-colors"
                        >
                            See All →
                        </Link>
                    ) : onTitleClick ? (
                        <button
                            type="button"
                            onClick={onTitleClick}
                            className="text-sm text-violet-400 hover:text-violet-300 transition-colors"
                        >
                            See All →
                        </button>
                    ) : null}
                </div>
            </div>

            {/* Scroll Container */}
            <div className="relative">
                {/* Left Arrow */}
                <button
                    onClick={() => scroll("left")}
                    className={`
            absolute left-0 top-1/2 -translate-y-1/2 z-10
            w-12 h-12 rounded-full bg-black/80 backdrop-blur-sm
            flex items-center justify-center
            border border-white/10 hover:border-violet-500/50
            text-white hover:text-violet-400
            transition-all duration-300
            ${canScrollLeft ? "opacity-100" : "opacity-0 pointer-events-none"}
            -translate-x-1/2 group-hover/section:translate-x-0
          `}
                >
                    <ChevronLeft className="w-6 h-6" />
                </button>

                {/* Games */}
                <div
                    ref={scrollRef}
                    className="flex gap-4 overflow-x-auto scrollbar-hide pb-2 scroll-smooth"
                    style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
                >
                    {games.map((game) => (
                        <div key={game.id} className="flex-shrink-0 w-60 sm:w-64">
                            <GameCard game={game} size={cardSize} showPrice={showPrice} />
                        </div>
                    ))}
                </div>

                {/* Right Arrow */}
                <button
                    onClick={() => scroll("right")}
                    className={`
            absolute right-0 top-1/2 -translate-y-1/2 z-10
            w-12 h-12 rounded-full bg-black/80 backdrop-blur-sm
            flex items-center justify-center
            border border-white/10 hover:border-violet-500/50
            text-white hover:text-violet-400
            transition-all duration-300
            ${canScrollRight ? "opacity-100" : "opacity-0 pointer-events-none"}
            translate-x-1/2 group-hover/section:translate-x-0
          `}
                >
                    <ChevronRight className="w-6 h-6" />
                </button>

                {/* Edge Gradients */}
                <div className={`
          absolute left-0 top-0 bottom-2 w-16 
          bg-gradient-to-r from-background to-transparent 
          pointer-events-none transition-opacity
          ${canScrollLeft ? "opacity-100" : "opacity-0"}
        `} />
                <div className={`
          absolute right-0 top-0 bottom-2 w-16 
          bg-gradient-to-l from-background to-transparent 
          pointer-events-none transition-opacity
          ${canScrollRight ? "opacity-100" : "opacity-0"}
        `} />
            </div>
        </section>
    );
}
