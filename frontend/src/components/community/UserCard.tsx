import { Link } from "react-router-dom";
import { Gamepad2, Clock } from "lucide-react";
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
            className={`block bg-zinc-900/50 border border-white/10 rounded-xl overflow-hidden hover:border-violet-500/50 transition-colors ${isLarge ? "p-6" : "p-4"
                }`}
        >
            <div className={`flex items-center gap-${isLarge ? "4" : "3"}`}>
                {/* Avatar */}
                {user.avatar_url ? (
                    <img
                        src={getImageUrl(user.avatar_url)}
                        alt={user.display_name || user.username}
                        className={`${isLarge ? "w-20 h-20" : "w-14 h-14"
                            } rounded-xl object-cover`}
                    />
                ) : (
                    <div
                        className={`${isLarge ? "w-20 h-20" : "w-14 h-14"
                            } rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-bold ${isLarge ? "text-2xl" : "text-xl"
                            }`}
                    >
                        {(user.display_name || user.username)[0].toUpperCase()}
                    </div>
                )}

                {/* Info */}
                <div className="flex-1 min-w-0">
                    <p className={`text-white font-medium truncate ${isLarge ? "text-lg" : ""}`}>
                        {user.display_name || user.username}
                    </p>
                    <p className="text-sm text-zinc-500 truncate">@{user.username}</p>

                    <div className={`flex items-center gap-4 ${isLarge ? "mt-2" : "mt-1"}`}>
                        <div className="flex items-center gap-1 text-xs text-zinc-400">
                            <Gamepad2 className="w-3 h-3" />
                            <span>{user.games_count} games</span>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-zinc-400">
                            <Clock className="w-3 h-3" />
                            <span>{user.total_playtime_hours}h played</span>
                        </div>
                    </div>
                </div>
            </div>
        </Link>
    );
}
