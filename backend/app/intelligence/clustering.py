import math
import re
from collections import Counter, defaultdict

_TOKEN = re.compile(r"[a-z]{3,}")
_BACKTICKED = re.compile(r"`[^`]*`")
_STOPWORDS = frozenset(
    "the and are for with that this was were not but can has have from into its use used "
    "when which will would should may might also than then them they their there here been "
    "being does did out any all only more most some such each other what who how why our "
    "your you per via too very one two threshold".split()
)


def normalize(text: str) -> tuple[str, ...]:
    """Lowercase, drop `identifiers`, numbers and stopwords, apply a tiny plural stemmer."""
    text = _BACKTICKED.sub(" ", text.lower())
    tokens: list[str] = []
    for token in _TOKEN.findall(text):
        if token in _STOPWORDS:
            continue
        if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return tuple(tokens)


def _vectors(docs: list[tuple[str, ...]]) -> list[dict[str, float]]:
    n = len(docs)
    df = Counter(term for doc in docs for term in set(doc))
    vectors = []
    for doc in docs:
        weights = {
            term: (1 + math.log(count)) * (math.log((1 + n) / (1 + df[term])) + 1)
            for term, count in Counter(doc).items()
        }
        norm = math.sqrt(sum(w * w for w in weights.values())) or 1.0
        vectors.append({term: w / norm for term, w in weights.items()})
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


def cluster_texts(texts: list[str], threshold: float = 0.5) -> list[list[int]]:
    """
    Groups similar texts (single-link clustering over TF-IDF cosine similarity).
    Returns clusters as lists of indices into `texts`, largest first.

    Identical normalized texts are merged BEFORE comparing, so the O(n^2) step
    only runs over distinct message templates (tens), not thousands of findings.
    Texts with no usable words stay as singletons.
    """
    unique: dict[tuple[str, ...], list[int]] = {}
    for index, text in enumerate(texts):
        unique.setdefault(normalize(text), []).append(index)

    keys = list(unique)
    vectors = _vectors(keys)
    parent = list(range(len(keys)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(keys)):
        if not keys[i]:
            continue
        for j in range(i + 1, len(keys)):
            if keys[j] and _cosine(vectors[i], vectors[j]) >= threshold:
                parent[find(i)] = find(j)

    groups: dict[int, list[int]] = defaultdict(list)
    singles: list[list[int]] = []
    for k, (key, indices) in enumerate(unique.items()):
        if key:
            groups[find(k)].extend(indices)
        else:
            singles.extend([i] for i in indices)

    clusters = [sorted(g) for g in groups.values()] + singles
    return sorted(clusters, key=lambda g: (-len(g), g[0]))


def top_terms(texts: list[str], k: int = 3) -> list[str]:
    """Most common meaningful words across a cluster, used as readable tags."""
    counts: Counter[str] = Counter()
    for text in texts:
        counts.update(set(normalize(text)))
    return [term for term, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]
