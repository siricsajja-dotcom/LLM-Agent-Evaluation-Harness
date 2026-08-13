"""Runs the default test suite against both mock agents and writes a
report card for each to reports/, plus prints a summary to stdout.

    python3 -m examples.run_demo
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import HarnessRunner, default_suite, write_html_report, write_json_report  # noqa: E402
from examples.mock_agents import NaiveAgent, GuardedAgent  # noqa: E402


def run_and_report(agent, out_stub: str):
    suite = default_suite()
    runner = HarnessRunner(agent, agent_name=agent.name)
    print(f"\n=== {agent.name} ===")
    outcome = runner.run(suite, verbose=True)

    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    html_path = reports_dir / f"{out_stub}.html"
    json_path = reports_dir / f"{out_stub}.json"
    write_html_report(outcome, str(html_path))
    data = write_json_report(outcome, str(json_path))

    print(f"\nOverall: {data['n_passed']}/{data['n_cases']} passed "
          f"({data['overall_pass_rate']*100:.0f}%), grade {data['overall_grade']}")
    for cat, info in sorted(data["categories"].items()):
        print(f"  {cat:20s} {info['n_passed']}/{info['n_cases']} passed  grade={info['grade']}")
    print(f"Report written to {html_path}")
    return data


def main():
    run_and_report(NaiveAgent(), "naive_agent_report")
    run_and_report(GuardedAgent(), "guarded_agent_report")


if __name__ == "__main__":
    main()
