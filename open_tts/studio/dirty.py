"""Which speaker blocks need rebuild after a line edit (no Qt)."""

from __future__ import annotations

from open_tts.video import merged_speaker_blocks


def block_index_for_line(
    line_id: int,
    segments: list[dict],
    audio_duration: float,
    dual_start: int,
    dual_end: int,
) -> int | None:
    """Return merged block index containing 1-based line_id, or None."""
    blocks = merged_speaker_blocks(
        segments, audio_duration, dual_start, dual_end
    )
    for i, block in enumerate(blocks):
        for ln in block["lines"]:
            if ln["id"] == line_id:
                return i
    return None


def dirty_block_indices_for_line(
    line_id: int,
    segments: list[dict],
    audio_duration: float,
    dual_start: int,
    dual_end: int,
    *,
    speaker_changed: bool = False,
    text_changed: bool = False,
    cue_changed: bool = False,
) -> set[int]:
    """
    Return 0-based speaker-block indices that must be re-rendered for this edit.

    Cue-only edits affect the block containing the line. Speaker changes can
    reshuffle merged blocks, so all blocks are marked dirty. Text changes mark
    the containing block (full audio/video pipeline may still rebuild everything).
    """
    blocks = merged_speaker_blocks(
        segments, audio_duration, dual_start, dual_end
    )
    if not blocks:
        return set()

    if speaker_changed:
        return set(range(len(blocks)))

    idx = block_index_for_line(
        line_id, segments, audio_duration, dual_start, dual_end
    )
    if idx is None:
        return set()

    dirty: set[int] = {idx}
    if text_changed or cue_changed:
        return dirty
    return dirty
