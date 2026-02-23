import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppLayout() {
    return (
        <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
            <Sidebar />
            <main className="flex-1 h-full overflow-y-auto no-scrollbar">
                <Outlet />
            </main>
        </div>
    );
}
