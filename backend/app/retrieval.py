def strong_matches(matches, threshold: float):
    """Cosine threshold is an evidence gate, never a confidence percentage."""
    return [(chunk, document, float(score)) for chunk, document, score in matches if float(score) >= threshold]
