"""Runs a suite of TestCases against an Agent, turn by turn, and
collects CaseResults. Multi-turn cases (instruction drift) are replayed
faithfully: the runner calls the agent after every user turn and feeds
its actual reply back into the transcript as the assistant turn before
sending the next user message, so a stateful or context-sensitive agent
sees a coherent conversation rather than a flattened prompt.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from .agent_interface import Agent, Message
from .case_types import CaseResult, TestCase


@dataclass
class RunOutcome:
    results: list[CaseResult]
    agent_name: str
    wall_seconds: float

    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)


class HarnessRunner:
    def __init__(self, agent: Agent, agent_name: str = "agent"):
        self.agent = agent
        self.agent_name = agent_name

    def run(self, cases: list[TestCase], verbose: bool = False) -> RunOutcome:
        results: list[CaseResult] = []
        t0 = time.monotonic()
        for case in cases:
            if verbose:
                print(f"  running {case.id} [{case.category.value}] ...", end=" ", flush=True)
            result = self._run_one(case)
            results.append(result)
            if verbose:
                print("PASS" if result.passed else "FAIL")
        return RunOutcome(results=results, agent_name=self.agent_name,
                           wall_seconds=time.monotonic() - t0)

    def _run_one(self, case: TestCase) -> CaseResult:
        transcript: list[Message] = []
        final_response = ""
        for msg in case.messages:
            transcript.append(msg)
            if msg["role"] == "user":
                final_response = self.agent.respond(list(transcript))
                transcript.append(Message(role="assistant", content=final_response))
        return case.run_evaluate(final_response, transcript)
