use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::process::Command;
use std::sync::{Arc, Mutex};
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ShMeta {
    pub id: i32,
    pub title: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub igdb_id: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub executable_path: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub launch_args: Option<String>,
    #[serde(default)]
    pub total_playtime_minutes: i32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_played: Option<String>,
}

#[derive(Debug, Serialize, Clone)]
pub struct GameSession {
    pub game_id: i32,
    pub game_path: String,
    pub start_time: u64, // Unix timestamp
    pub is_running: bool,
}

#[derive(Debug, Serialize, Clone)]
pub struct LaunchResult {
    pub success: bool,
    pub game_id: i32,
    pub message: String,
    pub pid: Option<u32>,
}

#[derive(Debug, Serialize, Clone)]
pub struct PlaytimeUpdate {
    pub game_id: i32,
    pub session_minutes: i32,
    pub total_minutes: i32,
    pub last_played: String,
}

// Global state for tracking running games
lazy_static::lazy_static! {
    static ref RUNNING_GAMES: Arc<Mutex<HashMap<i32, GameSession>>> = Arc::new(Mutex::new(HashMap::new()));
}

/// Read sh_meta.json from a game folder
pub fn read_sh_meta(game_path: &str) -> Result<ShMeta, String> {
    let meta_path = Path::new(game_path).join("sh_meta.json");
    
    if !meta_path.exists() {
        return Err(format!("sh_meta.json not found in {}", game_path));
    }
    
    let content = fs::read_to_string(&meta_path)
        .map_err(|e| format!("Failed to read sh_meta.json: {}", e))?;
    
    serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse sh_meta.json: {}", e))
}

/// Write sh_meta.json back to game folder
pub fn write_sh_meta(game_path: &str, meta: &ShMeta) -> Result<(), String> {
    let meta_path = Path::new(game_path).join("sh_meta.json");
    
    let content = serde_json::to_string_pretty(&meta)
        .map_err(|e| format!("Failed to serialize metadata: {}", e))?;
    
    fs::write(&meta_path, content)
        .map_err(|e| format!("Failed to write sh_meta.json: {}", e))
}

/// Find the game executable in a game folder
pub fn find_executable(game_path: &str) -> Result<String, String> {
    let path = Path::new(game_path);
    
    // First check sh_meta.json for explicit executable path
    if let Ok(meta) = read_sh_meta(game_path) {
        if let Some(exe_path) = meta.executable_path {
            let full_exe = path.join(&exe_path);
            if full_exe.exists() {
                return Ok(full_exe.to_string_lossy().to_string());
            }
        }
    }
    
    // Auto-detect common executable patterns
    let exe_extensions = ["exe", "sh", "bat", "cmd"];
    let common_names = [
        "game", "start", "launch", "play", "run",
    ];
    
    // Search for exe files in root
    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let entry_path = entry.path();
            if entry_path.is_file() {
                if let Some(ext) = entry_path.extension() {
                    let ext_str = ext.to_string_lossy().to_lowercase();
                    if exe_extensions.contains(&ext_str.as_str()) {
                        // Prefer executables with common game-related names
                        if let Some(stem) = entry_path.file_stem() {
                            let stem_lower = stem.to_string_lossy().to_lowercase();
                            if common_names.iter().any(|n| stem_lower.contains(n)) {
                                return Ok(entry_path.to_string_lossy().to_string());
                            }
                        }
                    }
                }
            }
        }
        
        // If no common name found, return first exe
        if let Ok(entries) = fs::read_dir(path) {
            for entry in entries.flatten() {
                let entry_path = entry.path();
                if entry_path.is_file() {
                    if let Some(ext) = entry_path.extension() {
                        let ext_str = ext.to_string_lossy().to_lowercase();
                        if ext_str == "exe" {
                            return Ok(entry_path.to_string_lossy().to_string());
                        }
                    }
                }
            }
        }
    }
    
    Err("No executable found in game folder".to_string())
}

/// Launch a game
pub fn launch_game(game_path: &str, custom_args: Option<&str>) -> Result<LaunchResult, String> {
    // Read metadata
    let meta = read_sh_meta(game_path)?;
    
    // Find executable
    let executable = find_executable(game_path)?;
    
    // Build launch command
    let mut cmd = Command::new(&executable);
    
    // Set working directory to game folder
    cmd.current_dir(game_path);
    
    // Add launch arguments
    if let Some(args) = custom_args {
        for arg in args.split_whitespace() {
            cmd.arg(arg);
        }
    } else if let Some(args) = &meta.launch_args {
        for arg in args.split_whitespace() {
            cmd.arg(arg);
        }
    }
    
    // Spawn the game process
    let child = cmd.spawn()
        .map_err(|e| format!("Failed to launch game: {}", e))?;
    
    let pid = child.id();
    
    // Record session start
    let session = GameSession {
        game_id: meta.id,
        game_path: game_path.to_string(),
        start_time: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs(),
        is_running: true,
    };
    
    {
        let mut games = RUNNING_GAMES.lock().unwrap();
        games.insert(meta.id, session);
    }
    
    Ok(LaunchResult {
        success: true,
        game_id: meta.id,
        message: format!("Launched {} (PID: {})", meta.title, pid),
        pid: Some(pid),
    })
}

/// Check if a game is currently running
pub fn is_game_running(game_id: i32) -> bool {
    let games = RUNNING_GAMES.lock().unwrap();
    games.contains_key(&game_id)
}

/// Get all running games
pub fn get_running_games() -> Vec<GameSession> {
    let games = RUNNING_GAMES.lock().unwrap();
    games.values().cloned().collect()
}

/// Stop tracking a game session and return playtime update
pub fn stop_game_session(game_id: i32) -> Result<PlaytimeUpdate, String> {
    let session = {
        let mut games = RUNNING_GAMES.lock().unwrap();
        games.remove(&game_id)
            .ok_or_else(|| format!("Game {} is not running", game_id))?
    };
    
    // Calculate session duration
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    let session_seconds = now - session.start_time;
    let session_minutes = (session_seconds / 60) as i32;
    
    // Update sh_meta.json with new playtime
    let mut meta = read_sh_meta(&session.game_path)?;
    meta.total_playtime_minutes += session_minutes;
    meta.last_played = Some(chrono::Utc::now().to_rfc3339());
    write_sh_meta(&session.game_path, &meta)?;
    
    Ok(PlaytimeUpdate {
        game_id,
        session_minutes,
        total_minutes: meta.total_playtime_minutes,
        last_played: meta.last_played.unwrap_or_default(),
    })
}

/// Get playtime info from a game folder
pub fn get_playtime(game_path: &str) -> Result<(i32, Option<String>), String> {
    let meta = read_sh_meta(game_path)?;
    Ok((meta.total_playtime_minutes, meta.last_played))
}
