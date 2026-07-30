import re

HEADER_KEYWORDS = {"title:", "author:", "authors:", "draft date:", "date:", "contact:", "copyright:", "notes:"}

class ParsedScript:
    def __init__(self, words: list[str], cues: list[str], para_starts: list[bool]):
        self.words = words
        self.cues = cues
        self.para_starts = para_starts

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

def parse_fountain(content: str) -> ParsedScript:
    """
    Parses Fountain or markdown script content.
    Extracts spoken dialogue words while tracking active stage cues ([Screen Recording...])
    and paragraph boundaries for teleprompter formatting.
    """
    lines = content.splitlines()
    
    words = []
    cues = []
    para_starts = []

    current_cue = ""
    in_header = True
    next_is_para_start = True

    for line in lines:
        stripped = line.strip()

        if not stripped:
            next_is_para_start = True
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
            # Strip redundant prefixes like "Screen Recording:", "Visual:", etc.
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
            for i, w in enumerate(line_words):
                words.append(w)
                cues.append(current_cue)
                # First word of a line/paragraph gets the paragraph start flag
                para_starts.append(next_is_para_start and (i == 0))
            
            next_is_para_start = False

    return ParsedScript(words=words, cues=cues, para_starts=para_starts)

def parse_fountain_words(content: str) -> list[str]:
    return parse_fountain(content).words
