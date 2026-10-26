"""Streaming sentence boundary splitter for piping tokens directly into TTS synthesis."""

import re
from typing import AsyncIterator, List


class SentenceSplitter:
    """Buffers streamed LLM tokens and yields complete sentences at natural punctuation marks."""

    # Punctuation marks that denote a spoken clause or sentence boundary
    PUNCTUATION_REGEX = re.compile(r'([.!?\n]+|\:\s+)')
    # Common abbreviations that should NOT cause a sentence split
    ABBREVIATIONS = {
        "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.",
        "e.g.", "i.e.", "vs.", "etc.", "approx.", "u.s.", "u.k."
    }

    def __init__(self, min_words: int = 3):
        self.min_words = min_words
        self._buffer = ""

    def process_token(self, token: str) -> List[str]:
        """Add a token to the buffer and return any newly completed sentences."""
        self._buffer += token
        sentences = []

        # Check for punctuation splits
        matches = list(self.PUNCTUATION_REGEX.finditer(self._buffer))
        if not matches:
            return sentences

        last_end = 0
        for match in matches:
            split_idx = match.end()
            candidate = self._buffer[last_end:split_idx].strip()

            # Verify it is not an abbreviation or decimal number
            if self._is_abbreviation_or_decimal(candidate):
                continue

            # Check minimum word count to ensure meaningful speech chunk
            words = candidate.split()
            if len(words) >= self.min_words:
                sentences.append(candidate)
                last_end = split_idx

        if last_end > 0:
            self._buffer = self._buffer[last_end:].lstrip()

        return sentences

    def flush(self) -> List[str]:
        """Flush and return any remaining buffered text as the final sentence."""
        remaining = self._buffer.strip()
        self._buffer = ""
        if remaining:
            return [remaining]
        return []

    def _is_abbreviation_or_decimal(self, text: str) -> bool:
        """Check if trailing period is part of a number or common abbreviation."""
        lower = text.lower().strip()
        last_word = lower.split()[-1] if lower.split() else ""

        if last_word in self.ABBREVIATIONS:
            return True

        # Check if ends with decimal number e.g. "3." in "3.14"
        if re.search(r'\d+\.$', text):
            return True

        return False


async def stream_sentences(token_generator: AsyncIterator[str], min_words: int = 3) -> AsyncIterator[str]:
    """Async generator taking a stream of tokens and yielding complete sentences."""
    splitter = SentenceSplitter(min_words=min_words)
    async for token in token_generator:
        sentences = splitter.process_token(token)
        for sentence in sentences:
            yield sentence

    for sentence in splitter.flush():
        yield sentence
