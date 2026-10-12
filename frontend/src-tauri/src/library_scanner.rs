use std::fs;
use std::io::Read;
use std::path::Path;
use serde::{Deserialize, Serialize};
use reqwest::Client;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GameMetadata {
    pub id: i32,
    pub title: String,
    pub igdb_id: Option<i32>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ShMeta {
    pub id: i32,
    pub title: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub igdb_id: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub steam_app_id: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub executable_path: Option<String>,
    #[serde(default)]
    pub total_playtime_minutes: i32,
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

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct LocalVerificationResult {
    pub found: bool,
    pub path: Option<String>,
    pub executable: Option<String>,
    pub match_method: Option<String>,
    pub verified_binary: bool,
}

pub fn normalize_title(s: &str) -> String {
    let cleaned: String = s
        .chars()
        .map(|c| match c {
            ':' | '*' | '?' | '"' | '<' | '>' | '|' | '/' | '\\' | '_' | '—' | '–' | '-' | '!' | ',' | '™' | '®' | '©' => ' ',
            other => other,
        })
        .collect();
    cleaned
        .split_whitespace()
        .collect::<Vec<&str>>()
        .join(" ")
        .to_lowercase()
}

pub fn alphanumeric_fingerprint(s: &str) -> String {
    s.chars()
        .filter(|c| c.is_alphanumeric())
        .flat_map(|c| c.to_lowercase())
        .collect()
}

fn is_roman_numeral(s: &str) -> bool {
    matches!(
        s,
        "i" | "ii" | "iii" | "iv" | "v" | "vi" | "vii" | "viii" | "ix" | "x" |
        "xi" | "xii" | "xiii" | "xiv" | "xv" | "xvi" | "xvii" | "xviii" | "xix" | "xx"
    )
}

fn is_sequel_token(token: &str) -> bool {
    if token.is_empty() {
        return false;
    }
    // Starts with a digit: e.g. "2", "3", "2nd", "3rd", "4th"
    if token.starts_with(|c: char| c.is_ascii_digit()) {
        return true;
    }
    // Roman numerals: "i", "ii", "iii", "iv", "v", etc.
    if is_roman_numeral(token) {
        return true;
    }
    // Specific sequel edition terms
    matches!(token, "sequel" | "prequel")
}

fn has_sequel_word(norm_a: &str, norm_b: &str) -> bool {
    let words_a: Vec<&str> = norm_a.split_whitespace().collect();
    let words_b: Vec<&str> = norm_b.split_whitespace().collect();
    let (shorter_words, longer_words) = if words_a.len() < words_b.len() {
        (&words_a, &words_b)
    } else {
        (&words_b, &words_a)
    };
    if shorter_words.is_empty() || longer_words.len() <= shorter_words.len() {
        return false;
    }
    // Check if longer_words starts with shorter_words
    if longer_words[..shorter_words.len()] == shorter_words[..] {
        let next_word = longer_words[shorter_words.len()];
        if is_sequel_token(next_word) {
            return true;
        }
    }
    false
}

fn is_sequel_fingerprint_remainder(remainder: &str) -> bool {
    if remainder.is_empty() {
        return false;
    }
    // Starts with a digit: e.g. "2", "2remastered"
    if remainder.starts_with(|c: char| c.is_ascii_digit()) {
        return true;
    }
    // Exact Roman numerals: "i", "ii", "iii", "iv", "v", etc.
    if is_roman_numeral(remainder) {
        return true;
    }
    // Remainder starts with unambiguous Roman numerals:
    // "ii" and "iii" do not begin any English words
    if remainder.starts_with("ii") || remainder.starts_with("iii") {
        return true;
    }
    // "iv" prefix except for "ivory" or "ivy"
    if remainder.starts_with("iv") && !remainder.starts_with("ivory") && !remainder.starts_with("ivy") {
        return true;
    }
    // "vii" and "viii" do not begin any English words
    if remainder.starts_with("vii") || remainder.starts_with("viii") {
        return true;
    }
    false
}

pub fn titles_match(a: &str, b: &str) -> bool {
    let norm_a = normalize_title(a);
    let norm_b = normalize_title(b);
    if !norm_a.is_empty() && norm_a == norm_b {
        return true;
    }
    let fp_a = alphanumeric_fingerprint(a);
    let fp_b = alphanumeric_fingerprint(b);
    if fp_a.is_empty() || fp_b.is_empty() {
        return false;
    }
    if fp_a == fp_b {
        return true;
    }

    // Check if word-level prefix indicates a sequel or numbered edition
    if has_sequel_word(&norm_a, &norm_b) {
        return false;
    }

    if fp_a.len() >= 8 && fp_b.len() >= 8 {
        let (shorter, longer) = if fp_a.len() < fp_b.len() {
            (&fp_a, &fp_b)
        } else {
            (&fp_b, &fp_a)
        };
        if longer.starts_with(shorter) {
            let remainder = &longer[shorter.len()..];
            if is_sequel_fingerprint_remainder(remainder) {
                return false;
            }
            return true;
        }
    }
    false
}

pub fn is_valid_pe_binary(file_path: &Path) -> bool {
    let mut file = match fs::File::open(file_path) {
        Ok(f) => f,
        Err(_) => return false,
    };

    let mut header = [0u8; 64];
    let bytes_read = match file.read(&mut header) {
        Ok(n) => n,
        Err(_) => return false,
    };

    if bytes_read == 0 {
        return false;
    }

    // Windows PE DOS header starts with 'M', 'Z' (0x4D, 0x5A)
    if bytes_read >= 2 && header[0] == 0x4D && header[1] == 0x5A {
        return true;
    }

    // Linux ELF header starts with 0x7F, 'E', 'L', 'F'
    if bytes_read >= 4 && header[0] == 0x7F && header[1] == b'E' && header[2] == b'L' && header[3] == b'F' {
        return true;
    }

    // Scripts (.bat, .cmd, .sh) are valid if non-empty
    if let Some(ext) = file_path.extension() {
        let ext_str = ext.to_string_lossy().to_lowercase();
        if ext_str == "bat" || ext_str == "cmd" || ext_str == "sh" {
            return bytes_read > 0;
        }
    }

    false
}

fn scan_subdirs_for_pe(root: &Path, current: &Path, depth: usize, max_depth: usize) -> Option<String> {
    if depth > max_depth {
        return None;
    }
    let entries = match fs::read_dir(current) {
        Ok(e) => e,
        Err(_) => return None,
    };

    let mut subdirs = Vec::new();
    let mut candidates = Vec::new();
    let priority_names = ["game", "launch", "start", "play", "run"];

    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_file() {
            if let Some(ext) = path.extension() {
                let ext_str = ext.to_string_lossy().to_lowercase();
                if ext_str == "exe" || ext_str == "bat" || ext_str == "cmd" || ext_str == "sh" {
                    if is_valid_pe_binary(&path) {
                        let rel = path.strip_prefix(root).unwrap_or(&path).to_string_lossy().to_string();
                        let stem = path.file_stem().unwrap_or_default().to_string_lossy().to_lowercase();
                        if priority_names.iter().any(|p| stem.contains(p)) {
                            return Some(rel);
                        }
                        candidates.push(rel);
                    }
                }
            }
        } else if path.is_dir() {
            let dir_name = path.file_name().unwrap_or_default().to_string_lossy().to_lowercase();
            if !dir_name.starts_with('.') && dir_name != "node_modules" {
                subdirs.push(path);
            }
        }
    }

    if let Some(first) = candidates.into_iter().next() {
        return Some(first);
    }

    for sub in subdirs {
        if let Some(found) = scan_subdirs_for_pe(root, &sub, depth + 1, max_depth) {
            return Some(found);
        }
    }

    None
}

pub fn find_and_validate_executable(
    game_dir: &Path,
    expected_exe: Option<&str>,
) -> Option<(String, bool)> {
    // 1. Check explicit expected_exe if provided (must be valid PE or non-empty script)
    if let Some(rel) = expected_exe {
        let full = game_dir.join(rel);
        if full.is_file() && is_valid_pe_binary(&full) {
            return Some((rel.to_string(), true));
        }
    }

    // 2. Scan root directory for executables (only accept is_pe == true)
    let exe_extensions = ["exe", "bat", "cmd", "sh"];
    let priority_names = ["game", "launch", "start", "play", "run"];

    if let Ok(entries) = fs::read_dir(game_dir) {
        let mut candidates = Vec::new();
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                if let Some(ext) = path.extension() {
                    let ext_str = ext.to_string_lossy().to_lowercase();
                    if exe_extensions.contains(&ext_str.as_str()) && is_valid_pe_binary(&path) {
                        let stem = path.file_stem().unwrap_or_default().to_string_lossy().to_lowercase();
                        let rel = path.file_name().unwrap().to_string_lossy().to_string();
                        if priority_names.iter().any(|p| stem.contains(p)) {
                            return Some((rel, true));
                        }
                        candidates.push(rel);
                    }
                }
            }
        }
        if let Some(first) = candidates.into_iter().next() {
            return Some((first, true));
        }
    }

    // 3. Scan subdirectories up to depth 3 (handles Binaries/Win64, Game/Binaries, etc.)
    if let Some(sub_rel) = scan_subdirs_for_pe(game_dir, game_dir, 1, 3) {
        return Some((sub_rel, true));
    }

    None
}

pub async fn verify_game_on_disk(
    library_paths: Vec<String>,
    game_id: i32,
    game_title: String,
    steam_app_id: Option<i32>,
    expected_exe: Option<String>,
) -> LocalVerificationResult {
    for lib_path_str in &library_paths {
        let lib_path = Path::new(lib_path_str);
        if !lib_path.is_dir() {
            continue;
        }

        let entries = match fs::read_dir(lib_path) {
            Ok(e) => e,
            Err(_) => continue,
        };

        for entry in entries.flatten() {
            let candidate_dir = entry.path();
            if !candidate_dir.is_dir() {
                continue;
            }

            let folder_name = candidate_dir.file_name().unwrap_or_default().to_string_lossy().to_string();

            // Step 1: Check existing sh_meta.json
            let meta_path = candidate_dir.join("sh_meta.json");
            let mut matched_method = None;

            if meta_path.exists() {
                if let Ok(content) = fs::read_to_string(&meta_path) {
                    if let Ok(meta) = serde_json::from_str::<ShMeta>(&content) {
                        if meta.id == game_id {
                            matched_method = Some("sh_meta_id".to_string());
                        } else if steam_app_id.is_some() && meta.steam_app_id == steam_app_id {
                            matched_method = Some("sh_meta_steam_id".to_string());
                        } else if titles_match(&meta.title, &game_title) {
                            matched_method = Some("sh_meta_title".to_string());
                        }
                    }
                }
            }

            // Step 2: Resilient directory name match
            if matched_method.is_none() && titles_match(&folder_name, &game_title) {
                matched_method = Some("normalized_name".to_string());
            }

            // Step 3: Validate binary presence & signature if candidate matched
            if let Some(method) = matched_method {
                if let Some((rel_exe, is_pe)) = find_and_validate_executable(&candidate_dir, expected_exe.as_deref()) {
                    if is_pe {
                        // Only update/write sh_meta.json when binary is verified valid
                        let updated_meta = ShMeta {
                            id: game_id,
                            title: game_title.clone(),
                            igdb_id: None,
                            steam_app_id,
                            executable_path: Some(rel_exe.clone()),
                            total_playtime_minutes: 0,
                        };
                        let _ = fs::write(&meta_path, serde_json::to_string_pretty(&updated_meta).unwrap_or_default());

                        return LocalVerificationResult {
                            found: true,
                            path: Some(candidate_dir.to_string_lossy().to_string()),
                            executable: Some(rel_exe),
                            match_method: Some(method),
                            verified_binary: true,
                        };
                    }
                }
            }
        }
    }

    LocalVerificationResult {
        found: false,
        path: None,
        executable: None,
        match_method: None,
        verified_binary: false,
    }
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
                    if res.status().is_success() {
                        if let Ok(backend_game) = res.json::<BackendGame>().await {
                            let meta = GameMetadata {
                                id: backend_game.id,
                                title: backend_game.title.clone(),
                                igdb_id: backend_game.igdb_id,
                            };
                            
                            let _ = fs::write(&meta_path, serde_json::to_string_pretty(&meta).unwrap());
                            
                            results.push(ScanResult {
                                path: path.to_string_lossy().to_string(),
                                game: meta,
                                status: "Matched".to_string(),
                            });
                        }
                    }
                }
            }
        }
    }
    
    results
}

pub async fn uninstall_game(path_str: String) -> Result<(), String> {
    let path = Path::new(&path_str);
    
    // Safety 1: Must exist
    if !path.exists() {
        return Err("Path does not exist".to_string());
    }

    // Safety 2: Must be a directory
    if !path.is_dir() {
        return Err("Path is not a directory".to_string());
    }

    // Safety 3: Must contain sh_meta.json (Proof it is a managed game)
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
    let path = Path::new(&path_str);
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_titles_match_normalization() {
        assert!(titles_match("A Plague Tale: Innocence", "A Plague Tale_ Innocence"));
        assert!(titles_match("8Doors: Arum's Afterlife Adventure", "8Doors_ Arum's Afterlife Adventure"));
        assert!(titles_match("Batman™: Arkham Knight", "Batman_ Arkham Knight"));
        assert!(titles_match("Half-Life 2", "Half Life 2"));
        assert!(!titles_match("Portal 2", "Half-Life 2"));
    }

    #[test]
    fn test_titles_match_sequel_collision_rejection() {
        // Numeric sequels must NEVER match base game
        assert!(!titles_match("Overcooked", "Overcooked 2"));
        assert!(!titles_match("Overcooked", "Overcooked2"));
        assert!(!titles_match("Borderlands", "Borderlands 2"));
        assert!(!titles_match("Borderlands", "Borderlands2"));
        assert!(!titles_match("Dark Souls", "Dark Souls 2"));
        assert!(!titles_match("Half-Life", "Half-Life 2"));
        assert!(!titles_match("Spelunky", "Spelunky 2"));

        // Roman numeral sequels must NEVER match base game
        assert!(!titles_match("Dark Souls", "Dark Souls II"));
        assert!(!titles_match("Dark Souls", "Dark Souls III"));
        assert!(!titles_match("Dark Souls II", "Dark Souls III"));
        assert!(!titles_match("Final Fantasy VII", "Final Fantasy VIII"));
        assert!(!titles_match("Grand Theft Auto", "Grand Theft Auto V"));
        assert!(!titles_match("Grand Theft Auto", "Grand Theft Auto IV"));
    }

    #[test]
    fn test_titles_match_editions_and_subtitles() {
        // Legitimate subtitle and edition additions should match
        assert!(titles_match("Batman™: Arkham Knight", "Batman_ Arkham Knight"));
        assert!(titles_match("BioShock® 2", "BioShock 2"));
        assert!(titles_match("The Witcher 3: Wild Hunt", "The Witcher 3"));
        assert!(titles_match("Cyberpunk 2077", "Cyberpunk 2077: Phantom Liberty"));
    }

    #[test]
    fn test_alphanumeric_fingerprint() {
        assert_eq!(alphanumeric_fingerprint("A Plague Tale: Innocence"), "aplaguetaleinnocence");
        assert_eq!(alphanumeric_fingerprint("A Plague Tale_ Innocence"), "aplaguetaleinnocence");
    }

    #[test]
    fn test_pe_binary_validation() {
        let temp_dir = std::env::temp_dir();
        let valid_exe = temp_dir.join("shlab_test_valid.exe");
        let invalid_exe = temp_dir.join("shlab_test_zero.exe");
        let text_exe = temp_dir.join("shlab_test_text.exe");

        let _ = fs::write(&valid_exe, b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x00\x00\x00");
        let _ = fs::write(&invalid_exe, b"");
        let _ = fs::write(&text_exe, b"This is a fake plaintext executable.");

        assert!(is_valid_pe_binary(&valid_exe));
        assert!(!is_valid_pe_binary(&invalid_exe));
        assert!(!is_valid_pe_binary(&text_exe));

        let _ = fs::remove_file(valid_exe);
        let _ = fs::remove_file(invalid_exe);
        let _ = fs::remove_file(text_exe);
    }

    #[tokio::test]
    async fn test_zero_byte_rejection_and_no_meta_written() {
        let temp_root = std::env::temp_dir().join(format!("shlab_test_verify_{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        let game_dir = temp_root.join("Overcooked");
        fs::create_dir_all(&game_dir).unwrap();

        // Put a zero-byte executable
        let zero_exe = game_dir.join("game.exe");
        fs::write(&zero_exe, b"").unwrap();

        let res = verify_game_on_disk(
            vec![temp_root.to_string_lossy().to_string()],
            1001,
            "Overcooked".to_string(),
            None,
            None,
        ).await;

        assert!(!res.found, "0-byte executable must NOT be marked found");
        assert!(!res.verified_binary, "0-byte executable must NOT be verified_binary");

        // Verify sh_meta.json was NOT created
        let meta_file = game_dir.join("sh_meta.json");
        assert!(!meta_file.exists(), "sh_meta.json must NEVER be written for 0-byte binaries");

        let _ = fs::remove_dir_all(&temp_root);
    }

    #[tokio::test]
    async fn test_genuine_pe_acceptance_and_meta_written() {
        let temp_root = std::env::temp_dir().join(format!("shlab_test_valid_verify_{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        let game_dir = temp_root.join("Genuine Game");
        fs::create_dir_all(&game_dir).unwrap();

        // Valid PE executable
        let valid_exe = game_dir.join("start.exe");
        let mut pe = vec![0x4Du8, 0x5Au8];
        pe.extend(vec![0u8; 128]);
        fs::write(&valid_exe, &pe).unwrap();

        let res = verify_game_on_disk(
            vec![temp_root.to_string_lossy().to_string()],
            2002,
            "Genuine Game".to_string(),
            None,
            None,
        ).await;

        assert!(res.found, "Genuine PE must be marked found");
        assert!(res.verified_binary, "Genuine PE must be marked verified_binary");
        assert_eq!(res.executable, Some("start.exe".to_string()));

        // Verify sh_meta.json WAS created
        let meta_file = game_dir.join("sh_meta.json");
        assert!(meta_file.exists(), "sh_meta.json must be written for valid binaries");

        let _ = fs::remove_dir_all(&temp_root);
    }
}
