from app.retrieval import strong_matches


def test_only_qualifying_evidence_passes_to_generation():
    matches = [("strong", "VPN", 0.8), ("boundary", "VPN", 0.35), ("weak", "MFA", 0.2)]
    assert [c for c, _, _ in strong_matches(matches, 0.35)] == ["strong", "boundary"]


def test_no_match_and_low_score_produce_empty_context():
    assert strong_matches([], 0.35) == []
    assert strong_matches([("irrelevant", "policy", 0.1)], 0.35) == []
