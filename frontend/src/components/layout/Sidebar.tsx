import { LayoutGrid, Download, Settings, MessageSquare, Newspaper, Gamepad2, LogOut, User } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";

const NAV_ITEMS = [
    { icon: LayoutGrid, label: "Library", path: "/" },
    { icon: Gamepad2, label: "Store", path: "/store" },
    { icon: Download, label: "Downloads", path: "/downloads" },
    { icon: MessageSquare, label: "Community", path: "/community" },
    { icon: Newspaper, label: "News", path: "/news" },
];

export function Sidebar() {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, logout } = useAuth();

    const handleLogout = async () => {
        await logout();
        navigate("/login");
    };

    return (
        <div className="w-64 h-full bg-zinc-950/95 backdrop-blur-md border-r border-white/10 flex flex-col">
            <div className="p-6 flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
                    <Gamepad2 className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-violet-400 via-purple-300 to-indigo-400 bg-clip-text text-transparent">
                        sh_lab
                    </h1>
                </div>
            </div>

            <nav className="flex-1 px-3 space-y-1">
                {NAV_ITEMS.map((item) => {
                    const isActive = location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path));
                    return (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={cn(
                                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 border-l-2",
                                isActive
                                    ? "bg-violet-600/15 text-violet-300 border-violet-500 shadow-[0_0_15px_-3px_rgba(124,58,237,0.3)] font-semibold"
                                    : "border-transparent text-zinc-400 hover:text-white hover:bg-white/5"
                            )}
                        >
                            <item.icon className={cn("w-4 h-4", isActive ? "text-violet-400" : "text-zinc-400")} />
                            {item.label}
                        </Link>
                    );
                })}
            </nav>

            {/* Settings */}
            <div className="px-3 py-2 border-t border-white/5">
                <Link
                    to="/settings"
                    className={cn(
                        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 border-l-2",
                        location.pathname === "/settings"
                            ? "bg-violet-600/15 text-violet-300 border-violet-500 shadow-[0_0_15px_-3px_rgba(124,58,237,0.3)] font-semibold"
                            : "border-transparent text-zinc-400 hover:text-white hover:bg-white/5"
                    )}
                >
                    <Settings className={cn("w-4 h-4", location.pathname === "/settings" ? "text-violet-400" : "text-zinc-400")} />
                    Settings
                </Link>
            </div>

            {/* User Panel */}
            <div className="p-3 border-t border-white/5">
                <Link
                    to="/profile"
                    className="flex items-center gap-3 px-3 py-2 mb-2 rounded-lg hover:bg-white/5 transition-colors"
                >
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold">
                        {user?.display_name?.[0] || user?.username?.[0] || <User className="w-4 h-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">
                            {user?.display_name || user?.username || "Guest"}
                        </p>
                        {user?.is_admin && (
                            <p className="text-xs text-violet-400">Admin</p>
                        )}
                    </div>
                </Link>

                <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                >
                    <LogOut className="w-4 h-4" />
                    Logout
                </button>
            </div>
        </div>
    );
}
