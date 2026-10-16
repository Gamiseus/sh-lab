// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
mod library_scanner;
mod game_installer;
mod game_launcher;

use tauri::Emitter;

#[tauri::command]
fn open_folder(base_path: String, relative_path: String) -> Result<(), String> {
    use std::process::Command;
    use std::path::Path;

    let full_path = Path::new(&base_path).join(relative_path);
    
    // Check if path exists (security/safety)
    if !full_path.exists() {
        return Err(format!("Path does not exist: {:?}", full_path));
    }

    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(full_path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    #[cfg(not(target_os = "windows"))]
    {
        // Linux/Mac implementation (xdg-open or open)
        Command::new("xdg-open")
            .arg(full_path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }

    Ok(())
}

#[tauri::command]
async fn scan_library_path(path: String) -> Vec<library_scanner::ScanResult> {
    library_scanner::scan_path(&path).await
}

#[tauri::command]
async fn uninstall_game_command(path: String) -> Result<(), String> {
    library_scanner::uninstall_game(path).await
}

#[tauri::command]
async fn verify_local_game_command(
    library_paths: Vec<String>,
    game_id: i32,
    game_title: String,
    steam_app_id: Option<i32>,
    expected_exe: Option<String>,
) -> library_scanner::LocalVerificationResult {
    library_scanner::verify_game_on_disk(
        library_paths,
        game_id,
        game_title,
        steam_app_id,
        expected_exe,
    ).await
}

#[tauri::command]
async fn reset_metadata_command(path: String) -> Result<(), String> {
    library_scanner::reset_metadata(path).await
}

// ============================================================
// Install Commands
// ============================================================

#[tauri::command]
async fn prepare_install_command(
    backend_url: String,
    game_id: i32,
) -> Result<game_installer::InstallInfo, String> {
    game_installer::prepare_install(&backend_url, game_id).await
}

#[tauri::command]
async fn install_game_command(
    app: tauri::AppHandle,
    backend_url: String,
    game_id: i32,
    library_path: String,
) -> Result<(), String> {
    // Clone app handle for the callback
    let app_handle = app.clone();
    
    game_installer::install_game(
        &backend_url,
        game_id,
        &library_path,
        move |progress| {
            // Emit progress event to frontend
            let _ = app_handle.emit("install-progress", &progress);
        },
    )
    .await
}

#[tauri::command]
async fn get_install_size_command(
    backend_url: String,
    game_id: i32,
) -> Result<i64, String> {
    game_installer::get_install_size(&backend_url, game_id).await
}

#[tauri::command]
async fn save_game_file_command(
    game_dir: String,
    relative_path: String,
    data: Vec<u8>,
) -> Result<(), String> {
    use std::path::Path;
    let target_file = Path::new(&game_dir).join(&relative_path);
    if let Some(parent) = target_file.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    std::fs::write(&target_file, data).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
async fn finalize_game_installation_command(
    game_dir: String,
    game_id: i32,
    game_title: String,
) -> Result<(), String> {
    use std::path::Path;
    let target_dir = Path::new(&game_dir);
    std::fs::create_dir_all(target_dir).map_err(|e| e.to_string())?;
    
    let meta = serde_json::json!({
        "id": game_id,
        "title": game_title,
    });
    let meta_path = target_dir.join("sh_meta.json");
    let meta_json = serde_json::to_string_pretty(&meta).map_err(|e| e.to_string())?;
    std::fs::write(&meta_path, meta_json).map_err(|e| e.to_string())?;
    Ok(())
}

// ============================================================
// Game Launch Commands
// ============================================================

#[tauri::command]
fn launch_game_command(
    game_path: String,
    custom_args: Option<String>,
) -> Result<game_launcher::LaunchResult, String> {
    game_launcher::launch_game(&game_path, custom_args.as_deref())
}

#[tauri::command]
fn is_game_running_command(game_id: i32) -> bool {
    game_launcher::is_game_running(game_id)
}

#[tauri::command]
fn get_running_games_command() -> Vec<game_launcher::GameSession> {
    game_launcher::get_running_games()
}

#[tauri::command]
fn stop_game_session_command(game_id: i32) -> Result<game_launcher::PlaytimeUpdate, String> {
    game_launcher::stop_game_session(game_id)
}

#[tauri::command]
fn get_game_playtime_command(game_path: String) -> Result<(i32, Option<String>), String> {
    game_launcher::get_playtime(&game_path)
}

#[tauri::command]
fn find_game_executable_command(game_path: String) -> Result<String, String> {
    game_launcher::find_executable(&game_path)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            open_folder,
            scan_library_path,
            verify_local_game_command,
            uninstall_game_command,
            reset_metadata_command,
            // Install commands
            prepare_install_command,
            install_game_command,
            get_install_size_command,
            save_game_file_command,
            finalize_game_installation_command,
            // Launch commands
            launch_game_command,
            is_game_running_command,
            get_running_games_command,
            stop_game_session_command,
            get_game_playtime_command,
            find_game_executable_command
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
