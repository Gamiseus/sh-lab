import { calculateDownloadMetrics, formatSpeed, formatBytes, formatETA } from "../../frontend/src/stores/DownloadStore";

console.log("Running DownloadStore empirical test harness...");

// 1. formatSpeed
if (formatSpeed(0) !== "0.0 MB/s") throw new Error(`formatSpeed(0) failed: ${formatSpeed(0)}`);
if (formatSpeed(-1) !== "0.0 MB/s") throw new Error(`formatSpeed(-1) failed: ${formatSpeed(-1)}`);
if (formatSpeed(12.34) !== "12.3 MB/s") throw new Error(`formatSpeed(12.34) failed: ${formatSpeed(12.34)}`);

// 2. formatBytes
if (formatBytes(0) !== "0 B") throw new Error(`formatBytes(0) failed: ${formatBytes(0)}`);
if (formatBytes(1024) !== "1 KB") throw new Error(`formatBytes(1024) failed: ${formatBytes(1024)}`);
if (formatBytes(1048576) !== "1 MB") throw new Error(`formatBytes(1048576) failed: ${formatBytes(1048576)}`);

// 3. formatETA
if (formatETA(null) !== "--") throw new Error(`formatETA(null) failed: ${formatETA(null)}`);
if (formatETA(0) !== "0s") throw new Error(`formatETA(0) failed: ${formatETA(0)}`);
if (formatETA(45) !== "45s") throw new Error(`formatETA(45) failed: ${formatETA(45)}`);
if (formatETA(90) !== "1m 30s") throw new Error(`formatETA(90) failed: ${formatETA(90)}`);
if (formatETA(3665) !== "1h 1m") throw new Error(`formatETA(3665) failed: ${formatETA(3665)}`);

// 4. calculateDownloadMetrics boundaries
const m1 = calculateDownloadMetrics(0, 0, 1.0);
if (m1.progress_percent !== 0.0 || m1.speed_bytes_sec !== 0.0 || m1.eta_seconds !== null) {
  throw new Error(`m1 boundary failed: ${JSON.stringify(m1)}`);
}

const m2 = calculateDownloadMetrics(50, 100, 1.0);
if (m2.progress_percent !== 50.0 || m2.eta_seconds !== 1.0) {
  throw new Error(`m2 boundary failed: ${JSON.stringify(m2)}`);
}

const m3 = calculateDownloadMetrics(100, 100, 2.0);
if (m3.progress_percent !== 100.0 || m3.eta_seconds !== 0.0) {
  throw new Error(`m3 boundary failed: ${JSON.stringify(m3)}`);
}

console.log("PASS: All 12 DownloadStore TypeScript assertions verified successfully.");
