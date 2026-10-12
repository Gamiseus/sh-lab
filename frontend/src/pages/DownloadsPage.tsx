import { Link, useNavigate } from "react-router-dom";
import {
  Download,
  HardDrive,
  Activity,
  CheckCircle2,
  Pause,
  Play,
  Trash2,
  ArrowUpRight,
  FolderDown,
  ArrowUp,
  ArrowDown,
  FolderOpen,
  Clock,
  Sparkles,
} from "lucide-react";
import {
  useDownloadStore,
  formatSpeed,
  formatBytes,
  formatETA,
  DownloadItem,
} from "@/stores/DownloadStore";

export function DownloadsPage() {
  const navigate = useNavigate();

  const activeDownload = useDownloadStore((s) => s.activeDownload);
  const queue = useDownloadStore((s) => s.queue);
  const paused = useDownloadStore((s) => s.paused);
  const completed = useDownloadStore((s) => s.completed);
  const isPausedAll = useDownloadStore((s) => s.isPausedAll);

  const pauseAll = useDownloadStore((s) => s.pauseAll);
  const resumeAll = useDownloadStore((s) => s.resumeAll);
  const pauseDownload = useDownloadStore((s) => s.pauseDownload);
  const resumeDownload = useDownloadStore((s) => s.resumeDownload);
  const cancelDownload = useDownloadStore((s) => s.cancelDownload);
  const clearCompleted = useDownloadStore((s) => s.clearCompleted);
  const removeCompleted = useDownloadStore((s) => s.removeCompleted);
  const reorderQueue = useDownloadStore((s) => s.reorderQueue);

  // Maintain activeDownloads array for test contract compatibility
  const activeDownloads: DownloadItem[] = activeDownload
    ? [activeDownload, ...queue, ...paused]
    : [...queue, ...paused];
  const completedDownloads: DownloadItem[] = completed;

  const currentSpeed = activeDownload ? formatSpeed(activeDownload.speedMbPerSec) : "0.0 MB/s";
  const diskSpeed = activeDownload
    ? formatSpeed(activeDownload.speedMbPerSec * 0.98)
    : "0.0 MB/s";

  const handleLaunchGame = (item: DownloadItem) => {
    navigate(`/games/${item.id}`);
  };

  const handleOpenFolder = (item: DownloadItem) => {
    const path =
      item.installPath ||
      `c:\\Users\\Administrator\\Documents\\Projects\\sh-lab\\data\\games\\${item.title}`;
    console.info("Opening folder at path:", path);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
            <Download className="w-8 h-8 text-violet-400" />
            Downloads & Installs
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Monitor real-time transfer speeds, installation queues, and drive allocations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => (isPausedAll ? resumeAll() : pauseAll())}
            disabled={activeDownloads.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-sm font-medium transition-colors border border-white/10 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isPausedAll ? (
              <>
                <Play className="w-4 h-4 text-emerald-400" />
                <span>Resume All</span>
              </>
            ) : (
              <>
                <Pause className="w-4 h-4 text-amber-400" />
                <span>Pause All</span>
              </>
            )}
          </button>
          <Link
            to="/settings"
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-violet-600/20"
          >
            Storage Settings
          </Link>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-violet-600/10 text-violet-400 border border-violet-500/20">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Download Speed
            </p>
            <p className="text-2xl font-bold text-white mt-0.5">
              {currentSpeed.replace(" MB/s", "")}{" "}
              <span className="text-sm font-normal text-zinc-400">MB/s</span>
            </p>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/20">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Disk Write Speed
            </p>
            <p className="text-2xl font-bold text-white mt-0.5">
              {diskSpeed.replace(" MB/s", "")}{" "}
              <span className="text-sm font-normal text-zinc-400">MB/s</span>
            </p>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-blue-600/10 text-blue-400 border border-blue-500/20">
            <FolderDown className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              In Queue
            </p>
            <p className="text-2xl font-bold text-white mt-0.5">
              {activeDownloads.length}{" "}
              <span className="text-sm font-normal text-zinc-400">items</span>
            </p>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-zinc-900/60 border border-white/5 flex items-center gap-4">
          <div className="p-3 rounded-lg bg-emerald-600/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Completed
            </p>
            <p className="text-2xl font-bold text-white mt-0.5">
              {completedDownloads.length}{" "}
              <span className="text-sm font-normal text-zinc-400">items</span>
            </p>
          </div>
        </div>
      </div>

      {/* Active Download Hero Card */}
      {activeDownload && (
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-zinc-900 via-zinc-900/90 to-zinc-950 border border-violet-500/30 p-6 shadow-2xl space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {activeDownload.cover_url || activeDownload.header_image ? (
                <img
                  src={activeDownload.cover_url || activeDownload.header_image}
                  alt={activeDownload.title}
                  className="w-16 h-20 rounded-lg object-cover border border-white/10 shadow-md"
                />
              ) : (
                <div className="w-16 h-20 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400">
                  <Download className="w-8 h-8" />
                </div>
              )}
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-bold text-white">
                    {activeDownload.title}
                  </h3>
                  <span
                    className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${
                      activeDownload.status === "downloading"
                        ? "bg-violet-500/10 text-violet-300 border-violet-500/30 animate-pulse"
                        : activeDownload.status === "preparing"
                        ? "bg-amber-500/10 text-amber-300 border-amber-500/30 animate-pulse"
                        : "bg-zinc-800 text-zinc-300 border-white/10"
                    }`}
                  >
                    {activeDownload.status === "downloading"
                      ? "Downloading"
                      : activeDownload.status === "preparing"
                      ? "Preparing Depot"
                      : "Paused"}
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-1">
                  {activeDownload.statusMessage || "Transferring data from server cache..."}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-end md:self-center">
              {activeDownload.status === "paused" ? (
                <button
                  onClick={() => resumeDownload(activeDownload.id)}
                  className="flex items-center gap-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md shadow-emerald-600/20"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Resume</span>
                </button>
              ) : (
                <button
                  onClick={() => pauseDownload(activeDownload.id)}
                  className="flex items-center gap-2 px-3.5 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg text-xs font-semibold transition-all border border-white/10"
                >
                  <Pause className="w-3.5 h-3.5 text-amber-400" />
                  <span>Pause</span>
                </button>
              )}
              <button
                onClick={() => cancelDownload(activeDownload.id)}
                className="flex items-center gap-2 px-3.5 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-300 rounded-lg text-xs font-semibold transition-all border border-red-500/20"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Cancel</span>
              </button>
            </div>
          </div>

          {/* Live Progress Bar */}
          <div className="space-y-2">
            <div className="w-full bg-zinc-800/80 rounded-full h-3 overflow-hidden border border-white/5">
              <div
                className="bg-gradient-to-r from-violet-600 via-indigo-500 to-emerald-400 h-full rounded-full transition-all duration-300 ease-out"
                style={{ width: `${activeDownload.progressPercent}%` }}
              />
            </div>
            <div className="flex flex-wrap items-center justify-between text-xs text-zinc-400 gap-2">
              <div className="flex items-center gap-3">
                <span className="font-semibold text-white">
                  {activeDownload.progressPercent.toFixed(1)}%
                </span>
                <span>
                  {formatBytes(activeDownload.downloadedBytes)} of{" "}
                  {formatBytes(activeDownload.totalBytes)}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-violet-400 font-medium">
                  {formatSpeed(activeDownload.speedMbPerSec)}
                </span>
                <span className="flex items-center gap-1 text-zinc-400">
                  <Clock className="w-3 h-3 text-zinc-500" />
                  {formatETA(activeDownload.etaSeconds)} remaining
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Queue Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>Active Queue</span>
            {queue.length > 0 && (
              <span className="text-xs px-2 py-0.5 bg-violet-600/20 border border-violet-500/30 text-violet-300 rounded-full font-normal">
                {queue.length} pending
              </span>
            )}
          </h2>
        </div>

        {activeDownloads.length === 0 ? (
          <div className="p-12 rounded-2xl bg-zinc-900/40 border border-white/5 flex flex-col items-center justify-center text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
              <Download className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">No active downloads</h3>
              <p className="text-sm text-zinc-400 mt-1 max-w-md">
                Your queue is currently empty. Browse the game store catalog to install new games or check for updates.
              </p>
            </div>
            <Link
              to="/store"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-violet-600/20"
            >
              Browse Games in Store
              <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Queued / Paused items (excluding activeDownload which is displayed in the hero card) */}
            {[...queue, ...paused].map((item, idx) => (
              <div
                key={item.id}
                className="p-4 rounded-xl bg-zinc-900/70 border border-white/5 flex items-center justify-between gap-4 hover:border-white/10 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="text-xs font-bold text-zinc-500 w-5 text-center">
                    #{idx + 1}
                  </div>
                  {item.cover_url ? (
                    <img
                      src={item.cover_url}
                      alt={item.title}
                      className="w-10 h-12 rounded object-cover border border-white/10 flex-shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-12 rounded bg-zinc-800 border border-white/10 flex items-center justify-center text-zinc-500 flex-shrink-0">
                      <Download className="w-5 h-5" />
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-white truncate text-sm">
                        {item.title}
                      </h4>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                          item.status === "paused"
                            ? "bg-amber-500/10 text-amber-300 border-amber-500/20"
                            : "bg-blue-500/10 text-blue-300 border-blue-500/20"
                        }`}
                      >
                        {item.status === "paused" ? "Paused" : "Queued"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-zinc-400 mt-1">
                      <span>{formatBytes(item.totalBytes)}</span>
                      {item.downloadedBytes > 0 && (
                        <span>• {item.progressPercent.toFixed(1)}% downloaded</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <button
                    onClick={() => reorderQueue(item.id, "up")}
                    disabled={idx === 0}
                    className="p-1.5 hover:bg-white/10 rounded-lg text-zinc-400 hover:text-white transition-colors disabled:opacity-20 disabled:cursor-not-allowed"
                    title="Move Up"
                  >
                    <ArrowUp className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => reorderQueue(item.id, "down")}
                    disabled={idx === queue.length - 1}
                    className="p-1.5 hover:bg-white/10 rounded-lg text-zinc-400 hover:text-white transition-colors disabled:opacity-20 disabled:cursor-not-allowed"
                    title="Move Down"
                  >
                    <ArrowDown className="w-4 h-4" />
                  </button>
                  {item.status === "paused" ? (
                    <button
                      onClick={() => resumeDownload(item.id)}
                      className="p-1.5 hover:bg-emerald-500/20 rounded-lg text-emerald-400 transition-colors"
                      title="Resume"
                    >
                      <Play className="w-4 h-4 fill-current" />
                    </button>
                  ) : (
                    <button
                      onClick={() => pauseDownload(item.id)}
                      className="p-1.5 hover:bg-amber-500/20 rounded-lg text-amber-400 transition-colors"
                      title="Pause"
                    >
                      <Pause className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={() => cancelDownload(item.id)}
                    className="p-1.5 hover:bg-red-500/20 rounded-lg text-zinc-400 hover:text-red-400 transition-colors"
                    title="Remove from queue"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Completed Downloads Section */}
      {completedDownloads.length > 0 && (
        <div className="space-y-4 pt-4 border-t border-white/5">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              Completed Installs ({completedDownloads.length})
            </h2>
            <button
              onClick={() => clearCompleted()}
              className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              Clear History
            </button>
          </div>

          <div className="space-y-3">
            {completedDownloads.map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-xl bg-zinc-900/50 border border-white/5 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <h4 className="font-semibold text-white text-sm truncate">
                      {item.title}
                    </h4>
                    <p className="text-xs text-zinc-400 mt-0.5">
                      {formatBytes(item.totalBytes)} • Installed successfully
                      {item.completedAt && ` • ${new Date(item.completedAt).toLocaleDateString()}`}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleLaunchGame(item)}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-colors"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Play</span>
                  </button>
                  <button
                    onClick={() => handleOpenFolder(item)}
                    className="p-1.5 hover:bg-white/10 rounded-lg text-zinc-400 hover:text-white transition-colors"
                    title="Open game folder"
                  >
                    <FolderOpen className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => removeCompleted(item.id)}
                    className="p-1.5 hover:bg-red-500/20 rounded-lg text-zinc-400 hover:text-red-400 transition-colors"
                    title="Remove from history"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
