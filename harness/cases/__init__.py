from ..case_types import TestCase
from . import injection, jailbreak, hallucination, drift


def default_suite() -> list[TestCase]:
    """All built-in test cases across all four failure-mode categories."""
    return [
        *injection.CASES,
        *jailbreak.CASES,
        *hallucination.CASES,
        *drift.CASES,
    ]


__all__ = ["default_suite", "injection", "jailbreak", "hallucination", "drift"]
