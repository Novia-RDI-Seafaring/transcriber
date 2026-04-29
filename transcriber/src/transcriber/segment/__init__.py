"""Word-to-sentence segmentation."""

from transcriber.segment.sentences import group_words_into_segments, merge_short_segments

__all__ = ["group_words_into_segments", "merge_short_segments"]
