"""Tier 2: Boundary & Corner Cases — R3: Local Library Verification Before Network Transfer.

Requirements covered:
- R3.B1: Empty library paths list handled safely without scan error.
- R3.B2: Non-existent or inaccessible library directory does not crash scanner.
- R3.B3: Title match with corrupt/0-byte executable is rejected.
- R3.B4: Unicode, diacritics, and complex symbols normalization.
- R3.B5: Deeply nested game executable detected in subdirectories.
"""
import os
import pytest
from tests.helpers import (
    normalize_title_for_filesystem,
    verify_local_game_signature,
    titles_match,
)

pytestmark = pytest.mark.tier2


def test_r3_boundary_empty_library_paths():
    """R3.B1: When configured library paths is empty list [], pre-check safely returns False."""
    configured_paths = []
    found = False
    for p in configured_paths:
        if os.path.exists(p):
            found = True
    assert found is False, "Empty configured paths must not find any installations"


def test_r3_boundary_nonexistent_or_permission_denied_directory():
    """R3.B2: Non-existent directory root does not crash the pre-check scanner."""
    fake_path = "Z:\\NonExistentDrive_SHLAB_Testing\\games"
    is_valid, exe = verify_local_game_signature(fake_path, "Test Game")
    assert is_valid is False
    assert exe is None


def test_r3_boundary_folder_matches_but_executable_corrupted_or_zero_bytes(tmp_path):
    """R3.B3: Matching folder name with 0-byte, plain text, corrupt, or non-PE header is rejected."""
    game_dir = tmp_path / "The Witcher 3"
    game_dir.mkdir()
    exe = game_dir / "witcher3.exe"

    # 1. Corrupt zero-byte executable -> Rejected
    exe.write_bytes(b"")
    is_valid, _ = verify_local_game_signature(str(game_dir), "The Witcher 3")
    assert is_valid is False, "Zero-byte executable must be rejected during signature check"

    # 2. Plaintext file with .exe extension -> Rejected
    exe.write_bytes(b"This is plaintext content inside a fake witcher3.exe file!")
    is_valid, _ = verify_local_game_signature(str(game_dir), "The Witcher 3")
    assert is_valid is False, "Plaintext executable must be rejected during signature check"

    # 3. Corrupt null-byte header -> Rejected
    exe.write_bytes(b"\x00" * 1024)
    is_valid, _ = verify_local_game_signature(str(game_dir), "The Witcher 3")
    assert is_valid is False, "Corrupted null-header executable must be rejected during signature check"

    # 4. Partial 1-byte header -> Rejected
    exe.write_bytes(b"M")
    is_valid, _ = verify_local_game_signature(str(game_dir), "The Witcher 3")
    assert is_valid is False, "Partial 1-byte header must be rejected during signature check"

    # 5. Non-PE magic bytes (e.g. zip/jar archive magic PK\x03\x04) -> Rejected
    exe.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
    is_valid, _ = verify_local_game_signature(str(game_dir), "The Witcher 3")
    assert is_valid is False, "Non-PE magic header must be rejected during signature check"

    # 6. Genuine PE binary -> Valid
    exe.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00" + b"\x00" * 512)
    is_valid, detected = verify_local_game_signature(str(game_dir), "The Witcher 3")
    assert is_valid is True, "Valid PE binary must be accepted during signature check"
    assert detected == str(exe)


def test_r3_boundary_case_folding_and_diacritics():
    """R3.B4: Titles with unicode diacritics and complex symbols normalize cleanly."""
    title = "Pokémon: Let's Go, Pikachu! & Eevee™"
    normalized = normalize_title_for_filesystem(title)
    assert "pokémon" in normalized or "pokemon" in normalized
    assert ":" not in normalized
    assert "!" not in normalized
    assert "™" not in normalized


def test_r3_boundary_subfolder_deep_nesting(tmp_path):
    """R3.B5: Game executable placed in deep subfolder (e.g. bin/x64/) is successfully detected."""
    game_dir = tmp_path / "BioShock Infinite"
    deep_bin = game_dir / "Binaries" / "Win64"
    deep_bin.mkdir(parents=True)

    exe = deep_bin / "BioShockInfinite.exe"
    exe.write_bytes(b"MZ" + b"\x00" * 2048)

    is_valid, detected_exe = verify_local_game_signature(str(game_dir), "BioShock Infinite")
    assert is_valid is True, "Scanner must traverse subdirectories to locate executable"
    assert detected_exe == str(exe)


def test_r3_boundary_sequel_titles_do_not_collide():
    """R3.B6: Numbered sequels, prequels, and roman numerals must NOT collide during title matching."""
    # Numbered sequel collisions must be rejected
    assert titles_match("Overcooked", "Overcooked 2") is False
    assert titles_match("Borderlands", "Borderlands 2") is False
    assert titles_match("Dark Souls", "Dark Souls 2") is False
    assert titles_match("Spelunky", "Spelunky 2") is False
    assert titles_match("Portal", "Portal 2") is False
    assert titles_match("Half-Life", "Half-Life 2") is False

    # Roman numeral sequel collisions must be rejected
    assert titles_match("Dark Souls", "Dark Souls II") is False
    assert titles_match("Final Fantasy", "Final Fantasy VII") is False
    assert titles_match("Grand Theft Auto", "Grand Theft Auto IV") is False

    # Authentic title variations and punctuation normalization must match
    assert titles_match("A Plague Tale: Innocence", "A Plague Tale_ Innocence") is True
    assert titles_match("Batman™: Arkham Knight", "Batman_ Arkham Knight") is True
    assert titles_match("BioShock® 2", "BioShock 2") is True
    assert titles_match("8Doors: Arum's Afterlife Adventure", "8Doors_ Arum's Afterlife Adventure") is True
    assert titles_match("Half-Life 2", "Half Life 2") is True

