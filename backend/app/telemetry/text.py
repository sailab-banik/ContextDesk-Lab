"""Small text measures shared by the cache stub, the memory scorer, and the
context builder."""

import re

# Roughly four characters per token for English prose. The project reports
# context size in tokens for comparability with LLM usage; this estimate is
# labeled as an estimate everywhere it surfaces.
CHARS_PER_TOKEN = 4

STOPWORDS = frozenset(
    """
    a an the and or but if is are was were be been being do does did doing
    have has had having i me my we our you your it its this that these those
    to of in on at for with about from as by so how what when where which who
    whom why can could should would will shall may might must not no yes
    again still just now then there here please help
    """.split()
)


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN) if text else 0


def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def overlap_score(query: str, candidate: str) -> float:
    """Lexical overlap coefficient between two pieces of text, 0.0-1.0.

    The overlap coefficient (intersection over the smaller set) rather than
    Jaccard: a short question compared against a long record should not be
    penalised for the record's extra words.

    This is a local, lexical approximation. It stands in for an embedding
    similarity the stubs cannot compute, and it is never presented as one — the
    components that use it report status STUB, or label the score as locally
    computed.
    """
    left, right = content_words(query), content_words(candidate)
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))
