from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Dict, List

from .aggregate import aggregate_run
from .storage import RunStorage


def generate_report(root: Path, run_name: str) -> Dict[str, object]:
    summary = aggregate_run(root, run_name)
    storage = RunStorage(root, run_name)

    leaderboard_svg = _bar_chart_svg(
        title="Overall Writing Score",
        rows=[
            (row["candidate_model_id"], row["overall"])
            for row in sorted(summary["writing_by_model"], key=lambda item: item["overall"], reverse=True)
        ],
        value_label="Score",
        max_value=5.0,
    )
    judge_svg = _bar_chart_svg(
        title="Judge Quality",
        rows=[
            (row["judge_model_id"], row["agreement_overall"])
            for row in sorted(summary["judge_quality"], key=lambda item: item["agreement_overall"], reverse=True)
        ],
        value_label="Agreement",
        max_value=1.0,
    )
    storage.write_analysis_text("overall_scores.svg", leaderboard_svg)
    storage.write_analysis_text("judge_quality.svg", judge_svg)
    report_md = _report_markdown(summary)
    storage.write_analysis_text("REPORT.md", report_md)
    return summary


def _report_markdown(summary: Dict[str, object]) -> str:
    writing_rows = sorted(summary["writing_by_model"], key=lambda item: item["overall"], reverse=True)
    judge_rows = sorted(summary["judge_quality"], key=lambda item: item["agreement_overall"], reverse=True)

    def table(rows: List[Dict[str, object]], fields: List[str]) -> str:
        header = "| " + " | ".join(fields) + " |"
        divider = "| " + " | ".join(["---"] * len(fields)) + " |"
        body = "\n".join(
            "| " + " | ".join(str(row.get(field, "")) for field in fields) + " |" for row in rows
        )
        return "\n".join([header, divider, body]) if body else "\n".join([header, divider])

    lines = [
        f"# ZinsserBench Report: {summary['run_name']}",
        "",
        f"- Benchmark version: `{summary['benchmark_version']}`",
        f"- Models evaluated: `{len(summary['writing_by_model'])}`",
        "",
        "## Overall writing leaderboard",
        "",
        table(writing_rows, ["candidate_model_id", "overall", "clarity", "simplicity", "structure_flow"]),
        "",
        "## Judge quality leaderboard",
        "",
        table(judge_rows, ["judge_model_id", "agreement_overall", "agreement_clarity", "agreement_structure_flow"]),
        "",
        "## Analysis files",
        "",
        "- `writing_by_model.csv`",
        "- `writing_by_model_axis.csv`",
        "- `writing_by_model_category.csv`",
        "- `writing_by_model_prompt.csv`",
        "- `writing_by_prompt_axis.csv`",
        "- `judge_quality.csv`",
        "- `model_prompt_details.csv`",
        "",
        "## Charts",
        "",
        "![Overall scores](overall_scores.svg)",
        "",
        "![Judge quality](judge_quality.svg)",
        "",
    ]
    return "\n".join(lines)


def _bar_chart_svg(title: str, rows: List[tuple], value_label: str, max_value: float) -> str:
    width = 900
    top = 60
    row_height = 36
    chart_left = 220
    chart_right = width - 40
    chart_width = chart_right - chart_left
    height = top + row_height * max(1, len(rows)) + 40
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text { font-family: Menlo, Consolas, monospace; fill: #1f2937; } .title { font-size: 24px; font-weight: 700; } .label { font-size: 13px; } .value { font-size: 12px; } .bar { fill: #2f6fed; } .axis { stroke: #d1d5db; stroke-width: 1; }</style>',
        f'<text x="24" y="32" class="title">{html.escape(title)}</text>',
        f'<text x="{chart_left}" y="32" class="label">{html.escape(value_label)}</text>',
        f'<line x1="{chart_left}" y1="{top - 12}" x2="{chart_right}" y2="{top - 12}" class="axis" />',
    ]
    for index, (label, value) in enumerate(rows):
        y = top + index * row_height
        bar_width = 0 if max_value <= 0 else (float(value) / max_value) * chart_width
        parts.extend(
            [
                f'<text x="24" y="{y + 18}" class="label">{html.escape(str(label))}</text>',
                f'<rect x="{chart_left}" y="{y}" width="{bar_width:.2f}" height="20" rx="4" class="bar" />',
                f'<text x="{chart_left + bar_width + 8:.2f}" y="{y + 15}" class="value">{float(value):.3f}</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts)
