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
