"""
BankSathi — Language Detection Module

Detects whether a banking query is in:
  - HINDI: Devanagari script
  - HINGLISH: Romanized Hindi mixed with English / Hindi banking terms
  - ENGLISH: Standard English query

Designed specifically for Indian banking queries with high explainability.
"""

import re
from typing import Dict, Any

# Devanagari Unicode character range: \u0900 - \u097F
DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")

# Common Hindi/Hinglish vocabulary tokens frequently seen in banking queries
HINGLISH_MARKERS = {
    # Banking & financial domain terms
    "khata", "khate", "paisa", "paise", "kheti", "kisan", "dukaan", "dukan",
    "bima", "byaj", "byaaj", "udhaar", "karz", "rin", "padhai", "shiksha",
    "saal", "mahina", "mahine", "beti", "ladki", "kamai", "rokda", "vyapar",
    "karobar", "suraksha", "budhapa", "vriddha", "nivesh", "bachat",

    # Pronouns & interrogatives
    "mera", "meri", "mere", "mujhe", "mujhko", "hum", "humare", "apna", "apni",
    "apne", "kya", "kaise", "kitna", "kitni", "kitne", "kab", "kahan", "kaun",
    "kisko", "kisme", "kisko",

    # Verbs & auxiliaries
    "chahiye", "hoga", "hogi", "hoge", "karna", "kare", "karo", "karein",
    "lena", "le", "dena", "de", "hai", "hain", "tha", "thi", "the", "lagta",
    "lagti", "padega", "padegi", "batao", "bataye", "batayein", "batado",
    "milta", "milega", "milegi", "nikla", "kat", "gaya", "gaye", "aaya",
    "aaye", "aayega", "phas", "gaye",

    # Prepositions, conjunctions & particles
    "ke", "ki", "ka", "ko", "se", "me", "mein", "par", "aur", "ya", "lekin",
    "agar", "bhi", "toh", "to", "wala", "wali", "wale",

    # Negation
    "nahi", "nahin", "na", "mat",
}


def detect_language(text: str) -> Dict[str, Any]:
    """
    Detect the language of a banking user query.

    Parameters
    ----------
    text : str
        The raw user input.

    Returns
    -------
    dict
        {
            "language": "ENGLISH" | "HINDI" | "HINGLISH",
            "confidence": float (0.0 to 1.0),
            "devanagari_ratio": float,
            "hinglish_markers_found": list[str]
        }
    """
    if not text or not text.strip():
        return {
            "language": "ENGLISH",
            "confidence": 1.0,
            "devanagari_ratio": 0.0,
            "hinglish_markers_found": [],
        }

    clean_text = text.strip()
    total_chars = len(clean_text)

    # 1. Check for Devanagari script (Pure Hindi)
    devanagari_chars = len(DEVANAGARI_REGEX.findall(clean_text))
    devanagari_ratio = devanagari_chars / total_chars if total_chars > 0 else 0.0

    if devanagari_ratio >= 0.25:
        return {
            "language": "HINDI",
            "confidence": round(min(1.0, devanagari_ratio + 0.3), 2),
            "devanagari_ratio": round(devanagari_ratio, 2),
            "hinglish_markers_found": [],
        }

    # 2. Check for Hinglish markers in romanized text
    # Normalize words to lower case and check word tokens
    words = re.findall(r"\b[a-zA-Z]+\b", clean_text.lower())
    total_words = len(words)

    if total_words == 0:
        # Numbers or symbols only
        return {
            "language": "ENGLISH",
            "confidence": 0.9,
            "devanagari_ratio": 0.0,
            "hinglish_markers_found": [],
        }

    found_markers = [w for w in words if w in HINGLISH_MARKERS]
    marker_ratio = len(found_markers) / total_words

    # If at least one strong marker exists in a short query, or > 15% words are markers
    if len(found_markers) >= 1 and (marker_ratio >= 0.15 or len(found_markers) >= 2):
        confidence = min(0.98, 0.60 + (marker_ratio * 0.40))
        return {
            "language": "HINGLISH",
            "confidence": round(confidence, 2),
            "devanagari_ratio": 0.0,
            "hinglish_markers_found": list(dict.fromkeys(found_markers)),
        }

    # If single marker in a short sentence (<= 4 words)
    if len(found_markers) == 1 and total_words <= 4:
        return {
            "language": "HINGLISH",
            "confidence": 0.75,
            "devanagari_ratio": 0.0,
            "hinglish_markers_found": found_markers,
        }

    # 3. Default to English
    return {
        "language": "ENGLISH",
        "confidence": 0.95,
        "devanagari_ratio": 0.0,
        "hinglish_markers_found": [],
    }
