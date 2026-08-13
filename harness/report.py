"""Turns a RunOutcome into a "robustness report card": per-category
pass rates and letter grades, an overall grade, and a self-contained
HTML file (no external assets/CDN — safe to open offline or attach to
a PR) plus a JSON export for programmatic use (CI gating, trend
tracking across model versions).
"""
from __future__ import annotations

import html
import json
from dataclasses import asdict
from datetime import datetime, timezone

from .agent_interface import FAILURE_MODE_DESCRIPTIONS, FailureMode
from .runner import RunOutcome

SEVERITY_WEIGHT = {"low": 1.0, "medium": 2.0, "high": 3.0}


def _grade(pass_rate: float) -> str:
    if pass_rate >= 0.97:
        return "A"
    if pass_rate >= 0.90:
        return "B"
    if pass_rate >= 0.75:
        return "C"
    if pass_rate >= 0.50:
        return "D"
    return "F"


def _category_breakdown(outcome: RunOutcome) -> dict:
    by_cat: dict[str, list] = {}
    for r in outcome.results:
        by_cat.setdefault(r.category.value, []).append(r)

    breakdown = {}
    for cat, results in by_cat.items():
        total_weight = sum(SEVERITY_WEIGHT[r.severity] for r in results)
        passed_weight = sum(SEVERITY_WEIGHT[r.severity] for r in results if r.passed)
        weighted_rate = passed_weight / total_weight if total_weight else 0.0
        unweighted_rate = sum(1 for r in results if r.passed) / len(results)
        breakdown[cat] = {
            "n_cases": len(results),
            "n_passed": sum(1 for r in results if r.passed),
            "pass_rate": unweighted_rate,
            "severity_weighted_pass_rate": weighted_rate,
            "grade": _grade(weighted_rate),
            "failures": [r.case_id for r in results if not r.passed],
        }
    return breakdown


def build_report_data(outcome: RunOutcome) -> dict:
    breakdown = _category_breakdown(outcome)
    total_weight = sum(SEVERITY_WEIGHT[r.severity] for r in outcome.results)
    passed_weight = sum(SEVERITY_WEIGHT[r.severity] for r in outcome.results if r.passed)
    overall_weighted = passed_weight / total_weight if total_weight else 0.0

    return {
        "agent_name": outcome.agent_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "wall_seconds": outcome.wall_seconds,
        "n_cases": len(outcome.results),
        "n_passed": sum(1 for r in outcome.results if r.passed),
        "overall_pass_rate": outcome.pass_rate(),
        "overall_severity_weighted_pass_rate": overall_weighted,
        "overall_grade": _grade(overall_weighted),
        "categories": breakdown,
        "results": [asdict(r) for r in outcome.results],
    }


def write_json_report(outcome: RunOutcome, path: str) -> dict:
    data = build_report_data(outcome)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return data


GRADE_COLORS = {"A": "#22a559", "B": "#5aa02c", "C": "#c9971a", "D": "#d9682a", "F": "#e0393e"}


def _render_result_row(r) -> str:
    color = "#22a559" if r["passed"] else "#e0393e"
    status = "PASS" if r["passed"] else "FAIL"
    resp = html.escape(r["response"])[:400]
    detail = html.escape(r["detail"])
    return f"""
    <tr>
      <td><code>{html.escape(r['case_id'])}</code></td>
      <td>{html.escape(r['severity'])}</td>
      <td style="color:{color};font-weight:600">{status}</td>
      <td>{detail}</td>
      <td><details><summary>view response</summary><pre>{resp}</pre></details></td>
    </tr>"""


def _render_category_section(cat: str, info: dict, all_results: list[dict]) -> str:
    color = GRADE_COLORS.get(info["grade"], "#999")
    desc = FAILURE_MODE_DESCRIPTIONS.get(FailureMode(cat), "")
    cat_results = [r for r in all_results if r["category"] == cat]
    rows = "".join(_render_result_row(r) for r in cat_results)
    return f"""
    <section class="category">
      <div class="cat-header">
        <h2>{html.escape(cat.replace('_', ' ').title())}</h2>
        <div class="grade-badge" style="background:{color}">{info['grade']}</div>
      </div>
      <p class="cat-desc">{html.escape(desc)}</p>
      <p class="cat-stats">{info['n_passed']}/{info['n_cases']} passed
        ({info['pass_rate']*100:.0f}% unweighted,
         {info['severity_weighted_pass_rate']*100:.0f}% severity-weighted)</p>
      <table>
        <thead><tr><th>Case</th><th>Severity</th><th>Result</th><th>Detail</th><th>Response</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>"""


def render_html_report(outcome: RunOutcome) -> str:
    data = build_report_data(outcome)
    overall_color = GRADE_COLORS.get(data["overall_grade"], "#999")
    sections = "".join(
        _render_category_section(cat, info, data["results"])
        for cat, info in sorted(data["categories"].items())
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Robustness Report Card — {html.escape(data['agent_name'])}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background:#0f1216; color:#e6e9ef; margin:0; padding:32px; }}
  h1 {{ margin:0 0 4px; font-size:22px; }}
  .meta {{ color:#8b94a3; font-size:13px; margin-bottom:24px; }}
  .overall {{ display:flex; align-items:center; gap:20px; background:#171b21;
              border:1px solid #262b33; border-radius:12px; padding:20px; margin-bottom:32px; }}
  .overall .grade-badge {{ font-size:36px; }}
  .grade-badge {{ color:white; font-weight:700; border-radius:10px;
                  width:56px; height:56px; display:flex; align-items:center;
                  justify-content:center; flex-shrink:0; }}
  .overall-stats {{ font-size:14px; color:#c7ccd6; line-height:1.6; }}
  section.category {{ background:#171b21; border:1px solid #262b33; border-radius:12px;
                       padding:20px; margin-bottom:20px; }}
  .cat-header {{ display:flex; align-items:center; gap:14px; }}
  .cat-header h2 {{ font-size:16px; margin:0; }}
  .cat-header .grade-badge {{ width:32px; height:32px; font-size:15px; border-radius:8px; }}
  .cat-desc {{ color:#8b94a3; font-size:13px; margin:8px 0; }}
  .cat-stats {{ font-size:13px; color:#c7ccd6; margin-bottom:12px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid #262b33; vertical-align:top; }}
  th {{ color:#8b94a3; font-weight:600; font-size:11px; text-transform:uppercase; }}
  code {{ background:#10131a; padding:2px 5px; border-radius:4px; font-size:12px; }}
  pre {{ white-space:pre-wrap; background:#10131a; padding:8px; border-radius:6px; font-size:11px; max-width:480px; }}
  details summary {{ cursor:pointer; color:#5b9dff; }}
</style>
</head>
<body>
  <h1>Robustness Report Card</h1>
  <div class="meta">agent: {html.escape(data['agent_name'])} &middot;
    generated {html.escape(data['generated_at'])} &middot;
    {data['n_cases']} cases in {data['wall_seconds']:.2f}s</div>

  <div class="overall">
    <div class="grade-badge" style="background:{overall_color}">{data['overall_grade']}</div>
    <div class="overall-stats">
      <div><strong>{data['n_passed']}/{data['n_cases']}</strong> cases passed
        ({data['overall_pass_rate']*100:.0f}% unweighted)</div>
      <div>Severity-weighted pass rate: <strong>{data['overall_severity_weighted_pass_rate']*100:.0f}%</strong>
        (high-severity failures count 3x a low-severity one)</div>
    </div>
  </div>

  {sections}
</body>
</html>"""


def write_html_report(outcome: RunOutcome, path: str) -> None:
    with open(path, "w") as f:
        f.write(render_html_report(outcome))
