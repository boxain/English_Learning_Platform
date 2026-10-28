"""Shadowing segmentation rules."""

from app.services.segmenter import (
    MAX_SEGMENT_SECONDS,
    MAX_SENTENCES,
    Cue,
    segment_transcript,
)


def _text(cues: list[Cue]) -> str:
    return " ".join(segment.text for segment in segment_transcript(cues))


def test_groups_short_sentences_into_one_segment():
    segments = segment_transcript(
        [
            Cue("Hello there.", 0.0, 2.0),
            Cue("How are you?", 2.0, 2.0),
            Cue("I am fine.", 4.0, 2.0),
        ]
    )
    assert len(segments) == 1
    assert segments[0].text == "Hello there. How are you? I am fine."
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 6.0
    assert segments[0].sentence_count == 3


def test_keeps_multiple_sentences_inside_one_caption_cue():
    segments = segment_transcript([Cue("Hello. World. Again.", 0.0, 9.0)])
    assert len(segments) == 1
    assert segments[0].text == "Hello. World. Again."
    assert segments[0].sentence_count == 3


def test_splits_before_segment_exceeds_fifteen_seconds():
    segments = segment_transcript(
        [
            Cue("This sentence takes a while to say out loud.", 0.0, 8.0),
            Cue("This next sentence also takes quite a while.", 8.0, 8.0),
        ]
    )
    assert len(segments) == 2
    assert segments[0].end_time == 8.0
    assert segments[1].start_time == 8.0
    assert all(segment.duration <= MAX_SEGMENT_SECONDS for segment in segments)


def test_caps_a_segment_at_three_sentences():
    segments = segment_transcript(
        [
            Cue("One.", 0.0, 1.0),
            Cue("Two.", 1.0, 1.0),
            Cue("Three.", 2.0, 1.0),
            Cue("Four.", 3.0, 1.0),
        ]
    )
    assert [segment.sentence_count for segment in segments] == [3, 1]
    assert segments[0].text == "One. Two. Three."
    assert segments[1].text == "Four."


def test_does_not_split_abbreviations_or_decimals():
    segments = segment_transcript(
        [
            Cue("Dr. Smith went to the U.S. yesterday.", 0.0, 6.0),
            Cue("He met Mr. Jones at 3.14 exactly.", 6.0, 4.0),
        ]
    )
    assert len(segments) == 1
    assert segments[0].sentence_count == 2
    assert segments[0].text == "Dr. Smith went to the U.S. yesterday. He met Mr. Jones at 3.14 exactly."


def test_splits_ellipsis_as_a_sentence_boundary():
    segments = segment_transcript([Cue("Wait... Then go home.", 0.0, 6.0)])
    assert segments[0].sentence_count == 2
    assert segments[0].text == "Wait... Then go home."


def test_splits_a_long_sentence_on_clause_and_time():
    segments = segment_transcript(
        [
            Cue(
                "I walked to the store, bought some fresh bread, came back home, and sat down quietly for a while.",
                0.0,
                30.0,
            )
        ]
    )
    assert len(segments) >= 2
    assert all(segment.duration <= MAX_SEGMENT_SECONDS + 0.001 for segment in segments)
    assert segments[0].start_time == 0.0
    assert segments[-1].end_time == 30.0
    assert " ".join(segment.text for segment in segments) == (
        "I walked to the store, bought some fresh bread, came back home, and sat down quietly for a while."
    )


def test_splits_a_long_sentence_without_punctuation_by_time():
    words = " ".join(f"word{i}" for i in range(80)) + "."
    segments = segment_transcript([Cue(words, 0.0, 40.0)])
    assert len(segments) >= 3
    assert all(segment.duration <= MAX_SEGMENT_SECONDS + 0.001 for segment in segments)
    assert " ".join(segment.text for segment in segments) == words
    assert segments[0].start_time == 0.0
    assert abs(segments[-1].end_time - 40.0) < 0.02


def test_skips_non_speech_cues_without_clipping_nearby_speech():
    segments = segment_transcript(
        [
            Cue("Hello there.", 0.0, 5.0),
            Cue("[Music]", 4.0, 3.0),
            Cue("(Applause)", 7.0, 1.0),
            Cue("How are you today?", 8.0, 4.0),
        ]
    )
    assert segments[0].text == "Hello there."
    assert segments[0].start_time == 0.0
    assert segments[0].end_time == 5.0
    assert segments[-1].text == "How are you today?"
    assert "[Music]" not in _text(
        [Cue("Hello [Music] world.", 0.0, 6.0)]
    )
    assert segment_transcript([Cue("[Music]", 0.0, 4.0), Cue("(Laughter)", 4.0, 2.0)]) == []
    assert segment_transcript([Cue("♪ Hello there. ♪", 1.0, 6.0)])[0].text == "Hello there."
    assert segment_transcript([Cue("[♪♪♪]", 0.0, 3.0), Cue("Hello there.", 3.0, 6.0)])[0].text == "Hello there."


def test_starts_a_new_segment_after_a_long_pause():
    segments = segment_transcript(
        [
            Cue("Hello there friend.", 0.0, 2.0),
            Cue("Much later we continue talking here.", 10.0, 6.0),
        ]
    )
    assert len(segments) == 2
    assert segments[0].end_time == 2.0
    assert segments[1].start_time == 10.0


def test_mixed_monologue_stays_inside_shadowing_bounds():
    cues: list[Cue] = []
    clock = 0.0
    for index in range(30):
        if index % 7 == 0:
            text = (
                f"Sentence {index} keeps going, with a clause in the middle, "
                "and then it finally finishes."
            )
            duration = 12.0
        else:
            text = f"Sentence {index} is ready now."
            duration = 2.4
        cues.append(Cue(text, clock, duration))
        clock += duration + 0.2

    segments = segment_transcript(cues)
    assert len(segments) > 1
    assert any(segment.sentence_count > 1 for segment in segments)
    assert all(1 <= segment.sentence_count <= MAX_SENTENCES for segment in segments)
    assert all(segment.duration <= MAX_SEGMENT_SECONDS + 0.001 for segment in segments)
    for previous, current in zip(segments, segments[1:], strict=False):
        assert current.start_time >= previous.end_time - 0.001
    spoken = " ".join(cue.text for cue in cues)
    assert " ".join(segment.text for segment in segments) == spoken
