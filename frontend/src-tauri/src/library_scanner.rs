use std::fs;
// std::path types used implicitly via entry.path()
use serde::{Deserialize, Serialize};
use reqwest::Client;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GameMetadata {
    pub id: i32,
    pub title: String,
    pub igdb_id: Option<i32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BackendGame {
    pub id: i32,
    pub title: String,
    pub igdb_id: Option<i32>,
    pub cover_url: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ScanResult {
    pub path: String,
    pub game: GameMetadata,
    pub status: String, // "Found", "Matched", "Conflict"
}

pub async fn scan_path(library_path: &str) -> Vec<ScanResult> {
    let mut results = Vec::new();
    let entries = match fs::read_dir(library_path) {
        Ok(e) => e,
        Err(_) => return results,
    };

    let client = Client::new();

    for entry in entries {
        if let Ok(entry) = entry {
            let path = entry.path();
            if path.is_dir() {
                // 1. Check for sh_meta.json
                let meta_path = path.join("sh_meta.json");
                if meta_path.exists() {
                     if let Ok(content) = fs::read_to_string(&meta_path) {
                         if let Ok(meta) = serde_json::from_str::<GameMetadata>(&content) {
                             // Sanity Check: Folder name vs Title
                             let _folder_name = path.file_name().unwrap().to_string_lossy();
                             // Simple check: does title start with folder name or vice versa? 
                             // Or just assume user is honest for now. 
                             // TODO: robust similarity check.
                             
                             results.push(ScanResult {
                                 path: path.to_string_lossy().to_string(),
                                 game: meta,
                                 status: "Found".to_string(),
                             });
                             continue;
                         }
                     }
                }

                // 2. If no meta, ask Backend
                let folder_name = path.file_name().unwrap().to_string_lossy();
                let url = format!("http://localhost:8000/api/v1/store/match?folder_name={}", folder_name);
                
                if let Ok(res) = client.get(&url).send().await {
                    println!("[Scanner] Backend Match Response: {}", res.status());
                    if res.status().is_success() {
                        if let Ok(backend_game) = res.json::<BackendGame>().await {
                            println!("[Scanner] Match Found: {} (ID: {})", backend_game.title, backend_game.id);
                             // Match found! Write meta
                            let meta = GameMetadata {
                                id: backend_game.id,
                                title: backend_game.title.clone(),
                                igdb_id: backend_game.igdb_id,
                            };
                            
                            if let Err(e) = fs::write(&meta_path, serde_json::to_string_pretty(&meta).unwrap()) {
                                println!("[Scanner] Failed to write meta: {}", e);
                            }
                            
                            results.push(ScanResult {
                                path: path.to_string_lossy().to_string(),
                                game: meta,
                                status: "Matched".to_string(),
                            });
                        } else {
                            println!("[Scanner] Failed to parse BackendGame JSON");
                        }
                    } else {
                         println!("[Scanner] Backend returned error: {}", res.status());
                    }
                } else {
                    println!("[Scanner] Failed to contact Backend at {}", url);
                }
            }
        }
    }
    
    results
}

pub async fn uninstall_game(path_str: String) -> Result<(), String> {
    let path = std::path::Path::new(&path_str);
    
    // Safety 1: Must exist
    if !path.exists() {
        return Err("Path does not exist".to_string());
    }

    // Safety 2: Must be a directory
    if !path.is_dir() {
         return Err("Path is not a directory".to_string());
    }

    // Safety 3: Must contain sh_meta.json (Proof it is a managed game)
    // This prevents deleting C:\Windows if passed by accident.
    let meta_path = path.join("sh_meta.json");
    if !meta_path.exists() {
        return Err("Safety Guard: Folder does not contain sh_meta.json. Refusing to delete.".to_string());
    }

    // Perform Deletion
    match fs::remove_dir_all(path) {
        Ok(_) => Ok(()),
        Err(e) => Err(format!("Failed to delete folder: {}", e)),
    }
}

pub async fn reset_metadata(path_str: String) -> Result<(), String> {
    let path = std::path::Path::new(&path_str);
    let meta_path = path.join("sh_meta.json");
    
    if meta_path.exists() {
        match fs::remove_file(meta_path) {
            Ok(_) => Ok(()),
            Err(e) => Err(format!("Failed to delete meta file: {}", e)),
        }
    } else {
        Ok(()) // Already gone
    }
}
