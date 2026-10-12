import { create } from 'zustand';
import { api } from '@/lib/api';

// What we know from the scanner (Rust)
export interface LocalGameData {
    id: number;
    path: string; // The specific folder path for this installation
}

export interface LocalVerificationResult {
    found: boolean;
    path?: string | null;
    executable?: string | null;
    match_method?: string | null;
    verified_binary: boolean;
}

export interface UserLibraryEntry {
    game_id: number;
    added_at: string;
    status?: 'uninstalled' | 'installing' | 'installed';
}

// What we know from the Backend
export interface GameMetadata {
    id: number;
    title: string;
    cover_url?: string;
    header_image?: string;
    background_url?: string;
    description?: string;
    summary?: string;
    developer?: string;
    publisher?: string;
    release_date?: string;
    rating?: number;
    genres?: string[];
    categories?: string[];
    steam_app_id?: number;
    igdb_id?: number;
    playtime_minutes: number;
}

// Combined View for Library
export interface LibraryGame extends GameMetadata {
    install_path?: string;
    is_installed: boolean;
    added_at?: string;
}

interface LibraryState {
    // Dual tracking: owned library titles vs locally installed games
    userLibrary: Record<number, UserLibraryEntry>;
    userGames: Record<number, UserLibraryEntry>;
    installedGames: Record<number, LocalGameData>;

    // Cache of Metadata (ID -> Metadata)
    gameMetadata: Record<number, GameMetadata>;

    // Computed / Getters
    getLibrary: () => LibraryGame[];
    isInLibrary: (id: number) => boolean;
    isInstalled: (id: number) => boolean;

    // Actions
    addToLibrary: (gameId: number, metadata?: Partial<GameMetadata>) => Promise<void>;
    removeFromLibrary: (gameId: number) => Promise<void>;
    addInstalledGame: (game: LocalGameData) => void;
    setInstalledGames: (games: LocalGameData[]) => void;
    setGameMetadata: (metadata: GameMetadata[]) => void;
    removeGame: (id: number) => void;
    syncUserLibrary: () => Promise<void>;
}

const STORAGE_KEY = 'sh_user_library';

function loadStoredUserLibrary(): Record<number, UserLibraryEntry> {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) return JSON.parse(stored);
    } catch (e) {
        console.warn('Failed to parse stored user library:', e);
    }
    return {};
}

function saveUserLibrary(lib: Record<number, UserLibraryEntry>) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(lib));
    } catch (e) {
        console.warn('Failed to persist user library:', e);
    }
}

const initialUserLib = loadStoredUserLibrary();

export const useLibraryStore = create<LibraryState>((set, get) => ({
    userLibrary: initialUserLib,
    userGames: initialUserLib,
    installedGames: {},
    gameMetadata: {},

    isInLibrary: (id: number) => {
        const { userLibrary, installedGames } = get();
        return Boolean(userLibrary[id] || installedGames[id]);
    },

    isInstalled: (id: number) => {
        const { installedGames } = get();
        return Boolean(installedGames[id] && installedGames[id].path);
    },

    getLibrary: () => {
        const { userLibrary, installedGames, gameMetadata } = get();
        const allIds = new Set<number>([
            ...Object.keys(userLibrary).map(Number),
            ...Object.keys(installedGames).map(Number)
        ]);

        return Array.from(allIds).map(id => {
            const local = installedGames[id];
            const entry = userLibrary[id];
            const meta = gameMetadata[id];
            const isInstalled = Boolean(local && local.path);

            if (!meta) {
                return {
                    id,
                    title: `Game #${id}`,
                    install_path: local?.path,
                    is_installed: isInstalled,
                    playtime_minutes: 0,
                    added_at: entry?.added_at || new Date().toISOString()
                };
            }

            return {
                ...meta,
                install_path: local?.path,
                is_installed: isInstalled,
                added_at: entry?.added_at || new Date().toISOString()
            };
        });
    },

    addToLibrary: async (gameId: number, metadata?: Partial<GameMetadata>) => {
        const { userLibrary, gameMetadata, installedGames } = get();
        const isInstalled = Boolean(installedGames[gameId]);
        const updatedUserLib = {
            ...userLibrary,
            [gameId]: {
                game_id: gameId,
                added_at: userLibrary[gameId]?.added_at || new Date().toISOString(),
                status: isInstalled ? ('installed' as const) : ('uninstalled' as const)
            }
        };

        const updatedMeta = { ...gameMetadata };
        if (metadata) {
            updatedMeta[gameId] = {
                id: gameId,
                title: metadata.title || `Game #${gameId}`,
                cover_url: metadata.cover_url,
                header_image: metadata.header_image,
                background_url: metadata.background_url,
                description: metadata.description,
                summary: metadata.summary,
                developer: metadata.developer,
                publisher: metadata.publisher,
                release_date: metadata.release_date,
                rating: metadata.rating,
                genres: metadata.genres,
                categories: metadata.categories,
                steam_app_id: metadata.steam_app_id,
                igdb_id: metadata.igdb_id,
                playtime_minutes: metadata.playtime_minutes || 0,
            };
        }

        saveUserLibrary(updatedUserLib);
        set({ userLibrary: updatedUserLib, userGames: updatedUserLib, gameMetadata: updatedMeta });

        // Backend synchronization
        try {
            await api.post('/library/user', { game_id: gameId });
        } catch (err) {
            console.warn('Backend library sync failed (degraded to local storage):', err);
        }
    },

    removeFromLibrary: async (gameId: number) => {
        const { userLibrary } = get();
        const updated = { ...userLibrary };
        delete updated[gameId];
        saveUserLibrary(updated);
        set({ userLibrary: updated, userGames: updated });

        try {
            await api.delete(`/library/user/${gameId}`);
        } catch (err) {
            console.warn('Backend remove sync failed:', err);
        }
    },

    addInstalledGame: (game: LocalGameData) => {
        const { installedGames, userLibrary } = get();
        const updatedInstalled = {
            ...installedGames,
            [game.id]: game
        };
        const updatedUserLib = {
            ...userLibrary,
            [game.id]: {
                game_id: game.id,
                added_at: userLibrary[game.id]?.added_at || new Date().toISOString(),
                status: 'installed' as const
            }
        };
        saveUserLibrary(updatedUserLib);
        set({ installedGames: updatedInstalled, userLibrary: updatedUserLib, userGames: updatedUserLib });
    },

    setInstalledGames: (games) => {
        const record: Record<number, LocalGameData> = {};
        games.forEach(g => record[g.id] = g);

        // Ensure detected local games are in userLibrary
        const { userLibrary } = get();
        const updatedUserLib = { ...userLibrary };
        games.forEach(g => {
            if (!updatedUserLib[g.id]) {
                updatedUserLib[g.id] = {
                    game_id: g.id,
                    added_at: new Date().toISOString(),
                    status: 'installed'
                };
            }
        });
        saveUserLibrary(updatedUserLib);

        set({ installedGames: record, userLibrary: updatedUserLib, userGames: updatedUserLib });
    },

    setGameMetadata: (metadata) => {
        set(state => {
            const newMeta = { ...state.gameMetadata };
            metadata.forEach(m => newMeta[m.id] = m);
            return { gameMetadata: newMeta };
        });
    },

    removeGame: (id) => {
        set(state => {
            const newInstalled = { ...state.installedGames };
            delete newInstalled[id];
            return { installedGames: newInstalled };
        });
    },

    syncUserLibrary: async () => {
        try {
            const res = await api.get<any[]>('/library/user');
            if (Array.isArray(res.data) && res.data.length > 0) {
                const { userLibrary, gameMetadata } = get();
                const mergedUserLib = { ...userLibrary };
                const missingIds: number[] = [];

                res.data.forEach(item => {
                    mergedUserLib[item.game_id] = {
                        game_id: item.game_id,
                        added_at: item.added_at,
                        status: item.status
                    };
                    if (item.game && !gameMetadata[item.game_id]) {
                        gameMetadata[item.game_id] = {
                            id: item.game.id,
                            title: item.game.title,
                            cover_url: item.game.cover_url,
                            header_image: item.game.header_image,
                            background_url: item.game.background_url,
                            playtime_minutes: item.game.playtime_minutes || 0,
                            steam_app_id: item.game.steam_app_id,
                            description: item.game.short_description || item.game.description,
                            developer: item.game.developer,
                            publisher: item.game.publisher,
                            genres: item.game.genres,
                            rating: item.game.rating,
                        };
                    } else if (!gameMetadata[item.game_id]) {
                        missingIds.push(item.game_id);
                    }
                });

                saveUserLibrary(mergedUserLib);
                set({
                    userLibrary: mergedUserLib,
                    userGames: mergedUserLib,
                    gameMetadata: { ...gameMetadata }
                });

                if (missingIds.length > 0) {
                    try {
                        const batchRes = await api.post<GameMetadata[]>('/store/metadata/batch', missingIds);
                        if (batchRes.data) {
                            get().setGameMetadata(batchRes.data);
                        }
                    } catch (e) {
                        console.warn('Failed to batch fetch missing game metadata:', e);
                    }
                }
            }
        } catch (err) {
            console.warn('Failed to sync user library from server:', err);
        }
    }
}));
