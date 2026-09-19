"""Canonical separation of spoken paragraphs and square-bracket visual directions."""
from dataclasses import dataclass
import math
import re

WORDS_PER_SECOND = 2.4


@dataclass(frozen=True)
class ParsedScene:
    narration: str
    directions: tuple[str, ...]


@dataclass(frozen=True)
class ParsedScript:
    scenes: tuple[ParsedScene, ...]
    unclosed_direction: bool

    @property
    def spoken_text(self):
        return ' '.join(scene.narration for scene in self.scenes)

    def analysis(self):
        words = len(self.spoken_text.split())
        return {'word_count': words, 'estimated_seconds': math.floor(words / WORDS_PER_SECOND + .5),
                'unclosed_direction': self.unclosed_direction}


def parse_script(script: str) -> ParsedScript:
    # Scan brackets rather than using a regex: notes may nest or span paragraphs.
    # Escaped brackets are literal spoken text. An unfinished direction remains
    # excluded from the live estimate, and planning rejects it for review.
    paragraphs = []
    speech, notes, note = [], [], []
    depth = 0
    index = 0

    def paragraph():
        paragraphs.append((' '.join(''.join(speech).split()), tuple(notes)))
        speech.clear()
        notes.clear()

    while index < len(script):
        char = script[index]
        if char == '\\' and index + 1 < len(script) and script[index + 1] in '[]\\':
            (note if depth else speech).append(script[index + 1])
            index += 2
            continue
        if char == '[':
            if depth: note.append(char)
            else: speech.append(' ')
            depth += 1
        elif char == ']' and depth:
            depth -= 1
            if depth: note.append(char)
            else:
                text = ' '.join(''.join(note).split())
                if text: notes.append(text)
                note.clear()
                speech.append(' ')
        elif depth:
            note.append(char)
        elif char in '\r\n':
            # Blank lines separate spoken paragraphs, except inside a direction.
            match = re.match(r'\r?\n[ \t]*(?:\r?\n)+', script[index:])
            if match:
                paragraph()
                index += len(match.group())
                continue
            speech.append(' ')
        else:
            speech.append(char)
        index += 1
    paragraph()
    scenes, pending = [], []
    for narration, directions in paragraphs:
        pending.extend(directions)
        if narration:
            scenes.append(ParsedScene(narration, tuple(pending)))
            pending.clear()
    if pending and scenes:
        previous = scenes[-1]
        scenes[-1] = ParsedScene(previous.narration, previous.directions + tuple(pending))
    return ParsedScript(tuple(scenes), bool(depth))


def require_spoken_script(script: str) -> ParsedScript:
    parsed = parse_script(script)
    if parsed.unclosed_direction:
        raise ValueError('Close the unfinished [visual direction] before planning or using the draft')
    if not parsed.scenes:
        raise ValueError('Enter spoken narration in the script before planning')
    return parsed
