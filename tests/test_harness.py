import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.agent_interface import FailureMode, FunctionAgent, Message
from harness.case_types import CaseResult, TestCase
from harness.runner import HarnessRunner
from harness.report import build_report_data, render_html_report
from harness.scorers import (
    contains_any, contains_none, is_valid_json_object_with_key, looks_like_refusal,
)
from harness.cases import default_suite
from examples.mock_agents import NaiveAgent, GuardedAgent


class TestScorers(unittest.TestCase):
    def test_contains_any_case_insensitive(self):
        self.assertEqual(contains_any("Hello World", ["world"]), "world")
        self.assertIsNone(contains_any("Hello World", ["xyz"]))

    def test_contains_none(self):
        self.assertTrue(contains_none("abc", ["xyz"]))
        self.assertFalse(contains_none("abc", ["b"]))

    def test_valid_json_with_key(self):
        self.assertTrue(is_valid_json_object_with_key('{"answer": "x"}', "answer"))
        self.assertFalse(is_valid_json_object_with_key('{"other": "x"}', "answer"))
        self.assertFalse(is_valid_json_object_with_key("not json at all", "answer"))

    def test_valid_json_handles_code_fence(self):
        text = '```json\n{"answer": "x"}\n```'
        self.assertTrue(is_valid_json_object_with_key(text, "answer"))

    def test_looks_like_refusal(self):
        self.assertTrue(looks_like_refusal("I can't help with that."))
        self.assertFalse(looks_like_refusal("Sure, here's the answer."))


class TestRunner(unittest.TestCase):
    def test_single_turn_case(self):
        def evaluate(response, case, transcript):
            passed = "hello" in response.lower()
            return CaseResult(case.id, case.category, passed, 1.0 if passed else 0.0,
                               "detail", response)

        case = TestCase(
            id="t1", category=FailureMode.JAILBREAK, description="d",
            messages=[Message(role="system", content="sys"),
                      Message(role="user", content="say hello")],
            evaluate=evaluate,
        )
        agent = FunctionAgent(lambda msgs: "hello there")
        outcome = HarnessRunner(agent, "test-agent").run([case])
        self.assertEqual(len(outcome.results), 1)
        self.assertTrue(outcome.results[0].passed)
        self.assertEqual(outcome.pass_rate(), 1.0)

    def test_multi_turn_case_feeds_history_back(self):
        seen_lengths = []

        def agent_fn(msgs):
            seen_lengths.append(len(msgs))
            return f"reply-{len(msgs)}"

        def evaluate(response, case, transcript):
            return CaseResult(case.id, case.category, True, 1.0, "ok", response)

        case = TestCase(
            id="t2", category=FailureMode.INSTRUCTION_DRIFT, description="d",
            messages=[
                Message(role="system", content="sys"),
                Message(role="user", content="turn1"),
                Message(role="user", content="turn2"),
                Message(role="user", content="turn3"),
            ],
            evaluate=evaluate,
        )
        agent = FunctionAgent(agent_fn)
        HarnessRunner(agent, "test-agent").run([case])
        # transcript grows: [sys,u1]=2, then [sys,u1,a1,u2]=4, then [...,a2,u3]=6
        self.assertEqual(seen_lengths, [2, 4, 6])


class TestDefaultSuite(unittest.TestCase):
    def test_suite_covers_all_categories(self):
        suite = default_suite()
        categories = {c.category for c in suite}
        self.assertEqual(categories, set(FailureMode))

    def test_all_case_ids_unique(self):
        suite = default_suite()
        ids = [c.id for c in suite]
        self.assertEqual(len(ids), len(set(ids)))

    def test_guarded_agent_outperforms_naive_agent(self):
        suite = default_suite()
        naive_outcome = HarnessRunner(NaiveAgent(), "naive").run(suite)
        guarded_outcome = HarnessRunner(GuardedAgent(), "guarded").run(suite)
        self.assertGreater(guarded_outcome.pass_rate(), naive_outcome.pass_rate())
        # guarded should be strong; naive should be clearly worse
        self.assertGreaterEqual(guarded_outcome.pass_rate(), 0.9)
        self.assertLessEqual(naive_outcome.pass_rate(), 0.6)


class TestReport(unittest.TestCase):
    def test_report_data_has_all_categories(self):
        suite = default_suite()
        outcome = HarnessRunner(GuardedAgent(), "guarded").run(suite)
        data = build_report_data(outcome)
        self.assertEqual(data["n_cases"], len(suite))
        self.assertIn("overall_grade", data)
        for cat in FailureMode:
            self.assertIn(cat.value, data["categories"])

    def test_html_report_renders_without_error(self):
        suite = default_suite()
        agent = NaiveAgent()
        outcome = HarnessRunner(agent, agent.name).run(suite)
        html_out = render_html_report(outcome)
        self.assertIn("Robustness Report Card", html_out)
        self.assertIn("naive-agent", html_out)

    def test_json_report_is_serializable(self):
        suite = default_suite()
        outcome = HarnessRunner(GuardedAgent(), "guarded").run(suite)
        data = build_report_data(outcome)
        json.dumps(data, default=str)  # must not raise


if __name__ == "__main__":
    unittest.main()
