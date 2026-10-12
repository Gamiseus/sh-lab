"""Authoritative specification models and helper logic for SH-LAB R1-R6 requirements.

Derived strictly from ORIGINAL_REQUEST.md (header ## 2026-10-12T11:25:36Z) and PROJECT.md.
"""
from typing import Dict, Any, Optional, Set, Tuple, List
from datetime import datetime, timezone, timedelta
import re
import os

# ==============================================================================
# R1: Storefront Rating Badges & Sentiment Hierarchy
# ==============================================================================

def evaluate_rating_badge_hierarchy(
    steam_percent: Optional[int],
    metacritic_score: Optional[int],
    igdb_rating: Optional[float],
) -> Dict[str, Any]:
    """Calculate the primary storefront rating badge according to the R1 hierarchy.

    Contract:
    1. Primary: Steam positive percentage (steam_review_percent) if present.
       Sentiment colors:
       - >=70%: positive sentiment (emerald/green/blue)
       - 40-69%: mixed sentiment (amber/yellow)
       - <40%: negative sentiment (red/rose)
    2. Fallback 1: Metacritic score (metacritic_score) if steam_review_percent is None.
    3. Fallback 2: IGDB rating (rating, rounded) if both Steam and Metacritic are None.
    4. Fallback 3: No badge rendered if all three are absent.
    """
    if steam_percent is not None:
        if steam_percent >= 70:
            sentiment = "positive"
            color_cue = "emerald"
        elif steam_percent >= 40:
            sentiment = "mixed"
            color_cue = "amber"
        else:
            sentiment = "negative"
            color_cue = "red"
        
        return {
            "has_badge": True,
            "badge_type": "steam",
            "value": steam_percent,
            "display_text": f"{steam_percent}% Positive",
            "short_text": f"{steam_percent}%",
            "sentiment": sentiment,
            "color_cue": color_cue,
        }

    if metacritic_score is not None:
        if metacritic_score >= 75:
            sentiment = "positive"
            color_cue = "emerald"
        elif metacritic_score >= 50:
            sentiment = "mixed"
            color_cue = "amber"
        else:
            sentiment = "negative"
            color_cue = "red"
            
        return {
            "has_badge": True,
            "badge_type": "metacritic",
            "value": metacritic_score,
            "display_text": f"{metacritic_score}",
            "short_text": f"{metacritic_score}",
            "sentiment": sentiment,
            "color_cue": color_cue,
        }

    if igdb_rating is not None:
        rounded_igdb = round(igdb_rating)
        return {
            "has_badge": True,
            "badge_type": "igdb",
            "value": rounded_igdb,
            "display_text": f"{rounded_igdb}",
            "short_text": f"{rounded_igdb}",
            "sentiment": "igdb",
            "color_cue": "yellow",
        }

    return {
        "has_badge": False,
        "badge_type": None,
        "value": None,
        "display_text": None,
        "short_text": None,
        "sentiment": None,
        "color_cue": None,
    }


# ==============================================================================
# R3: Local Library Verification & Normalization
# ==============================================================================

def normalize_title_for_filesystem(title: str) -> str:
    """Normalize a game title to match directory names across filesystems.
    
    Removes invalid characters (: * ? \" < > | / \\), punctuation, collapses whitespace,
    and strips leading/trailing spaces.
    """
    cleaned = re.sub(r'[:*?"<>|/\\_—–\-!,™®©]', ' ', title)
    collapsed = re.sub(r'\s+', ' ', cleaned).strip().lower()
    return collapsed


def titles_match(a: str, b: str) -> bool:
    """Check if two game titles match after normalization and sequel-aware heuristics.
    
    Rules:
    1. Exact match after filesystem punctuation normalization -> True.
    2. Exact match on alphanumeric fingerprint -> True.
    3. Prefix matching: Only if length >= 8 and the remaining suffix does NOT
       start with a digit ('0'..='9') or roman numeral ('ii', 'iii', etc.) representing a sequel.
    """
    norm_a = normalize_title_for_filesystem(a)
    norm_b = normalize_title_for_filesystem(b)
    if norm_a and norm_a == norm_b:
        return True

    fp_a = re.sub(r'[^a-zA-Z0-9]', '', a).lower()
    fp_b = re.sub(r'[^a-zA-Z0-9]', '', b).lower()
    if not fp_a or not fp_b:
        return False
    if fp_a == fp_b:
        return True

    if len(fp_a) >= 8 and len(fp_b) >= 8:
        shorter, longer = (fp_a, fp_b) if len(fp_a) <= len(fp_b) else (fp_b, fp_a)
        if longer.startswith(shorter):
            suffix = longer[len(shorter):]
            # Suffix starting with a digit indicates a numeric sequel (e.g. Overcooked 2)
            if suffix[0].isdigit():
                return False
            # Suffix starting with roman numerals indicates a sequel (e.g. Dark Souls II)
            roman_numerals = ("ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x")
            if suffix in ("i",) or any(suffix.startswith(r) for r in roman_numerals):
                return False
            return True

    return False


def is_valid_pe_binary(file_path: str) -> bool:
    """Validate executable binary signature via magic header bytes.
    
    Checks:
    - Windows PE DOS header: starts with b"MZ" (0x4D, 0x5A)
    - Linux ELF binary: starts with b"\x7fELF" (0x7F, 0x45, 0x4C, 0x46)
    - Scripts (.bat, .cmd, .sh): valid if file size > 0
    
    Rejects:
    - 0-byte files
    - Plaintext files with .exe extension (lacking MZ header)
    - Corrupt / null-byte headers (e.g. 0x00 0x00 ...)
    - Non-existent files
    """
    if not os.path.isfile(file_path):
        return False
    try:
        with open(file_path, "rb") as f:
            header = f.read(64)
        if len(header) == 0:
            return False
        # Windows PE DOS header starts with 'M', 'Z' (0x4D, 0x5A)
        if len(header) >= 2 and header.startswith(b"MZ"):
            return True
        # Linux ELF header starts with 0x7F, 'E', 'L', 'F'
        if len(header) >= 4 and header.startswith(b"\x7fELF"):
            return True
        # Scripts (.bat, .cmd, .sh) are valid if non-empty
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".bat", ".cmd", ".sh") and len(header) > 0:
            return True
        return False
    except OSError:
        return False


def verify_local_game_signature(
    folder_path: str,
    game_title: str,
    executable_path: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Verify whether a folder on disk represents a valid local installation.

    Checks:
    1. Folder exists and is a directory.
    2. Folder contains at least one executable with a valid binary signature
       (PE DOS 'MZ' header, Linux ELF header, or non-empty script) matching
       the executable_path or matching the normalized game title.
    Returns (is_valid, detected_executable_path).
    """
    if not os.path.isdir(folder_path):
        return False, None

    # If specific executable_path is provided in metadata, check that first
    if executable_path:
        cand = os.path.normpath(os.path.join(folder_path, executable_path))
        if is_valid_pe_binary(cand):
            return True, cand

    norm_title = normalize_title_for_filesystem(game_title)
    norm_title_compact = norm_title.replace(" ", "")

    found_exe = None
    for root, _, files in os.walk(folder_path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in (".exe", ".bat", ".cmd", ".sh"):
                full_f = os.path.join(root, f)
                try:
                    if is_valid_pe_binary(full_f):
                        stem = os.path.splitext(f)[0].lower()
                        stem_compact = stem.replace(" ", "").replace("_", "").replace("-", "")
                        # Matching rule: executable stem contains title stem or vice-versa
                        if stem_compact in norm_title_compact or norm_title_compact in stem_compact or len(files) == 1:
                            return True, full_f
                        if not found_exe:
                            found_exe = full_f
                except OSError:
                    continue

    if found_exe:
        return True, found_exe

    return False, None


# ==============================================================================
# R4: Downloads Queue Calculations & Range Streaming
# ==============================================================================

def calculate_download_metrics(
    transferred_bytes: int,
    total_bytes: int,
    elapsed_seconds: float,
) -> Dict[str, Any]:
    """Calculate download queue metrics: speed, progress percent, and ETA."""
    if total_bytes <= 0:
        pct = 0.0
    else:
        pct = min(100.0, (transferred_bytes / total_bytes) * 100.0)

    if elapsed_seconds <= 0 or transferred_bytes <= 0:
        speed_bps = 0.0
        eta_sec = None
    else:
        speed_bps = transferred_bytes / elapsed_seconds
        remaining_bytes = max(0, total_bytes - transferred_bytes)
        eta_sec = (remaining_bytes / speed_bps) if speed_bps > 0 else None

    speed_mbps = speed_bps / (1024 * 1024)

    return {
        "progress_percent": round(pct, 2),
        "speed_bytes_sec": speed_bps,
        "speed_mb_sec": round(speed_mbps, 2),
        "eta_seconds": round(eta_sec, 1) if eta_sec is not None else None,
    }

def parse_http_range_header(range_header: str, file_size: int) -> Tuple[int, int, int, bool]:
    """Parse HTTP Range header 'bytes=start-end'.
    
    Returns (start, end, content_length, is_satisfiable).
    """
    if not range_header.startswith("bytes="):
        return 0, file_size - 1, file_size, False

    spec = range_header[6:].strip()
    try:
        if "-" in spec:
            start_str, end_str = spec.split("-", 1)
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
        else:
            start = int(spec)
            end = file_size - 1
    except ValueError:
        return 0, 0, 0, False

    if start < 0 or end >= file_size or start > end:
        return start, end, 0, False

    return start, end, end - start + 1, True


# ==============================================================================
# R5: 7-Day Orphan Retention & Cache Cleanup
# ==============================================================================

ORPHAN_RETENTION_SECONDS = 7 * 24 * 3600  # 604,800 seconds (7 days)

def evaluate_orphan_retention_status(
    user_count: int,
    orphaned_at: Optional[datetime],
    reference_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Evaluate whether a cached server game is orphaned and eligible for purge.

    Rules:
    - If user_count > 0: not orphaned, should retain.
    - If user_count == 0 and orphaned_at is None: orphaned immediately, retention timer starts now.
    - If user_count == 0 and orphaned_at is set:
      - elapsed = reference_time - orphaned_at
      - If elapsed >= 7 days (604,800s): eligible for automated purge.
      - If elapsed < 7 days: retained within grace period.
    """
    now = reference_time or datetime.now(timezone.utc)
    if orphaned_at and orphaned_at.tzinfo is None:
        orphaned_at = orphaned_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if user_count > 0:
        return {
            "is_orphaned": False,
            "orphaned_at": None,
            "eligible_for_purge": False,
            "seconds_remaining": None,
        }

    if orphaned_at is None:
        return {
            "is_orphaned": True,
            "orphaned_at": now,
            "eligible_for_purge": False,
            "seconds_remaining": ORPHAN_RETENTION_SECONDS,
        }

    elapsed = (now - orphaned_at).total_seconds()
    if elapsed >= ORPHAN_RETENTION_SECONDS:
        return {
            "is_orphaned": True,
            "orphaned_at": orphaned_at,
            "eligible_for_purge": True,
            "seconds_remaining": 0,
        }

    return {
        "is_orphaned": True,
        "orphaned_at": orphaned_at,
        "eligible_for_purge": False,
        "seconds_remaining": round(ORPHAN_RETENTION_SECONDS - elapsed, 1),
    }


# ==============================================================================
# Legacy Helpers (retained for backward compatibility)
# ==============================================================================

def get_canonical_valve_sentiment(positive_percent: int, total_reviews: int) -> Dict[str, Any]:
    if total_reviews < 10:
        return {"score": 0, "desc": "No user reviews", "tier": "neutral"}
    if positive_percent >= 95 and total_reviews >= 500:
        return {"score": 9, "desc": "Overwhelmingly Positive", "tier": "positive"}
    if positive_percent >= 80:
        if total_reviews >= 50:
            return {"score": 8, "desc": "Very Positive", "tier": "positive"}
        return {"score": 7, "desc": "Positive", "tier": "positive"}
    if positive_percent >= 70:
        return {"score": 6, "desc": "Mostly Positive", "tier": "positive"}
    if positive_percent >= 40:
        return {"score": 5, "desc": "Mixed", "tier": "mixed"}
    if positive_percent >= 20:
        return {"score": 4, "desc": "Mostly Negative", "tier": "negative"}
    if total_reviews >= 500:
        return {"score": 1, "desc": "Overwhelmingly Negative", "tier": "negative"}
    if total_reviews >= 50:
        return {"score": 2, "desc": "Very Negative", "tier": "negative"}
    return {"score": 3, "desc": "Negative", "tier": "negative"}

def calculate_pricing_display(price_cents: Optional[int], discount_percent: Optional[int]) -> Dict[str, Any]:
    discount = discount_percent or 0
    if price_cents is None:
        return {"display": "N/A", "has_discount": False, "badge": None, "strikethrough": None, "final_cents": None, "is_free": False}
    if price_cents == 0:
        return {"display": "Free", "has_discount": False, "badge": None, "strikethrough": None, "final_cents": 0, "is_free": True}
    formatted_final = f"${price_cents / 100:.2f}"
    if discount > 0:
        original_cents = round(price_cents / (1 - discount / 100))
        formatted_original = f"${original_cents / 100:.2f}"
        return {"display": formatted_final, "has_discount": True, "badge": f"-{discount}%", "strikethrough": formatted_original, "final_cents": price_cents, "original_cents": original_cents, "is_free": False}
    return {"display": formatted_final, "has_discount": False, "badge": None, "strikethrough": None, "final_cents": price_cents, "is_free": False}
