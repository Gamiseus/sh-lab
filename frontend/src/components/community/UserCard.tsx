import { Link } from "react-router-dom";
import { Gamepad2, Clock, ChevronRight, User } from "lucide-react";
import { UserCardData, getImageUrl } from "@/lib/api";

interface UserCardProps {
    user: UserCardData;
    size?: "normal" | "large";
}

export function UserCard({ user, size = "normal" }: UserCardProps) {
    const isLarge = size === "large";

    return (
        <Link
            to={`/profile/${user.id}`}
            className={`group relative block rounded-2xl border transition-all duration-300 overflow-hidden ${
                isLarge
                    ? "p-6 bg-gradient-to-br from-zinc-900/80 via-zinc-900/60 to-violet-950/20 border-violet-500/30 shadow-xl shadow-violet-950/20"
                    : "p-4 bg-zinc-900/60 hover:bg-zinc-900/90 border-white/10 hover:border-violet-500/50 hover:shadow-xl hover:shadow-violet-600/10 hover:-translate-y-0.5"
            }`}
        >
            {/* Ambient hover glow */}
            <div className="absolute inset-0 bg-gradient-to-r from-violet-600/5 via-indigo-600/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

            <div className={`flex items-center relative z-10 ${isLarge ? "gap-5" : "gap-3.5"}`}>
                {/* Avatar with Status Ring */}
                <div className="relative flex-shrink-0">
                    {user.avatar_url ? (
                        <img
                            src={getImageUrl(user.avatar_url)}
                            alt={user.display_name || user.username}
                            className={`${
                                isLarge ? "w-20 h-20 rounded-2xl" : "w-14 h-14 rounded-xl"
                            } object-cover ring-2 ring-white/10 group-hover:ring-violet-500/50 transition-all duration-300 shadow-md`}
                            loading="lazy"
                        />
                    ) : (
                        <div
                            className={`${
                                isLarge ? "w-20 h-20 rounded-2xl text-2xl" : "w-14 h-14 rounded-xl text-xl"
                            } bg-gradient-to-br from-violet-600 via-indigo-600 to-purple-600 flex items-center justify-center text-white font-extrabold shadow-lg shadow-violet-600/20 ring-2 ring-white/10 group-hover:ring-violet-500/50 transition-all`}
                        >
                            {(user.display_name || user.username)[0]?.toUpperCase() || <User className="w-6 h-6" />}
                        </div>
                    )}
                    {/* Active indicator dot */}
                    <span
                        className={`absolute -bottom-1 -right-1 rounded-full bg-emerald-500 ring-2 ring-zinc-950 shadow-sm ${
                            isLarge ? "w-4 h-4" : "w-3 h-3"
                        }`}
                        title="Community Member"
                    />
                </div>

                {/* Identity & Stats */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                        <p className={`font-bold text-white truncate group-hover:text-violet-300 transition-colors ${
                            isLarge ? "text-xl" : "text-base"
                        }`}>
                            {user.display_name || user.username}
                        </p>
                        {!isLarge && (
                            <ChevronRight className="w-4 h-4 text-zinc-600 group-hover:text-violet-400 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
                        )}
                    </div>
                    <p className="text-xs text-zinc-400 truncate">@{user.username}</p>

                    {/* Stats Badges */}
                    <div className={`flex flex-wrap items-center gap-2 ${isLarge ? "mt-3" : "mt-2"}`}>
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 border border-white/5 text-xs text-zinc-300">
                            <Gamepad2 className="w-3.5 h-3.5 text-violet-400" />
                            <span className="font-semibold text-white">{user.games_count}</span>
                            <span className="text-zinc-500">{user.games_count === 1 ? "game" : "games"}</span>
                        </div>
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 border border-white/5 text-xs text-zinc-300">
                            <Clock className="w-3.5 h-3.5 text-indigo-400" />
                            <span className="font-semibold text-white">{user.total_playtime_hours}h</span>
                            <span className="text-zinc-500">played</span>
                        </div>
                    </div>
                </div>

                {/* Large Card View Profile Action */}
                {isLarge && (
                    <div className="hidden sm:flex items-center gap-1 text-sm font-semibold text-violet-400 group-hover:text-violet-300 group-hover:translate-x-1 transition-all pl-2">
                        View Profile <ChevronRight className="w-4 h-4" />
                    </div>
                )}
            </div>
        </Link>
    );
}
