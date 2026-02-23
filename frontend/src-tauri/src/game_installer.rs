use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use reqwest::Client;
use tokio::io::AsyncWriteExt;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FileInfo {
    pub path: String,
    pub size: i64,
    pub is_dir: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct InstallInfo {
    pub game_id: i32,
    pub title: String,
    pub total_size: i64,
    pub file_count: i32,
    pub files: Vec<FileInfo>,
    pub repo_path: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct InstallProgress {
    pub game_id: i32,
    pub title: String,
    pub current_file: String,
    pub files_completed: i32,
    pub total_files: i32,
    pub bytes_downloaded: i64,
    pub total_bytes: i64,
    pub status: String, // "preparing", "downloading", "complete", "error"
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ShMeta {
    pub id: i32,
    pub title: String,
    pub igdb_id: Option<i32>,
}

/// Prepare installation by fetching file list from backend
pub async fn prepare_install(backend_url: &str, game_id: i32) -> Result<InstallInfo, String> {
    let client = Client::new();
    let url = format!("{}/api/v1/library/install/{}/prepare", backend_url, game_id);
    
    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Failed to connect to server: {}", e))?;
    
    if !response.status().is_success() {
        return Err(format!("Server returned error: {}", response.status()));
    }
    
    let install_info: InstallInfo = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    Ok(install_info)
}

/// Install a game by downloading all files to the library path
pub async fn install_game<F>(
    backend_url: &str,
    game_id: i32,
    library_path: &str,
    progress_callback: F,
) -> Result<(), String>
where
    F: Fn(InstallProgress) + Send + 'static,
{
    // Get install info
    let install_info = prepare_install(backend_url, game_id).await?;
    
    // Create game folder in library
    let game_folder = Path::new(library_path).join(&install_info.title);
    fs::create_dir_all(&game_folder)
        .map_err(|e| format!("Failed to create game folder: {}", e))?;
    
    let client = Client::new();
    let mut bytes_downloaded: i64 = 0;
    let mut files_completed: i32 = 0;
    
    // Report starting
    progress_callback(InstallProgress {
        game_id,
        title: install_info.title.clone(),
        current_file: "Starting...".to_string(),
        files_completed: 0,
        total_files: install_info.file_count,
        bytes_downloaded: 0,
        total_bytes: install_info.total_size,
        status: "preparing".to_string(),
        error: None,
    });
    
    // Download each file
    for file_info in &install_info.files {
        let file_path = game_folder.join(&file_info.path);
        
        // Create parent directories if needed
        if let Some(parent) = file_path.parent() {
            fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create directory: {}", e))?;
        }
        
        // Report progress
        progress_callback(InstallProgress {
            game_id,
            title: install_info.title.clone(),
            current_file: file_info.path.clone(),
            files_completed,
            total_files: install_info.file_count,
            bytes_downloaded,
            total_bytes: install_info.total_size,
            status: "downloading".to_string(),
            error: None,
        });
        
        // Download file
        let url = format!(
            "{}/api/v1/library/download/{}/{}",
            backend_url, game_id, file_info.path
        );
        
        let response = client
            .get(&url)
            .send()
            .await
            .map_err(|e| format!("Failed to download {}: {}", file_info.path, e))?;
        
        if !response.status().is_success() {
            return Err(format!(
                "Failed to download {}: HTTP {}",
                file_info.path,
                response.status()
            ));
        }
        
        let bytes = response
            .bytes()
            .await
            .map_err(|e| format!("Failed to read {}: {}", file_info.path, e))?;
        
        // Write to file
        let mut file = tokio::fs::File::create(&file_path)
            .await
            .map_err(|e| format!("Failed to create {}: {}", file_info.path, e))?;
        
        file.write_all(&bytes)
            .await
            .map_err(|e| format!("Failed to write {}: {}", file_info.path, e))?;
        
        bytes_downloaded += file_info.size;
        files_completed += 1;
    }
    
    // Create sh_meta.json
    let sh_meta = ShMeta {
        id: game_id,
        title: install_info.title.clone(),
        igdb_id: None, // Would need to fetch from backend
    };
    
    let meta_path = game_folder.join("sh_meta.json");
    let meta_json = serde_json::to_string_pretty(&sh_meta)
        .map_err(|e| format!("Failed to serialize metadata: {}", e))?;
    
    fs::write(&meta_path, meta_json)
        .map_err(|e| format!("Failed to write sh_meta.json: {}", e))?;
    
    // Report completion
    progress_callback(InstallProgress {
        game_id,
        title: install_info.title.clone(),
        current_file: "Complete!".to_string(),
        files_completed: install_info.file_count,
        total_files: install_info.file_count,
        bytes_downloaded: install_info.total_size,
        total_bytes: install_info.total_size,
        status: "complete".to_string(),
        error: None,
    });
    
    Ok(())
}

/// Get the size of a game installation
pub async fn get_install_size(backend_url: &str, game_id: i32) -> Result<i64, String> {
    let install_info = prepare_install(backend_url, game_id).await?;
    Ok(install_info.total_size)
}
