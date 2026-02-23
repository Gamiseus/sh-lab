import { create } from 'zustand';

// What we know from the scanner (Rust)
export interface LocalGameData {
    id: number;
    path: string; // The specific folder path for this installation
}

// What we know from the Backend
export interface GameMetadata {
    id: number;
    title: string;
    cover_url?: string;
    playtime_minutes: number;
    // ... other metadata
}

// Combined View
export interface LibraryGame extends GameMetadata {
    install_path: string;
}

interface LibraryState {
    // Core Identity: The List of Installed Games (ID -> Path)
    // We use a Map or Record for quick lookup
    installedGames: Record<number, LocalGameData>;

    // Cache of Metadata (ID -> Metadata)
    gameMetadata: Record<number, GameMetadata>;

    // Computed: Get full library list
    getLibrary: () => LibraryGame[];

    // Actions
    setInstalledGames: (games: LocalGameData[]) => void;
    setGameMetadata: (metadata: GameMetadata[]) => void;
    removeGame: (id: number) => void;
}

export const useLibraryStore = create<LibraryState>((set, get) => ({
    installedGames: {},
    gameMetadata: {},

    getLibrary: () => {
        const { installedGames, gameMetadata } = get();
        return Object.values(installedGames).map(local => {
            const meta = gameMetadata[local.id];
            // If metadata missing, return a placeholder
            if (!meta) {
                return {
                    id: local.id,
                    title: `Game #${local.id}`,
                    install_path: local.path,
                    playtime_minutes: 0
                };
            }
            return {
                ...meta,
                install_path: local.path
            };
        });
    },

    setInstalledGames: (games) => {
        const record: Record<number, LocalGameData> = {};
        games.forEach(g => record[g.id] = g);
        set({ installedGames: record });
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
    }
}));
