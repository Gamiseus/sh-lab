import { create } from "zustand";
import { API_BASE } from "@/lib/api";
import { useLibraryStore } from "./LibraryStore";

export type DownloadStatus =
  | "queued"
  | "preparing"
  | "downloading"
  | "paused"
  | "completed"
  | "error";

export interface DownloadMetrics {
  progress_percent: number;
  speed_bytes_sec: number;
  speed_mb_sec: number;
  eta_seconds: number | null;
}

export function calculateDownloadMetrics(
  transferredBytes: number,
  totalBytes: number,
  elapsedSeconds: number
): DownloadMetrics {
  let progress_percent = 0.0;
  if (totalBytes > 0) {
    progress_percent = Math.min(100.0, (transferredBytes / totalBytes) * 100.0);
  }

  let speed_bytes_sec = 0.0;
  let eta_seconds: number | null = null;

  if (elapsedSeconds > 0 && transferredBytes > 0) {
    speed_bytes_sec = transferredBytes / elapsedSeconds;
    const remaining_bytes = Math.max(0, totalBytes - transferredBytes);
    eta_seconds = speed_bytes_sec > 0 ? remaining_bytes / speed_bytes_sec : null;
  }

  const speed_mb_sec = speed_bytes_sec / (1024 * 1024);

  return {
    progress_percent: Math.round(progress_percent * 10) / 10,
    speed_bytes_sec: speed_bytes_sec,
    speed_mb_sec: Math.round(speed_mb_sec * 100) / 100,
    eta_seconds: eta_seconds !== null ? Math.round(eta_seconds * 10) / 10 : null,
  };
}

export function formatSpeed(speedMbSec: number): string {
  if (!speedMbSec || speedMbSec <= 0) return "0.0 MB/s";
  return `${speedMbSec.toFixed(1)} MB/s`;
}

export function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function formatETA(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "--";
  if (seconds <= 0) return "0s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return `${mins}m ${secs}s`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h ${remainingMins}m`;
}

export interface DownloadItem {
  id: number;
  title: string;
  cover_url?: string;
  header_image?: string;
  totalBytes: number;
  downloadedBytes: number;
  speed: string; // for compatibility with existing UI
  speedBytesPerSec: number;
  speedMbPerSec: number;
  etaSeconds: number | null;
  progressPercent: number;
  status: DownloadStatus;
  statusMessage?: string;
  serverTaskId?: string | null;
  installPath?: string;
  startedAt?: number;
  completedAt?: string;
  error?: string;
}

export interface EnqueueOptions {
  id: number;
  title: string;
  cover_url?: string;
  header_image?: string;
  installPath?: string;
  totalBytes?: number;
  autoStart?: boolean;
}

interface StoredQueueData {
  queue: DownloadItem[];
  paused: DownloadItem[];
  completed: DownloadItem[];
}

const STORAGE_KEY = "sh_download_queue";

function loadStoredQueue(): StoredQueueData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        queue: Array.isArray(parsed.queue) ? parsed.queue : [],
        paused: Array.isArray(parsed.paused) ? parsed.paused : [],
        completed: Array.isArray(parsed.completed) ? parsed.completed : [],
      };
    }
  } catch (e) {
    console.warn("Failed to parse stored download queue:", e);
  }
  return { queue: [], paused: [], completed: [] };
}

function saveStoredQueue(data: StoredQueueData) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (e) {
    console.warn("Failed to persist download queue:", e);
  }
}

async function safeInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T | null> {
  try {
    if (typeof window !== "undefined" && "__TAURI_INTERNALS__" in window) {
      const { invoke } = await import("@tauri-apps/api/core");
      return await invoke<T>(cmd, args);
    }
  } catch (err) {
    console.warn(`[DownloadStore] Tauri invoke ${cmd} failed:`, err);
  }
  return null;
}

function getPrimaryLibraryPath(): string {
  try {
    if (typeof window !== "undefined" && typeof localStorage !== "undefined") {
      const saved =
        localStorage.getItem("sh_library_paths") ||
        localStorage.getItem("library-paths");
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0 && parsed[0]) {
          return parsed[0];
        }
      }
    }
  } catch {
    // fallback
  }
  return "c:\\Users\\Administrator\\Documents\\Projects\\sh-lab\\data\\games";
}

// In-memory active streaming controllers
const activeControllers: Map<number, AbortController> = new Map();
const activeEventSources: Map<number, EventSource> = new Map();

interface DownloadStoreState {
  activeDownload: DownloadItem | null;
  queue: DownloadItem[];
  paused: DownloadItem[];
  completed: DownloadItem[];
  isPausedAll: boolean;

  // Actions
  enqueueDownload: (options: EnqueueOptions) => Promise<void>;
  startDownload: (gameId: number) => Promise<void>;
  pauseDownload: (gameId: number) => void;
  resumeDownload: (gameId: number) => void;
  cancelDownload: (gameId: number) => void;
  pauseAll: () => void;
  resumeAll: () => void;
  clearCompleted: () => void;
  removeCompleted: (gameId: number) => void;
  reorderQueue: (gameId: number, direction: "up" | "down") => void;

  // Progress update helpers
  updateProgress: (
    gameId: number,
    downloadedBytes: number,
    totalBytes: number,
    elapsedSeconds: number,
    statusMessage?: string
  ) => void;
  setDownloadStatus: (
    gameId: number,
    status: DownloadStatus,
    statusMessage?: string
  ) => void;
}

const initialData = loadStoredQueue();

export const useDownloadStore = create<DownloadStoreState>((set, get) => ({
  activeDownload: null,
  queue: initialData.queue,
  paused: initialData.paused,
  completed: initialData.completed,
  isPausedAll: false,

  enqueueDownload: async (options: EnqueueOptions) => {
    const { activeDownload, queue, paused, completed } = get();

    // Check if already in active, queue, or paused
    if (activeDownload?.id === options.id) return;
    if (queue.some((i) => i.id === options.id)) return;
    if (paused.some((i) => i.id === options.id)) return;

    // Remove from completed if re-downloading
    const newCompleted = completed.filter((i) => i.id !== options.id);

    const newItem: DownloadItem = {
      id: options.id,
      title: options.title,
      cover_url: options.cover_url,
      header_image: options.header_image,
      totalBytes: options.totalBytes || 0,
      downloadedBytes: 0,
      speed: "0.0 MB/s",
      speedBytesPerSec: 0,
      speedMbPerSec: 0,
      etaSeconds: null,
      progressPercent: 0,
      status: "queued",
      statusMessage: "Waiting in queue...",
      installPath: options.installPath || `${getPrimaryLibraryPath()}\\${options.title}`,
    };

    const newQueue = [...queue, newItem];
    saveStoredQueue({ queue: newQueue, paused, completed: newCompleted });
    set({ queue: newQueue, completed: newCompleted });

    // If no active download and not globally paused, start right away
    if (!get().activeDownload && !get().isPausedAll && options.autoStart !== false) {
      await get().startDownload(options.id);
    }
  },

  startDownload: async (gameId: number) => {
    const state = get();
    if (state.activeDownload && state.activeDownload.id !== gameId) {
      // Already another download active, keep this one queued
      return;
    }

    let target: DownloadItem | undefined =
      state.activeDownload?.id === gameId
        ? state.activeDownload
        : state.queue.find((i) => i.id === gameId) ||
          state.paused.find((i) => i.id === gameId);

    if (!target) return;

    // Promote to active download
    const newQueue = state.queue.filter((i) => i.id !== gameId);
    const newPaused = state.paused.filter((i) => i.id !== gameId);

    const activeItem: DownloadItem = {
      ...target,
      status: "preparing",
      statusMessage: "Checking server cache...",
      startedAt: Date.now(),
    };

    set({
      activeDownload: activeItem,
      queue: newQueue,
      paused: newPaused,
    });
    saveStoredQueue({
      queue: newQueue,
      paused: newPaused,
      completed: state.completed,
    });

    const abortController = new AbortController();
    activeControllers.set(gameId, abortController);

    try {
      const token =
        localStorage.getItem("sh_access_token") ||
        localStorage.getItem("token") ||
        "";

      // 1. Request install check from backend
      const reqUrl = `${API_BASE}/library/install/${gameId}/request`;
      const reqResp = await fetch(reqUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal: abortController.signal,
      });

      if (!reqResp.ok) {
        throw new Error(`Install request failed: ${reqResp.statusText}`);
      }

      const reqData = await reqResp.json();

      // 2. If not cached, listen to SSE stream for SteamCMD depot caching
      if (!reqData.cached && reqData.task_id) {
        set((s) => ({
          activeDownload: s.activeDownload
            ? {
                ...s.activeDownload,
                status: "preparing",
                serverTaskId: reqData.task_id,
                statusMessage: "Downloading Steam depot cache on server...",
              }
            : null,
        }));

        await new Promise<void>((resolve, reject) => {
          const sseUrl = `${API_BASE}/library/tasks/${reqData.task_id}/stream?token=${encodeURIComponent(token)}`;
          const eventSource = new EventSource(sseUrl);
          activeEventSources.set(gameId, eventSource);

          eventSource.onmessage = (event) => {
            try {
              const parsed = JSON.parse(event.data);
              if (parsed.status === "completed" || parsed.done) {
                eventSource.close();
                activeEventSources.delete(gameId);
                resolve();
              } else if (parsed.status === "failed" || parsed.error) {
                eventSource.close();
                activeEventSources.delete(gameId);
                reject(new Error(parsed.error || "SteamCMD depot download failed"));
              } else if (parsed.progress_percent !== undefined) {
                set((s) => ({
                  activeDownload: s.activeDownload
                    ? {
                        ...s.activeDownload,
                        progressPercent: parsed.progress_percent,
                        statusMessage: `Server caching depot: ${parsed.progress_percent}%`,
                      }
                    : null,
                }));
              }
            } catch (e) {
              console.warn("SSE parsing error:", e);
            }
          };

          eventSource.onerror = () => {
            eventSource.close();
            activeEventSources.delete(gameId);
            // If SSE stream ends or closes gracefully, continue to prepare check
            resolve();
          };

          abortController.signal.addEventListener("abort", () => {
            eventSource.close();
            activeEventSources.delete(gameId);
            reject(new Error("Download aborted"));
          });
        });
      }

      // 3. Prepare file manifest & total size
      const prepUrl = `${API_BASE}/library/install/${gameId}/prepare`;
      const prepResp = await fetch(prepUrl, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        signal: abortController.signal,
      });

      let totalBytes = activeItem.totalBytes;
      let files: Array<{ path: string; size: number }> = [];

      if (!prepResp.ok) {
        const errorData = await prepResp.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server preparation failed: ${prepResp.statusText}`);
      }

      const prepData = await prepResp.json();
      totalBytes = prepData.total_size || totalBytes;
      files = Array.isArray(prepData.files) ? prepData.files : [];

      if (files.length === 0) {
        throw new Error("No game files found on server repository");
      }

      set((s) => ({
        activeDownload: s.activeDownload
          ? {
              ...s.activeDownload,
              status: "downloading",
              totalBytes,
              statusMessage: "Streaming game files...",
            }
          : null,
      }));

      // 4. Client-side HTTP chunk streaming
      let downloadedBytes = activeItem.downloadedBytes;
      const startTime = performance.now();
      const targetInstallDir =
        activeItem.installPath || `${getPrimaryLibraryPath()}\\${activeItem.title}`;

      for (const file of files) {
        if (abortController.signal.aborted) break;

        const fileUrl = `${API_BASE}/library/download/${gameId}/${file.path}`;
        const headers: Record<string, string> = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        // RFC 7233: Only send Range if file has positive length (> 0).
        // 0-byte files cannot satisfy any byte range and trigger HTTP 416 Range Not Satisfiable.
        if (file.size > 0) {
          headers["Range"] = `bytes=0-${file.size - 1}`;
        }

        const fileResp = await fetch(fileUrl, {
          headers,
          signal: abortController.signal,
        });

        // 200, 206, or 416 on 0-byte file are acceptable completion statuses
        const isSuccess =
          fileResp.ok ||
          fileResp.status === 206 ||
          (file.size === 0 && fileResp.status === 416);

        if (!isSuccess) {
          throw new Error(`Failed to stream ${file.path}: ${fileResp.statusText}`);
        }

        const chunks: Uint8Array[] = [];
        if (file.size > 0 && fileResp.body) {
          const reader = fileResp.body.getReader();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            if (value) {
              chunks.push(value);
              downloadedBytes += value.length;
              const elapsedSec = (performance.now() - startTime) / 1000;
              get().updateProgress(
                gameId,
                downloadedBytes,
                totalBytes,
                elapsedSec,
                `Streaming ${file.path}...`
              );
            }
          }
        } else {
          // 0-byte file or response with empty body
          const elapsedSec = (performance.now() - startTime) / 1000;
          get().updateProgress(
            gameId,
            downloadedBytes,
            totalBytes,
            elapsedSec,
            `Streaming ${file.path}...`
          );
        }

        // If running in Tauri desktop app, persist file to target install directory
        if (typeof window !== "undefined" && "__TAURI_INTERNALS__" in window) {
          let fileBytes: Uint8Array;
          if (chunks.length === 1) {
            fileBytes = chunks[0];
          } else if (chunks.length > 1) {
            const totalChunkLength = chunks.reduce((acc, c) => acc + c.length, 0);
            fileBytes = new Uint8Array(totalChunkLength);
            let offset = 0;
            for (const chunk of chunks) {
              fileBytes.set(chunk, offset);
              offset += chunk.length;
            }
          } else {
            fileBytes = new Uint8Array(0);
          }

          await safeInvoke("save_game_file_command", {
            gameDir: targetInstallDir,
            relativePath: file.path,
            data: Array.from(fileBytes),
          });
        }
      }

      // Finalize installation on disk if running under Tauri
      if (typeof window !== "undefined" && "__TAURI_INTERNALS__" in window) {
        await safeInvoke("finalize_game_installation_command", {
          gameDir: targetInstallDir,
          gameId,
          gameTitle: activeItem.title,
        });
      }

      // 5. Completion transition
      const currentActive = get().activeDownload;
      if (currentActive && currentActive.id === gameId) {
        const completedItem: DownloadItem = {
          ...currentActive,
          status: "completed",
          downloadedBytes: totalBytes,
          progressPercent: 100.0,
          speed: "0.0 MB/s",
          speedBytesPerSec: 0,
          speedMbPerSec: 0,
          etaSeconds: 0.0,
          statusMessage: "Download complete",
          completedAt: new Date().toISOString(),
        };

        const updatedCompleted = [completedItem, ...get().completed];
        saveStoredQueue({
          queue: get().queue,
          paused: get().paused,
          completed: updatedCompleted,
        });

        // Register in LibraryStore as installed
        const libStore = useLibraryStore.getState();
        const installDir = targetInstallDir;
        libStore.addInstalledGame({
          id: gameId,
          path: installDir,
        });

        set({
          activeDownload: null,
          completed: updatedCompleted,
        });

        // Process next item in queue
        const nextQueue = get().queue;
        if (nextQueue.length > 0 && !get().isPausedAll) {
          get().startDownload(nextQueue[0].id);
        }
      }
    } catch (err: unknown) {
      if (abortController.signal.aborted) {
        // Was paused or cancelled intentionally
        return;
      }
      console.error(`Download failed for game ${gameId}:`, err);
      const errMsg = err instanceof Error ? err.message : String(err);
      set((s) => ({
        activeDownload: s.activeDownload
          ? {
              ...s.activeDownload,
              status: "error",
              error: errMsg,
              statusMessage: `Error: ${errMsg}`,
              speed: "0.0 MB/s",
              speedBytesPerSec: 0,
              speedMbPerSec: 0,
              etaSeconds: null,
            }
          : null,
      }));
    } finally {
      activeControllers.delete(gameId);
      const sse = activeEventSources.get(gameId);
      if (sse) {
        sse.close();
        activeEventSources.delete(gameId);
      }
    }
  },

  pauseDownload: (gameId: number) => {
    const { activeDownload, queue, paused, completed } = get();

    // Abort ongoing network transfer
    const controller = activeControllers.get(gameId);
    if (controller) controller.abort();
    const sse = activeEventSources.get(gameId);
    if (sse) sse.close();

    let targetItem: DownloadItem | null = null;
    let newQueue = queue;

    if (activeDownload && activeDownload.id === gameId) {
      targetItem = {
        ...activeDownload,
        status: "paused",
        statusMessage: "Download paused",
        speed: "0.0 MB/s",
        speedBytesPerSec: 0,
        speedMbPerSec: 0,
        etaSeconds: null,
      };
      set({ activeDownload: null });
    } else {
      const qItem = queue.find((i) => i.id === gameId);
      if (qItem) {
        targetItem = {
          ...qItem,
          status: "paused",
          statusMessage: "Download paused",
          speed: "0.0 MB/s",
          speedBytesPerSec: 0,
          speedMbPerSec: 0,
          etaSeconds: null,
        };
        newQueue = queue.filter((i) => i.id !== gameId);
      }
    }

    if (targetItem) {
      const newPaused = [...paused.filter((i) => i.id !== gameId), targetItem];
      saveStoredQueue({ queue: newQueue, paused: newPaused, completed });
      set({ queue: newQueue, paused: newPaused });
    }
  },

  resumeDownload: (gameId: number) => {
    const { paused, queue, completed } = get();
    const target = paused.find((i) => i.id === gameId);
    if (!target) return;

    const newPaused = paused.filter((i) => i.id !== gameId);
    const resumedItem: DownloadItem = {
      ...target,
      status: "queued",
      statusMessage: "Waiting to resume...",
    };

    const newQueue = [...queue, resumedItem];
    saveStoredQueue({ queue: newQueue, paused: newPaused, completed });
    set({ paused: newPaused, queue: newQueue });

    if (!get().activeDownload && !get().isPausedAll) {
      get().startDownload(gameId);
    }
  },

  cancelDownload: (gameId: number) => {
    const controller = activeControllers.get(gameId);
    if (controller) controller.abort();
    const sse = activeEventSources.get(gameId);
    if (sse) sse.close();

    const { activeDownload, queue, paused, completed } = get();
    const newActive = activeDownload?.id === gameId ? null : activeDownload;
    const newQueue = queue.filter((i) => i.id !== gameId);
    const newPaused = paused.filter((i) => i.id !== gameId);

    saveStoredQueue({ queue: newQueue, paused: newPaused, completed });
    set({
      activeDownload: newActive,
      queue: newQueue,
      paused: newPaused,
    });

    if (!newActive && newQueue.length > 0 && !get().isPausedAll) {
      get().startDownload(newQueue[0].id);
    }
  },

  pauseAll: () => {
    const { activeDownload, queue } = get();
    if (activeDownload) {
      get().pauseDownload(activeDownload.id);
    }
    queue.forEach((item) => {
      get().pauseDownload(item.id);
    });
    set({ isPausedAll: true });
  },

  resumeAll: () => {
    const { paused } = get();
    set({ isPausedAll: false });
    paused.forEach((item) => {
      get().resumeDownload(item.id);
    });
  },

  clearCompleted: () => {
    const { queue, paused } = get();
    saveStoredQueue({ queue, paused, completed: [] });
    set({ completed: [] });
  },

  removeCompleted: (gameId: number) => {
    const { queue, paused, completed } = get();
    const newCompleted = completed.filter((i) => i.id !== gameId);
    saveStoredQueue({ queue, paused, completed: newCompleted });
    set({ completed: newCompleted });
  },

  reorderQueue: (gameId: number, direction: "up" | "down") => {
    const { queue, paused, completed } = get();
    const index = queue.findIndex((i) => i.id === gameId);
    if (index === -1) return;

    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= queue.length) return;

    const newQueue = [...queue];
    const [moved] = newQueue.splice(index, 1);
    newQueue.splice(targetIndex, 0, moved);

    saveStoredQueue({ queue: newQueue, paused, completed });
    set({ queue: newQueue });
  },

  updateProgress: (
    gameId: number,
    downloadedBytes: number,
    totalBytes: number,
    elapsedSeconds: number,
    statusMessage?: string
  ) => {
    const metrics = calculateDownloadMetrics(
      downloadedBytes,
      totalBytes,
      elapsedSeconds
    );

    set((state) => {
      if (state.activeDownload && state.activeDownload.id === gameId) {
        return {
          activeDownload: {
            ...state.activeDownload,
            downloadedBytes,
            totalBytes,
            progressPercent: metrics.progress_percent,
            speedBytesPerSec: metrics.speed_bytes_sec,
            speedMbPerSec: metrics.speed_mb_sec,
            speed: formatSpeed(metrics.speed_mb_sec),
            etaSeconds: metrics.eta_seconds,
            statusMessage: statusMessage || state.activeDownload.statusMessage,
          },
        };
      }
      return state;
    });
  },

  setDownloadStatus: (
    gameId: number,
    status: DownloadStatus,
    statusMessage?: string
  ) => {
    set((state) => {
      if (state.activeDownload && state.activeDownload.id === gameId) {
        return {
          activeDownload: {
            ...state.activeDownload,
            status,
            statusMessage: statusMessage || state.activeDownload.statusMessage,
          },
        };
      }
      return state;
    });
  },
}));
