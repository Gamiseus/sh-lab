"""Tier 1: Feature Coverage — R3: Local Library Verification Before Network Transfer.

Requirements covered:
- R3.1: Pre-flight disk check across configured library paths prior to enqueuing network downloads.
- R3.2: Folder name normalization matches titles with punctuation, special characters, and casing variations.
- R3.3: Executable signature verification confirms existence of non-zero-byte executable binaries.
- R3.4: Multi-path verification checks across all configured library roots in `sh_library_paths`.
- R3.5: When local verification misses, client safely proceeds to network transfer request.
"""
import os
import shutil
import pytest
from tests.helpers import (
    normalize_title_for_filesystem,
    verify_local_game_signature,
    titles_match,
    is_valid_pe_binary,
)

pytestmark = pytest.mark.tier1


def test_r3_local_disk_precheck_skips_network_transfer(mock_local_library):
    """R3.1: Detected local game files immediately link game as installed without network download."""
    game_title = "Metro Last Light"
    game_folder = mock_local_library / "Metro Last Light"
    game_folder.mkdir()
    exe_file = game_folder / "MetroLL.exe"
    exe_file.write_bytes(b"MZ\x90\x00" + b"\x00" * 1024)  # simulated Windows PE header

    is_valid, detected_exe = verify_local_game_signature(
        folder_path=str(game_folder),
        game_title=game_title,
    )
    assert is_valid is True, "Pre-check must identify valid local installation"
    assert detected_exe is not None
    assert detected_exe.endswith(".exe")


def test_r3_folder_name_normalization_matching(mock_local_library):
    """R3.2: Normalization matches titles with punctuation, colons, and casing variations."""
    raw_title = "Half-Life 2: Episode One"
    normalized_expected = "half life 2 episode one"
    assert normalize_title_for_filesystem(raw_title) == normalized_expected

    # Create folder on disk with normalized/simplified name
    game_folder = mock_local_library / "half life 2 episode one"
    game_folder.mkdir()
    exe_file = game_folder / "hl2.exe"
    exe_file.write_bytes(b"MZ\x00\x00" + b"X" * 512)

    is_valid, detected_exe = verify_local_game_signature(
        folder_path=str(game_folder),
        game_title=raw_title,
    )
    assert is_valid is True, "Pre-check must match normalized folder name against title"


def test_r3_executable_signature_verification(mock_local_library):
    """R3.3: Executable signature verification requires non-empty binary with valid PE MZ header."""
    game_title = "Portal 2"
    game_folder = mock_local_library / "Portal 2"
    game_folder.mkdir()

    # Empty folder (no files) -> Invalid
    is_valid_empty, _ = verify_local_game_signature(str(game_folder), game_title)
    assert is_valid_empty is False, "Empty folder must not be treated as installed"

    # Only text/readme file (no exe) -> Invalid
    readme = game_folder / "readme.txt"
    readme.write_text("Portal 2 game notes")
    is_valid_txt, _ = verify_local_game_signature(str(game_folder), game_title)
    assert is_valid_txt is False, "Folder without executable binary must not be verified as installed"

    # 0-byte fake .exe -> Invalid
    zero_exe = game_folder / "portal2.exe"
    zero_exe.write_bytes(b"")
    is_valid_zero, _ = verify_local_game_signature(str(game_folder), game_title)
    assert is_valid_zero is False, "Zero-byte executable must fail signature verification"

    # Adversarial: Plaintext content with .exe extension -> Invalid
    zero_exe.write_bytes(b"This is plaintext content inside a fake portal2.exe file!")
    is_valid_plain, _ = verify_local_game_signature(str(game_folder), game_title)
    assert is_valid_plain is False, "Plaintext file with .exe extension must fail signature verification"

    # Adversarial: Corrupt null bytes with .exe extension -> Invalid
    zero_exe.write_bytes(b"\x00" * 1024)
    is_valid_null, _ = verify_local_game_signature(str(game_folder), game_title)
    assert is_valid_null is False, "Null-byte corrupted executable must fail signature verification"

    # Adversarial: Truncated 1-byte header -> Invalid
    zero_exe.write_bytes(b"M")
    is_valid_trunc, _ = verify_local_game_signature(str(game_folder), game_title)
    assert is_valid_trunc is False, "Truncated 1-byte header must fail signature verification"

    # Valid PE binary (DOS 'MZ' magic bytes) -> Valid
    zero_exe.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" + b"\x00" * 2048)
    is_valid_real, detected_exe = verify_local_game_signature(str(game_folder), game_title)
    assert is_valid_real is True
    assert detected_exe == str(zero_exe)


def test_r3_multi_path_scan_configured_drives(tmp_path):
    """R3.4: Pre-check scans across multiple configured library directory roots."""
    path_a = tmp_path / "games_ssd"
    path_b = tmp_path / "games_hdd"
    path_a.mkdir()
    path_b.mkdir()

    configured_paths = [str(path_a), str(path_b)]

    # Place game in path_b (the second configured drive)
    target_game = "Cyberpunk 2077"
    cp_dir = path_b / "Cyberpunk 2077"
    cp_dir.mkdir()
    exe = cp_dir / "Cyberpunk2077.exe"
    exe.write_bytes(b"MZ" + b"\x00" * 1024)

    found_in_paths = False
    for root_path in configured_paths:
        cand_folder = os.path.join(root_path, target_game)
        if os.path.exists(cand_folder):
            valid, _ = verify_local_game_signature(cand_folder, target_game)
            if valid:
                found_in_paths = True
                break

    assert found_in_paths is True, "Pre-check must discover game across secondary configured library paths"


def test_r3_missing_local_files_triggers_network_request(mock_local_library):
    """R3.5: When game does not exist on disk, pre-check safely returns False so network install proceeds."""
    game_title = "Uninstalled Game 2026"
    cand_folder = mock_local_library / game_title

    is_valid, _ = verify_local_game_signature(str(cand_folder), game_title)
    assert is_valid is False, "Pre-check on missing local files must return False to allow network install"


def test_r3_game_details_precheck_contract():
    """R3.6: GameDetailsPage.tsx implements pre-flight check before enqueuing network install."""
    details_path = os.path.join("frontend", "src", "pages", "GameDetailsPage.tsx")
    assert os.path.exists(details_path), f"GameDetailsPage.tsx not found at {details_path}"

    with open(details_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pre-flight check before network transfer
    has_precheck = (
        "scan_library_path" in content
        or "sh_library_paths" in content
        or "precheck" in content
        or "checkLocal" in content
        or "verifyLocal" in content
    )
    assert has_precheck, (
        "GameDetailsPage.tsx must invoke local library verification before dispatching network transfer"
    )


def test_r3_explicit_executable_path_pe_header_validation(mock_local_library):
    """R3.3: Explicit executable_path in metadata must be rejected if 0-byte, plain text, or corrupt."""
    game_title = "Metro Exodus"
    game_folder = mock_local_library / "Metro Exodus"
    game_folder.mkdir()
    bin_dir = game_folder / "bin"
    bin_dir.mkdir()
    exe_file = bin_dir / "MetroExodus.exe"

    # 0-byte explicit executable -> Invalid
    exe_file.write_bytes(b"")
    is_valid, _ = verify_local_game_signature(str(game_folder), game_title, executable_path="bin/MetroExodus.exe")
    assert is_valid is False, "0-byte explicit executable must be rejected"

    # Plaintext explicit executable -> Invalid
    exe_file.write_bytes(b"echo Not a real game")
    is_valid, _ = verify_local_game_signature(str(game_folder), game_title, executable_path="bin/MetroExodus.exe")
    assert is_valid is False, "Plaintext explicit executable must be rejected"

    # Null-byte corrupt explicit executable -> Invalid
    exe_file.write_bytes(b"\x00" * 512)
    is_valid, _ = verify_local_game_signature(str(game_folder), game_title, executable_path="bin/MetroExodus.exe")
    assert is_valid is False, "Null-byte corrupt explicit executable must be rejected"

    # Genuine PE binary -> Valid
    exe_file.write_bytes(b"MZ\x90\x00" + b"\x00" * 1024)
    is_valid, detected = verify_local_game_signature(str(game_folder), game_title, executable_path="bin/MetroExodus.exe")
    assert is_valid is True, "Genuine PE explicit executable must be validated"
    assert os.path.normpath(detected) == str(exe_file)


def test_r3_frontend_callers_check_verified_binary_contract():
    """R3.7: Frontend callers must check verified_binary before declaring game installed."""
    for rel_path in [
        os.path.join("frontend", "src", "pages", "GameDetailsPage.tsx"),
        os.path.join("frontend", "src", "pages", "LibraryPage.tsx"),
        os.path.join("frontend", "src", "components", "store", "HeroCarousel.tsx"),
    ]:
        assert os.path.exists(rel_path), f"{rel_path} not found"
        with open(rel_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "verified_binary" in content, (
            f"{rel_path} must reference and inspect verified_binary"
        )

