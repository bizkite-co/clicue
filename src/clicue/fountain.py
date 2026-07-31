import re

HEADER_KEYWORDS = {"title:", "author:", "authors:", "draft date:", "date:", "contact:", "copyright:", "notes:"}

class ParsedScript:
    def __init__(self, words: list[str], cues: list[str], para_starts: list[bool], styles: list[str] = None):
        self.words = words
        self.cues = cues
        self.para_starts = para_starts
        self.styles = styles if styles is not None else [""] * len(words)

    def __len__(self):
        return len(self.words)

def is_header_line(line: str) -> bool:
    low = line.strip().lower()
    return any(low.startswith(k) for k in HEADER_KEYWORDS)

def is_scene_heading(line: str) -> bool:
    stripped = line.strip()
    if re.match(r"^(INT\.|EXT\.|EST\.|INT\./EXT\.|EXT\./INT\.|\.)", stripped, re.IGNORECASE):
        return True
    return False

def is_character_name(line: str) -> bool:
    stripped = line.strip()
    if stripped.isupper() and 0 < len(stripped) < 30 and not is_scene_heading(stripped):
        return True
    return False

def process_word_emphasis(raw_word: str, in_italic: bool, in_bold: bool, in_code: bool) -> tuple[str, str, bool, bool, bool]:
    """
    Parses single-word or multi-word Fountain/Markdown emphasis delimiters (*word*, _word_, **bold**, `code`).
    Returns (clean_word, style_string, next_in_italic, next_in_bold, next_in_code).
    """
    word = raw_word
    
    # Check starting backtick code delimiter `
    starts_code = word.startswith("`")
    if starts_code:
        in_code = True
        word = word[1:]

    # Check starting delimiters (*, _, **, __, ***, ___)
    starts_triple = word.startswith("***") or word.startswith("___")
    starts_double = (word.startswith("**") or word.startswith("__")) and not starts_triple
    starts_single = (word.startswith("*") or word.startswith("_")) and not starts_double and not starts_triple

    if starts_triple:
        in_italic = True
        in_bold = True
        word = word[3:]
    elif starts_double:
        in_bold = True
        word = word[2:]
    elif starts_single:
        in_italic = True
        word = word[1:]

    ends_triple = False
    ends_double = False
    ends_single = False
    ends_code = False

    # Check ending delimiters (` or *, _, **, __, ***, ___) before optional trailing punctuation
    m_end = re.match(r"^(.*?)([\*\_\`]+)([^\w\*\_\`]*)$", word)
    if m_end:
        core, end_delim, punc = m_end.groups()
        if "`" in end_delim:
            ends_code = True
            end_delim = end_delim.replace("`", "")
        
        if len(end_delim) >= 3:
            ends_triple = True
        elif len(end_delim) == 2:
            ends_double = True
        elif len(end_delim) == 1:
            ends_single = True
            
        word = f"{core}{punc}"

    style_parts = []
    if in_code:
        style_parts.append("cyan")
    if in_bold:
        style_parts.append("bold")
    if in_italic:
        style_parts.append("italic")
        
    style_str = " ".join(style_parts)

    if ends_code:
        in_code = False
    if ends_triple:
        in_italic = False
        in_bold = False
    elif ends_double:
        in_bold = False
    elif ends_single:
        in_italic = False

    return word, style_str, in_italic, in_bold, in_code

def parse_fountain(content: str) -> ParsedScript:
    """
    Parses Fountain or markdown script content.
    Extracts spoken dialogue words, emphasis styles (*italic*, _italic_, **bold**, `code`),
    active stage cues ([Screen Recording...]), and paragraph boundaries.
    """
    lines = content.splitlines()
    
    words = []
    cues = []
    para_starts = []
    styles = []

    current_cue = ""
    in_header = True
    next_is_para_start = True

    in_italic = False
    in_bold = False
    in_code = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            next_is_para_start = True
            in_italic = False
            in_bold = False
            in_code = False
            continue

        # Check for metadata header
        if in_header:
            if is_header_line(line):
                continue
            else:
                in_header = False

        # Check for stage direction / bracketed cues [Screen Recording: ...]
        bracket_cues = re.findall(r"\[(.*?)\]", line)
        if bracket_cues:
            raw_cue = bracket_cues[-1].strip()
            clean_cue = re.sub(r"^(Screen Recording|Visual|Audio|Note|Action):\s*", "", raw_cue, flags=re.IGNORECASE)
            current_cue = clean_cue

        if is_scene_heading(line):
            continue

        if is_character_name(line):
            continue

        # Clean spoken text by removing [...] and (...)
        line_clean = re.sub(r"\[.*?\]", "", line)
        line_clean = re.sub(r"\(.*?\)", "", line_clean).strip()

        if line_clean:
            line_words = line_clean.split()
            for i, raw_w in enumerate(line_words):
                clean_w, word_style, in_italic, in_bold, in_code = process_word_emphasis(raw_w, in_italic, in_bold, in_code)
                words.append(clean_w)
                styles.append(word_style)
                cues.append(current_cue)
                para_starts.append(next_is_para_start and (i == 0))
            
            next_is_para_start = False

    return ParsedScript(words=words, cues=cues, para_starts=para_starts, styles=styles)

def parse_fountain_words(content: str) -> list[str]:
    return parse_fountain(content).words
