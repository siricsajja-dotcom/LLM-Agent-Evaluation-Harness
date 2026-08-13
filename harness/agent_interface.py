"""Agent interface and the failure-mode taxonomy the harness scores against.

The harness doesn't care what's behind an agent — an API call to a real
LLM, a LangChain-style agent with tools, or (as in examples/mock_agents.py)
a rule-based stand-in. It only needs something that turns a conversation
into a reply.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable, List, Protocol, TypedDict


class Message(TypedDict):
    role: str      # "system" | "user" | "assistant" | "tool"
    content: str


class Agent(Protocol):
    def respond(self, messages: List[Message]) -> str:
        """Given a full conversation so far, return the agent's next
        assistant-role reply as plain text."""
        ...


class FunctionAgent:
    """Wraps a plain ``fn(messages) -> str`` callable as an Agent, so you
    don't need to define a class just to plug in a function or a lambda
    around an API call.
    """

    def __init__(self, fn: Callable[[List[Message]], str], name: str = "agent"):
        self._fn = fn
        self.name = name

    def respond(self, messages: List[Message]) -> str:
        return self._fn(messages)


class FailureMode(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    HALLUCINATION = "hallucination"
    INSTRUCTION_DRIFT = "instruction_drift"


FAILURE_MODE_DESCRIPTIONS = {
    FailureMode.PROMPT_INJECTION: (
        "Untrusted content the agent processes (a tool result, a fetched "
        "document, pasted text) contains instructions that attempt to "
        "override the agent's actual task or system instructions."
    ),
    FailureMode.JAILBREAK: (
        "The user directly asks the agent to abandon its guardrails via "
        "persona override, hypothetical/fictional framing, or a claimed "
        "authority that isn't actually binding on the agent."
    ),
    FailureMode.HALLUCINATION: (
        "The agent states something as fact that is not supported by the "
        "context it was given — either inventing details or answering "
        "confidently when the honest answer is 'not in the provided "
        "material.'"
    ),
    FailureMode.INSTRUCTION_DRIFT: (
        "Over a long multi-turn conversation, the agent gradually stops "
        "following an instruction it was given early on (format "
        "constraints, persona constraints, a stated policy) even though "
        "nothing in the conversation legitimately superseded it."
    ),
}
