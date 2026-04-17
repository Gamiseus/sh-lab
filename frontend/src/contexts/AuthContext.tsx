import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// Types
interface User {
    id: number;
    username: string;
    display_name?: string;
    email?: string;
    is_admin: boolean;
    avatar_url?: string;
}

interface AuthTokens {
    access_token: string;
    refresh_token: string;
    expires_in: number;
}

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    getAuthHeader: () => { Authorization: string } | {};
}

const AuthContext = createContext<AuthContextType | null>(null);

// Constants
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'sh_access_token';
const REFRESH_KEY = 'sh_refresh_token';
const EXPIRY_KEY = 'sh_token_expiry';

// Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Get stored tokens
    const getStoredTokens = useCallback((): AuthTokens | null => {
        const accessToken = localStorage.getItem(TOKEN_KEY);
        const refreshToken = localStorage.getItem(REFRESH_KEY);
        const expiry = localStorage.getItem(EXPIRY_KEY);

        if (!accessToken || !refreshToken) return null;

        return {
            access_token: accessToken,
            refresh_token: refreshToken,
            expires_in: expiry ? parseInt(expiry, 10) : 0
        };
    }, []);

    // Store tokens
    const storeTokens = (tokens: AuthTokens) => {
        localStorage.setItem(TOKEN_KEY, tokens.access_token);
        localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
        localStorage.setItem(EXPIRY_KEY, (Date.now() + tokens.expires_in * 1000).toString());
    };

    // Clear tokens
    const clearTokens = () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem(EXPIRY_KEY);
    };

    // Get auth header for API calls
    const getAuthHeader = useCallback(() => {
        const tokens = getStoredTokens();
        if (!tokens) return {};
        return { Authorization: `Bearer ${tokens.access_token}` };
    }, [getStoredTokens]);

    // Fetch current user
    const fetchCurrentUser = useCallback(async (): Promise<User | null> => {
        const tokens = getStoredTokens();
        if (!tokens) return null;

        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: { Authorization: `Bearer ${tokens.access_token}` }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    // Try to refresh
                    const refreshed = await refreshToken();
                    if (refreshed) {
                        return fetchCurrentUser();
                    }
                }
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('Failed to fetch user:', error);
            return null;
        }
    }, [getStoredTokens]);

    // Refresh token
    const refreshToken = async (): Promise<boolean> => {
        const tokens = getStoredTokens();
        if (!tokens) return false;

        try {
            const response = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: tokens.refresh_token })
            });

            if (!response.ok) {
                clearTokens();
                return false;
            }

            const newTokens: AuthTokens = await response.json();
            storeTokens(newTokens);
            return true;
        } catch (error) {
            console.error('Token refresh failed:', error);
            clearTokens();
            return false;
        }
    };

    // Login
    const login = async (username: string, password: string): Promise<void> => {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Login failed' }));
            throw new Error(error.detail || 'Login failed');
        }

        const tokens: AuthTokens = await response.json();
        storeTokens(tokens);

        const fetchedUser = await fetchCurrentUser();
        setUser(fetchedUser);
    };

    // Logout
    const logout = async (): Promise<void> => {
        const tokens = getStoredTokens();

        if (tokens) {
            try {
                await fetch(`${API_BASE}/auth/logout`, {
                    method: 'POST',
                    headers: { Authorization: `Bearer ${tokens.access_token}` }
                });
            } catch (error) {
                console.error('Logout request failed:', error);
            }
        }

        clearTokens();
        setUser(null);
    };

    // Initial auth check
    useEffect(() => {
        const checkAuth = async () => {
            setIsLoading(true);
            const fetchedUser = await fetchCurrentUser();
            setUser(fetchedUser);
            setIsLoading(false);
        };

        checkAuth();
    }, [fetchCurrentUser]);

    // Token refresh interval
    useEffect(() => {
        const interval = setInterval(async () => {
            const expiry = localStorage.getItem(EXPIRY_KEY);
            if (expiry && Date.now() > parseInt(expiry, 10) - 60000) {
                await refreshToken();
            }
        }, 30000);

        return () => clearInterval(interval);
    }, []);

    const value: AuthContextType = {
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        getAuthHeader
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

// Hook to use auth context
export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

// Optional auth hook (doesn't throw if used outside provider)
export function useAuthOptional(): AuthContextType | null {
    return useContext(AuthContext);
}
