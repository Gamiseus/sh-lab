import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { AppLayout } from "@/layouts/AppLayout";
import ProtectedRoute from "@/components/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import { LibraryPage } from "@/pages/LibraryPage";
import { GameDetailsPage } from "@/pages/GameDetailsPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { StorePage } from "@/pages/StorePage";
import { ProfilePage } from "@/pages/ProfilePage";
import { CommunityPage } from "@/pages/CommunityPage";
import { NewsPage } from "@/pages/NewsPage";
import { NewsDetailsPage } from "@/pages/NewsDetailsPage";
import { DownloadsPage } from "@/pages/DownloadsPage";
import { AdminPage } from "@/pages/AdminPage";
import "./App.css";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public route - Login */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected routes */}
            <Route element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }>
              <Route path="/" element={<LibraryPage />} />
              <Route path="/games/:id" element={<GameDetailsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/store" element={<StorePage />} />
              <Route path="/store/:id" element={<GameDetailsPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/profile/:userId" element={<ProfilePage />} />
              <Route path="/community" element={<CommunityPage />} />
              <Route path="/news" element={<NewsPage />} />
              <Route path="/news/:id" element={<NewsDetailsPage />} />
              <Route path="/downloads" element={<DownloadsPage />} />
              <Route path="/admin" element={<AdminPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
