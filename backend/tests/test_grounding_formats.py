"""Offline marker normalization and adversarial grounding regression cases."""
import pytest
from dataclasses import replace

from app.generation import ApprovedFact, validate_grounded_content


FACTS = [
    ApprovedFact("F1", "Check that your phone has network access and automatic time enabled.", 1),
    ApprovedFact("F2", "Contact IT for an MFA reset if the authenticator is unavailable.", 1),
    ApprovedFact("F3", "Use an approved managed laptop for remote work.", 2),
]


@pytest.mark.parametrize("marker", ["[F1]", "**[F1]**", "([F1])", "[F1].", "[F1] ."])
@pytest.mark.parametrize("prefix", ["", "- ", "* ", "• ", "1. ", "2) "])
def test_safe_single_fact_formats(prefix, marker):
    result = validate_grounded_content(prefix + "Verify your phone network and automatic time. " + marker, FACTS[:1])
    assert result.reason == "passed"
    assert result.fact_ids == ["F1"] and result.answer.endswith("[1]")


@pytest.mark.parametrize("marker", ["[F1,F2]", "[F1, F2]", "[F1][F2]", "[F1], [F2]", "**[F1]** ([F2])."])
def test_safe_multiple_fact_formats(marker):
    result = validate_grounded_content("Check your phone network and contact IT for an MFA reset if the authenticator is unavailable. " + marker, FACTS[:2])
    assert result.reason == "passed" and result.fact_ids == ["F1", "F2"]
    assert result.answer.endswith("[1]")


def test_multisource_and_shared_source_sentences():
    result = validate_grounded_content(
        "Check your phone network and automatic time. [F1]\n"
        "Contact IT for an MFA reset if the authenticator is unavailable. [F2]\n"
        "Use an approved managed laptop for remote work. [F3]", FACTS)
    assert result.reason == "passed" and result.answer.count("[1]") == 2
    assert result.answer.endswith("[2]")


@pytest.mark.parametrize("text", [
    "Check your phone network. [F99]", "Check your phone network. [F0]",
    "Check your phone network. [F01]", "Check your phone network. [F]",
    "Check your phone network. [F1,]", "Check your phone network. [F1;F2]",
    "Check your phone network. [F1", "Check your phone network. [1]",
    "Check your phone network. ［F1］", "Check your phone network. [Ｆ1]",
    "Check your phone network. [F١]", "Check your phone network. [F\u200b1]",
    "Check your phone network. [F1] An uncited claim.",
    "Check your phone network. [F1][F1]", "Check your phone network. [F1]**",
    "Check your phone network. **[F1]", "Check your phone network. ([F1]",
    "Check your phone network. [F1])", "Check your phone network.",
    "Your MFA reset has a 5-minute SLA. [F2]",
    "Pay $50 for an MFA reset. [F2]", "MFA reset costs five dollars. [F2]",
    "Get HR manager approval for an MFA reset. [F2]",
    "An exception allows an MFA reset without identity checks. [F2]",
    "Download an authenticator from https://example.invalid. [F2]",
    "Email support@example.invalid for an MFA reset. [F2]",
    "Call +1 (555) 123-4567 for an MFA reset. [F2]",
    "Follow the Emergency Recovery Handbook for an MFA reset. [F2]",
    "Contact Bob for an MFA reset. [F2]",
    "Delete your authenticator to get an MFA reset. [F2]",
    "Do not check your phone network or automatic time. [F1]",
    "Your phone network controls the cafeteria menu. [F1]",
    "Football is wonderful. [F1]", "Check your phone network. [F1,F3]",
    "Check your phone network and", "", "   ",
])
def test_reject_unsupported_and_malformed_answers(text):
    # One shared source ensures coverage cannot hide a grammar/value failure.
    result = validate_grounded_content(text, [replace(fact, citation_number=1) for fact in FACTS])
    assert result.answer is None and result.reason != "incomplete_source_coverage"


def test_citation_laundering_cannot_satisfy_source_coverage():
    result = validate_grounded_content("Check your phone network and automatic time. [F1,F3]", [FACTS[0], FACTS[2]])
    assert result.reason == "unrelated_fact_reference"


def test_negation_cannot_be_removed():
    result = validate_grounded_content("Install unapproved software. [F1]", [ApprovedFact("F1", "Do not install unapproved software.", 1)])
    assert result.reason == "lost_negation"


def test_source_coverage_cannot_be_dropped():
    result = validate_grounded_content("Check your phone network. [F1]", FACTS)
    assert result.reason == "incomplete_source_coverage"


def test_captured_single_line_cited_sentence_shape():
    # Safe synthetic fixture matching the captured [xx]. prose [xx]. shape;
    # not a reconstruction or claim of acceptance of the discarded real prose.
    result = validate_grounded_content(
        "Check your phone network and automatic time [F1]. "
        "Contact IT for an MFA reset if the authenticator is unavailable [F2]. "
        "Use an approved managed laptop for remote work [F3].", FACTS)
    assert result.reason == "passed" and result.fact_ids == ["F1", "F2", "F3"]
    assert result.answer.count("\n") == 2


@pytest.mark.parametrize("text", [
    "Check your phone network [F1]. Contact IT for an MFA reset.",
    "Check your phone network [F1]. Get manager approval for an MFA reset [F2].",
    "Check your phone network [F1]. Unrelated claim. Contact IT for an MFA reset [F2].",
])
def test_inline_marker_splitting_never_covers_uncited_or_unsupported_claims(text):
    assert validate_grounded_content(text, FACTS).answer is None
