"""Split timestamped captions into short shadowing segments.

Each segment is about 1–3 sentences and roughly 5–15 seconds. Boundaries prefer
sentence endings. A single long sentence is split on clauses, then on time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

MIN_SEGMENT_SECONDS = 5.0
MAX_SEGMENT_SECONDS = 15.0
MAX_SENTENCES = 3
# Silence longer than this starts a new segment so playback is not mostly pause.
MAX_INTERNAL_GAP_SECONDS = 1.5

_SOUND_BRACKETS = re.compile(
    r"\[(?:music|applause|laughter|laughs|crowd|cheering|cheer|silence|noise|"
    r"inaudible|beat|singing|song|sfx|sound)[^\]]*\]",
    re.IGNORECASE,
)
_SOUND_PARENS = re.compile(
    r"\((?:music|applause|laughter|laughs|crowd|cheering|cheer|silence|noise|"
    r"inaudible|beat|singing|song|sfx|sound)[^)]*\)",
    re.IGNORECASE,
)
_TAGS = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

_ABBREVIATIONS = {
    "mr.",
    "mrs.",
    "ms.",
    "miss.",
    "dr.",
    "prof.",
    "sr.",
    "jr.",
    "st.",
    "vs.",
    "etc.",
    "eg.",
    "e.g.",
    "ie.",
    "i.e.",
    "a.m.",
    "p.m.",
    "am.",
    "pm.",
    "vol.",
    "fig.",
    "inc.",
    "ltd.",
    "co.",
    "gen.",
    "col.",
    "sgt.",
    "capt.",
    "lt.",
    "rev.",
    "hon.",
    "approx.",
    "dept.",
    "ph.d.",
    "m.d.",
    "b.a.",
    "m.a.",
    "d.c.",
    "u.s.",
    "u.k.",
    "u.s.a.",
}
_INITIALISM = re.compile(r"^(?:[A-Za-z]\.){2,}$")
_SINGLE_INITIAL = re.compile(r"^[A-Za-z]\.$")
_EDGE_PUNCT = "\"'“”‘’「」『』()[]{}"


@dataclass(frozen=True)
class Cue:
    text: str
    start: float
    duration: float


@dataclass(frozen=True)
class SegmentDraft:
    text: str
    start_time: float
    end_time: float
    sentence_count: int

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class TimedWord:
    text: str
    start: float
    end: float


def segment_transcript(cues: list[Cue]) -> list[SegmentDraft]:
    words = _cues_to_words(cues)
    if not words:
        return []
    sentences = _words_to_sentences(words)
    pieces: list[list[TimedWord]] = []
    for sentence in sentences:
        pieces.extend(_split_long_sentence(sentence))
    drafts = _pack_pieces(pieces)
    return _merge_short_segments(drafts)


def _clean_text(text: str) -> str:
    cleaned = unescape(text).replace("\n", " ").replace(">>", " ")
    cleaned = _TAGS.sub(" ", cleaned)
    cleaned = _SOUND_BRACKETS.sub(" ", cleaned)
    cleaned = _SOUND_PARENS.sub(" ", cleaned)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    if not re.search(r"[A-Za-z0-9]", cleaned):
        return ""
    return cleaned


def _cues_to_words(cues: list[Cue]) -> list[TimedWord]:
    prepared: list[tuple[str, float, float]] = []
    for cue in sorted(cues, key=lambda item: (item.start, item.duration)):
        text = _clean_text(cue.text)
        if text:
            prepared.append((text, float(cue.start), float(cue.duration)))

    words: list[TimedWord] = []
    previous_end: float | None = None
    for index, (text, cue_start, cue_duration) in enumerate(prepared):
        start = cue_start
        if previous_end is not None and start < previous_end:
            start = previous_end
        end = start + max(cue_duration, 0.05)
        if index + 1 < len(prepared):
            next_start = prepared[index + 1][1]
            if next_start > start:
                end = min(end, next_start)
        if end <= start:
            end = start + 0.05
        parts = text.split(" ")
        weights = [max(len(part), 1) for part in parts]
        total = sum(weights)
        span = end - start
        cursor = start
        for part, weight in zip(parts, weights, strict=True):
            word_end = cursor + span * (weight / total)
            words.append(TimedWord(part, cursor, word_end))
            cursor = word_end
        words[-1].end = end
        previous_end = end
    return words


def _boundary_token(token: str) -> str:
    return token.strip().strip(_EDGE_PUNCT)


def _is_sentence_end(token: str, next_token: str | None) -> bool:
    core = _boundary_token(token)
    if not core:
        return False
    if core.endswith(("!", "?")):
        return True
    if core.endswith("..."):
        return True
    if not core.endswith("."):
        return False
    lowered = core.lower()
    if lowered in _ABBREVIATIONS:
        return False
    if _INITIALISM.match(core) or _SINGLE_INITIAL.match(core):
        return False
    body = core[:-1]
    if body.isdigit() and next_token and _boundary_token(next_token)[:1].isdigit():
        return False
    return True


def _is_clause_end(token: str) -> bool:
    core = _boundary_token(token)
    return core.endswith((",", ";", ":")) or core in {"—", "–", "-"}


def _words_to_sentences(words: list[TimedWord]) -> list[list[TimedWord]]:
    sentences: list[list[TimedWord]] = []
    buffer: list[TimedWord] = []
    for index, word in enumerate(words):
        buffer.append(word)
        next_token = words[index + 1].text if index + 1 < len(words) else None
        if _is_sentence_end(word.text, next_token) or index == len(words) - 1:
            sentences.append(buffer)
            buffer = []
    return sentences


def _split_clauses(words: list[TimedWord]) -> list[list[TimedWord]]:
    clauses: list[list[TimedWord]] = []
    buffer: list[TimedWord] = []
    for word in words:
        buffer.append(word)
        if _is_clause_end(word.text):
            clauses.append(buffer)
            buffer = []
    if buffer:
        clauses.append(buffer)
    return clauses


def _split_words_by_time(words: list[TimedWord]) -> list[list[TimedWord]]:
    chunks: list[list[TimedWord]] = []
    buffer: list[TimedWord] = []
    for word in words:
        if not buffer:
            buffer = [word]
            continue
        if word.end - buffer[0].start <= MAX_SEGMENT_SECONDS:
            buffer.append(word)
            continue
        chunks.append(buffer)
        buffer = [word]
    if buffer:
        chunks.append(buffer)
    return chunks


def _pack_word_groups(groups: list[list[TimedWord]]) -> list[list[TimedWord]]:
    packed: list[list[TimedWord]] = []
    buffer: list[TimedWord] = []
    for group in groups:
        if not buffer:
            buffer = list(group)
            continue
        combined = buffer + group
        if combined[-1].end - combined[0].start <= MAX_SEGMENT_SECONDS:
            buffer = combined
            continue
        packed.append(buffer)
        buffer = list(group)
    if buffer:
        packed.append(buffer)
    return packed


def _split_long_sentence(words: list[TimedWord]) -> list[list[TimedWord]]:
    duration = words[-1].end - words[0].start
    if duration <= MAX_SEGMENT_SECONDS:
        return [words]
    clauses = _split_clauses(words)
    if len(clauses) == 1:
        return _split_words_by_time(words)
    pieces: list[list[TimedWord]] = []
    for group in _pack_word_groups(clauses):
        if group[-1].end - group[0].start > MAX_SEGMENT_SECONDS:
            pieces.extend(_split_words_by_time(group))
        else:
            pieces.append(group)
    return pieces


def _piece_to_draft(words: list[TimedWord], sentence_count: int) -> SegmentDraft:
    text = _WHITESPACE.sub(" ", " ".join(word.text for word in words)).strip()
    start = words[0].start
    end = words[-1].end
    if end <= start:
        end = start + 0.05
    return SegmentDraft(text=text, start_time=_round_time(start), end_time=_round_time(end), sentence_count=sentence_count)


def _round_time(value: float) -> float:
    return round(float(value), 3)


def _pack_pieces(pieces: list[list[TimedWord]]) -> list[SegmentDraft]:
    segments: list[SegmentDraft] = []
    buffer: list[list[TimedWord]] = []

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        words = [word for piece in buffer for word in piece]
        draft = _piece_to_draft(words, sentence_count=len(buffer))
        if draft.text:
            segments.append(draft)
        buffer = []

    for piece in pieces:
        if not piece:
            continue
        if not buffer:
            buffer = [piece]
            continue
        gap = piece[0].start - buffer[-1][-1].end
        combined_duration = piece[-1].end - buffer[0][0].start
        over_limits = (
            gap > MAX_INTERNAL_GAP_SECONDS
            or len(buffer) >= MAX_SENTENCES
            or combined_duration > MAX_SEGMENT_SECONDS
        )
        if over_limits:
            flush()
            buffer = [piece]
            continue
        buffer.append(piece)
    flush()
    return segments


def _can_merge(left: SegmentDraft, right: SegmentDraft) -> bool:
    if left.duration >= MIN_SEGMENT_SECONDS and right.duration >= MIN_SEGMENT_SECONDS:
        return False
    if right.start_time - left.end_time > MAX_INTERNAL_GAP_SECONDS:
        return False
    if left.sentence_count + right.sentence_count > MAX_SENTENCES:
        return False
    if right.end_time - left.start_time > MAX_SEGMENT_SECONDS:
        return False
    return True


def _merge(left: SegmentDraft, right: SegmentDraft) -> SegmentDraft:
    text = _WHITESPACE.sub(" ", f"{left.text} {right.text}").strip()
    return SegmentDraft(
        text=text,
        start_time=left.start_time,
        end_time=right.end_time,
        sentence_count=left.sentence_count + right.sentence_count,
    )


def _merge_short_segments(segments: list[SegmentDraft]) -> list[SegmentDraft]:
    merged = list(segments)
    changed = True
    while changed:
        changed = False
        for index, segment in enumerate(merged):
            if segment.duration >= MIN_SEGMENT_SECONDS:
                continue
            if index + 1 < len(merged) and _can_merge(segment, merged[index + 1]):
                merged[index] = _merge(segment, merged[index + 1])
                del merged[index + 1]
                changed = True
                break
            if index > 0 and _can_merge(merged[index - 1], segment):
                merged[index - 1] = _merge(merged[index - 1], segment)
                del merged[index]
                changed = True
                break
    return merged
