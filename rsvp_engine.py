def get_orp_index(word: str) -> int:
    """
    Calculate the Optimal Recognition Point (ORP) index for a word.
    The ORP is the letter where the eye should focus to minimize eye movement.
    Based on standard RSVP approximations.
    """
    length = len(word)
    if length <= 1:
        return 0
    elif 2 <= length <= 5:
        return 1
    elif 6 <= length <= 9:
        return 2
    elif 10 <= length <= 13:
        return 3
    else:
        return 4

def tokenize_text(text: str) -> list[str]:
    """
    Splits text into words by whitespace.
    """
    # Replace newlines with spaces to treat them consistently as word separators
    text = text.replace('\n', ' ')
    # Filter out empty words from extra spaces
    words = [w for w in text.split(' ') if w.strip()]
    return words

def get_delay_multiplier(word: str) -> float:
    """
    Returns a delay multiplier. Sentence endings need a longer pause
    for better reading comprehension in RSVP.
    """
    if not word:
        return 1.0
        
    last_char = word[-1]
    if last_char in ['.', '!', '?']:
        return 2.5  # Pauses roughly 2.5x the base word time
    elif last_char in [',', ';', ':']:
        return 1.5  # Slight pause for clauses
    return 1.0

def process_word_for_display(word: str) -> tuple[str, str, str]:
    """
    Splits a word into (prefix, focus_character, suffix)
    based on the Optimal Recognition Point.
    """
    if not word:
        return "", "", ""
        
    idx = get_orp_index(word)
    # Ensure index isn't out of bounds (can happen with weird character encodings)
    idx = min(idx, len(word) - 1)
    
    prefix = word[:idx]
    focus_char = word[idx]
    suffix = word[idx+1:]
    
    return prefix, focus_char, suffix


# ---------------------------------------------------------------------------
# v2: Adaptive Timing & Intelligent Chunking
# ---------------------------------------------------------------------------

# Common short function words eligible for chunking
FUNCTION_WORDS = frozenset({
    "the", "a", "an", "to", "of", "in", "on", "at", "by", "is", "it",
    "and", "or", "but", "for", "as", "if", "so", "no", "not", "be",
    "do", "he", "she", "we", "my", "up", "go", "its", "his", "her",
    "our", "are", "was", "has", "had", "did", "can", "may", "all",
    "who", "how", "out", "own", "any", "too", "yet", "nor", "per",
})

# Maximum characters for a word to be chunk-eligible
_CHUNK_CHAR_LIMIT = 4
# Maximum words in a single chunk
_MAX_CHUNK_SIZE = 3


def compute_adaptive_timing(word: str, base_time_ms: int = 140,
                            length_factor_ms: int = 35,
                            is_sentence_start: bool = False) -> int:
    """
    Compute a natural display duration in milliseconds for a single word.

    The duration scales with word length, adds penalties for punctuation
    and proper nouns, then is clamped to [100, 550] ms.
    """
    if not word:
        return base_time_ms

    # Strip trailing punctuation for length calculation
    clean = word.rstrip(".,;:!?\"'\u201c\u201d\u2018\u2019\u2014\u2013-)([]{}…")
    length = max(len(clean), 1)

    ms = base_time_ms + length_factor_ms * length

    # Punctuation penalties
    if word and word[-1] in '.!?':
        ms += 100
    elif word and word[-1] in ',;:':
        ms += 60

    # Proper noun detection: capitalized word NOT at sentence start
    if (clean and clean[0].isupper() and not is_sentence_start
            and clean[0].isalpha() and len(clean) > 1):
        ms = int(ms * 1.15)  # +15% for names/places

    # Clamp
    return max(100, min(550, ms))


def _has_trailing_punctuation(word: str) -> bool:
    """Check if a word ends with phrase-ending punctuation."""
    return bool(word) and word[-1] in '.,;:!?'


def _is_chunk_eligible(word: str) -> bool:
    """A word is chunk-eligible if it's short and is a common function word."""
    clean = word.lower().rstrip(".,;:!?\"'""''—–-)([]{}…")
    return len(clean) <= _CHUNK_CHAR_LIMIT and clean in FUNCTION_WORDS


def chunk_words(words: list[str]) -> list[dict]:
    """
    Group a flat list of word strings into display chunks.

    Returns a list of chunk dicts, each containing:
        display        – the text to show on screen (words joined by space)
        words          – list of original word strings in the chunk
        word_count     – how many raw words the chunk spans
        display_time_ms – adaptive timing for the chunk (sum with 10% reduction for multi-word)
        delay_multiplier – legacy field for backward compat
    """
    chunks: list[dict] = []
    i = 0
    n = len(words)
    sentence_start = True  # first word is always a sentence start

    while i < n:
        w = words[i]

        # Try to build a multi-word chunk starting at i
        if _is_chunk_eligible(w) and not _has_trailing_punctuation(w):
            group = [w]
            j = i + 1
            while j < n and len(group) < _MAX_CHUNK_SIZE:
                nw = words[j]
                if _is_chunk_eligible(nw):
                    group.append(nw)
                    if _has_trailing_punctuation(nw):
                        j += 1
                        break  # punctuation ends the chunk
                    j += 1
                else:
                    break

            # Only actually chunk if we collected >1 word
            if len(group) > 1:
                total_ms = sum(
                    compute_adaptive_timing(gw, is_sentence_start=(idx == 0 and sentence_start))
                    for idx, gw in enumerate(group)
                )
                # 10 % reduction for multi-word flow
                total_ms = int(total_ms * 0.9)
                total_ms = max(100, min(700, total_ms))
                chunks.append({
                    "display": " ".join(group),
                    "words": group,
                    "word_count": len(group),
                    "display_time_ms": total_ms,
                    "delay_multiplier": get_delay_multiplier(group[-1]),
                })
                # Check if last word in group ends a sentence
                sentence_start = _has_trailing_punctuation(group[-1]) and group[-1][-1] in '.!?'
                i = j
                continue

        # Single-word chunk (either not eligible or only one word collected)
        chunks.append({
            "display": w,
            "words": [w],
            "word_count": 1,
            "display_time_ms": compute_adaptive_timing(w, is_sentence_start=sentence_start),
            "delay_multiplier": get_delay_multiplier(w),
        })
        # Track sentence boundaries
        sentence_start = _has_trailing_punctuation(w) and w[-1] in '.!?'
        i += 1

    return chunks
