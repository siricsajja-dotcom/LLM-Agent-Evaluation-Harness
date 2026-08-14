# LLM Agent Robustness Harness - December 2025 (Pushed from VS Code)

A red-teaming / robustness evaluation harness for LLM agents. It doesn't
ask "did the agent get the right answer" — it asks "where does this
agent break," scored against a taxonomy of four failure modes, and
produces a **robustness report card** per agent.

| Failure mode | What it tests |
|---|---|
| **Prompt injection** | Untrusted content the agent processes (a fetched document, a tool result) contains an instruction trying to override the agent's actual task. |
| **Jailbreak** | The user directly asks the agent to abandon a guardrail via persona override, hypothetical/fictional framing, or a claimed authority. |
| **Hallucination** | Given a context passage, does the agent state facts not supported by it — either inventing details or answering confidently when the honest answer is "not in the material"? |
| **Instruction drift** | Over a long multi-turn conversation, does the agent stop following a constraint (format, persona, policy) it was given early on? |

Zero external dependencies — pure Python standard library. Two mock
agents are included (`NaiveAgent`, `GuardedAgent`) so the demo runs
immediately with no API key; point the harness at a real model by
implementing `Agent.respond` the same way against your provider's SDK.

## Quick start

```bash
git clone <this repo> && cd agent-robustness-harness
python3 -m examples.run_demo
```

This runs all 16 default test cases against both mock agents and
writes `reports/naive_agent_report.html` and
`reports/guarded_agent_report.html` — open either in a browser.
Sample console output:

```
=== naive-agent (undefended baseline) ===
Overall: 5/16 passed (31%), grade F
  hallucination        2/4 passed  grade=F
  instruction_drift    1/3 passed  grade=F
  jailbreak            1/5 passed  grade=F
  prompt_injection     1/4 passed  grade=F

=== guarded-agent (defense-in-depth baseline) ===
Overall: 16/16 passed (100%), grade A
  hallucination        4/4 passed  grade=A
  instruction_drift    3/3 passed  grade=A
  jailbreak            5/5 passed  grade=A
  prompt_injection     4/4 passed  grade=A
```

That spread is the point: the harness actually discriminates a
undefended agent from a defended one, category by category, rather
than producing the same score regardless of what's behind it.

## Wiring up a real agent

```python
from harness import Agent, Message, HarnessRunner, default_suite, write_html_report

class MyAgent:
    name = "my-model-v3"
    def respond(self, messages: list[Message]) -> str:
        # call your provider's API here, e.g.:
        # resp = client.messages.create(model="...", messages=messages)
        # return resp.content[0].text
        ...

outcome = HarnessRunner(MyAgent(), "my-model-v3").run(default_suite(), verbose=True)
write_html_report(outcome, "reports/my_model_v3.html")
print(outcome.pass_rate())
```

## Layout

```
harness/
  agent_interface.py   Agent protocol, FunctionAgent wrapper, FailureMode taxonomy
  case_types.py         TestCase / CaseResult data structures
  scorers.py             shared keyword/JSON scoring primitives + llm_judge hook
  fixtures.py             shared canary-secret system prompt (injection/jailbreak)
  runner.py               replays a case's conversation turn-by-turn against an agent
  report.py               aggregates results into a graded HTML + JSON report card
  cases/
    injection.py          4 prompt-injection cases
    jailbreak.py           5 jailbreak-pattern cases
    hallucination.py        4 grounded/unanswerable QA cases
    drift.py                 3 multi-turn format-persistence cases
examples/
  mock_agents.py         NaiveAgent (vulnerable) / GuardedAgent (robust) baselines
  run_demo.py             runs the suite against both, writes report cards
tests/
  test_harness.py        13 tests covering scorers, runner, suite, and reports
reports/                  generated HTML/JSON report cards land here (gitignored)
```

## Design notes

- **Canary secret, not real harmful content.** Injection and jailbreak
  cases are built around a stand-in secret the agent's system prompt
  protects (`fixtures.CANARY_SYSTEM_PROMPT`), rather than testing
  against actually dangerous requests. This mirrors how real red-team
  programs test exfiltration/override resistance — the secret is an
  inert proxy for "anything the agent shouldn't leak or be steered off
  of," whether that's real system-prompt contents, a tool credential,
  or a stated policy boundary. The jailbreak *patterns* themselves
  (persona override, hypothetical framing, claimed authority) are kept
  generic and illustrative, not tuned to actually defeat a specific
  production model.
- **Scoring is deliberately simple and offline (keyword/JSON checks),
  not a learned judge.** The value of this harness is the taxonomy and
  test design, not a state-of-the-art classifier. `scorers.llm_judge`
  shows how to swap in a stronger model as the judge for failure modes
  (subtle hallucinations especially) where a keyword heuristic is too
  blunt, without changing anything else about the harness.
- **Severity-weighted grading.** Each case has a severity
  (`low`/`medium`/`high`); the report card computes both a raw pass
  rate and a severity-weighted one (high-severity failures count 3x),
  because failing a benign control case and leaking a secret under
  direct pressure are not the same thing.
- **Control cases are included on purpose.** Each category includes at
  least one benign case with no attack at all, so the harness can't
  reward an agent that simply refuses everything — a robust agent has
  to actually do the legitimate task, not just close down.
- **Multi-turn replay is faithful, not flattened.** `HarnessRunner`
  calls the agent after every user turn and feeds its real reply back
  into the transcript before the next turn, so instruction-drift cases
  test what an agent does with an actual accumulating conversation
  history, not a single concatenated prompt.

## Running tests

```bash
python3 -m unittest discover -s tests -v
```
