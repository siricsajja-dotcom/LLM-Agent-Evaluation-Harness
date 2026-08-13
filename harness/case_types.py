"""Core data structures: a TestCase bundles a conversation to run plus
the scoring function that turns the agent's final reply into a
pass/fail verdict; a CaseResult records what happened.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .agent_interface import FailureMode, Message


@dataclass
class CaseResult:
    case_id: str
    category: FailureMode
    passed: bool
    score: float           # 0.0-1.0, usually 1.0 or 0.0 but scorers can be graded
    detail: str            # human-readable explanation of the verdict
    response: str           # the agent's final reply, for manual review
    severity: str = "medium"  # "low" | "medium" | "high" — used for report weighting


@dataclass
class TestCase:
    id: str
    category: FailureMode
    description: str
    # The conversation to send. For multi-turn cases (instruction drift),
    # this is the FULL turn sequence; the runner replays it turn by turn,
    # calling the agent after each user turn and feeding its reply back
    # in as an assistant turn, so a stateless agent function still gets a
    # coherent multi-turn transcript.
    messages: list[Message]
    evaluate: Callable[[str, "TestCase", list[Message]], CaseResult]
    severity: str = "medium"
    metadata: dict = field(default_factory=dict)

    def run_evaluate(self, final_response: str, transcript: list[Message]) -> CaseResult:
        return self.evaluate(final_response, self, transcript)
