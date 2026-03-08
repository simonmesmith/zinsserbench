from __future__ import annotations

import html
from pathlib import Path
from typing import Dict, List

from .aggregate import aggregate_run
from .storage import RunStorage


def generate_report(root: Path, run_name: str) -> Dict[str, object]:
    summary = aggregate_run(root, run_name)
    storage = RunStorage(root, run_name)
    writing_rows = sorted(summary["writing_by_model"], key=lambda item: item["criteria_average"], reverse=True)

    criteria_svg = _bar_chart_svg(
        title="Nonfiction Writing Criteria Average",
        rows=[
            (row["candidate_model_id"], row["criteria_average"])
            for row in writing_rows
        ],
        value_label="Score",
        max_value=5.0,
    )
    overall_svg = _bar_chart_svg(
        title="Nonfiction Writing Overall Average",
        rows=[
            (row["candidate_model_id"], row["overall_average"])
            for row in sorted(summary["writing_by_model"], key=lambda item: item["overall_average"], reverse=True)
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
    comparison_svg = _comparison_bar_chart_svg(
        title="Overall Average vs. Criteria Average",
        rows=[
            (
                row["candidate_model_id"],
                row["overall_average"],
                row["criteria_average"],
            )
            for row in writing_rows
        ],
        left_label="Overall average",
        right_label="Criteria average",
        max_value=5.0,
    )
    gap_svg = _delta_chart_svg(
        title="Criteria Average Minus Overall Average",
        rows=[
            (row["candidate_model_id"], row["criteria_minus_overall"])
            for row in sorted(summary["writing_by_model"], key=lambda item: item["criteria_minus_overall"])
        ],
    )
    axis_heatmap_svg = _axis_heatmap_svg(
        title="Model Strengths by Rubric Axis",
        rows=writing_rows,
    )
    storage.write_analysis_text("criteria_average.svg", criteria_svg)
    storage.write_analysis_text("overall_average.svg", overall_svg)
    storage.write_analysis_text("overall_vs_criteria.svg", comparison_svg)
    storage.write_analysis_text("criteria_minus_overall.svg", gap_svg)
    storage.write_analysis_text("axis_heatmap.svg", axis_heatmap_svg)
    storage.write_analysis_text("judge_quality.svg", judge_svg)
    report_md = _report_markdown(summary)
    storage.write_analysis_text("REPORT.md", report_md)
    return summary


def _report_markdown(summary: Dict[str, object]) -> str:
    writing_rows = sorted(summary["writing_by_model"], key=lambda item: item["criteria_average"], reverse=True)
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
        f"- Quarantined outputs excluded from scoring: `{len(summary.get('quarantined_outputs', []))}`",
        f"- Outputs with truncation warnings: `{len(summary.get('truncation_warnings', []))}`",
        f"- Outputs sanitized before judging: `{len(summary.get('sanitization_warnings', []))}`",
        f"- Same-company judgments skipped: `{len(summary.get('skipped_same_company_judgments', []))}`",
        "",
        "## Writing leaderboard",
        "",
        table(
            writing_rows,
            [
                "candidate_model_id",
                "criteria_average",
                "overall_average",
                "criteria_minus_overall",
                "clarity",
                "simplicity",
                "structure_flow",
            ],
        ),
        "",
        "Criteria average is the primary headline metric. It averages the six rubric criteria for each judged item, then averages those item-level means across the benchmark. Overall average is retained as a secondary diagnostic based on the judges' explicit overall scores.",
        "",
        "## Judge quality leaderboard",
        "",
        table(judge_rows, ["judge_model_id", "agreement_overall", "agreement_clarity", "agreement_structure_flow"]),
        "",
        "## Quarantined outputs",
        "",
    ]
    quarantined_rows = summary.get("quarantined_outputs", [])
    if quarantined_rows:
        lines.extend(
            [
                table(quarantined_rows, ["candidate_model_id", "prompt_id", "reason", "word_count", "minimum_words"]),
                "",
            ]
        )
    else:
        lines.extend(["None.", ""])

    lines.extend(
        [
            "## Generation warnings",
            "",
        ]
    )
    warning_sections = [
        ("Exact cap hits", "exact_cap_hits", ["candidate_model_id", "prompt_id", "completion_tokens", "max_output_tokens"]),
        ("Truncation warnings", "truncation_warnings", ["candidate_model_id", "prompt_id", "reasons", "generation_attempt"]),
        ("Sanitization warnings", "sanitization_warnings", ["candidate_model_id", "prompt_id", "removed_ratio", "patterns", "generation_attempt"]),
        ("Skipped same-company judgments", "skipped_same_company_judgments", ["candidate_model_id", "prompt_id", "judge_model_id", "company"]),
    ]
    for title, key, fields in warning_sections:
        lines.extend([f"### {title}", ""])
        rows = summary.get(key, [])
        if rows:
            lines.extend([table(rows, fields), ""])
        else:
            lines.extend(["None.", ""])

    lines.extend(
        [
        "## Analysis files",
        "",
        "- `quarantined_outputs.csv`",
        "- `exact_cap_hits.csv`",
        "- `truncation_warnings.csv`",
        "- `sanitization_warnings.csv`",
        "- `skipped_same_company_judgments.csv`",
        "- `excluded_for_insufficient_judges.csv`",
        "- `response_lengths_by_model.csv`",
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
        "![Criteria average](criteria_average.svg)",
        "",
        "![Overall average](overall_average.svg)",
        "",
        "![Judge quality](judge_quality.svg)",
        "",
        "![Overall vs criteria](overall_vs_criteria.svg)",
        "",
        "![Criteria minus overall](criteria_minus_overall.svg)",
        "",
        "![Axis heatmap](axis_heatmap.svg)",
        "",
        ]
    )
    return "\n".join(lines)


def _bar_chart_svg(title: str, rows: List[tuple], value_label: str, max_value: float) -> str:
    width = 900
    left_padding = 24
    title_y = 32
    subtitle_y = 56
    top = 72
    row_height = 36
    source_text = "Source: ZinsserBench (github.com/simonmesmith/zinsserbench)"
    max_label_length = max((len(str(label)) for label, _ in rows), default=0)
    chart_left = max(280, min(420, left_padding + max_label_length * 9))
    chart_right = width - 40
    chart_width = chart_right - chart_left
    height = top + row_height * max(1, len(rows)) + 56
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text { font-family: Menlo, Consolas, monospace; fill: #1f2937; } .title { font-size: 24px; font-weight: 700; } .label { font-size: 13px; } .value { font-size: 12px; } .source { font-size: 12px; fill: #4b5563; } .bar { fill: #2f6fed; } .axis { stroke: #d1d5db; stroke-width: 1; }</style>',
        f'<text x="{left_padding}" y="{title_y}" class="title">{html.escape(title)}</text>',
        f'<text x="{chart_left}" y="{subtitle_y}" class="label">{html.escape(value_label)}</text>',
        f'<line x1="{chart_left}" y1="{top - 12}" x2="{chart_right}" y2="{top - 12}" class="axis" />',
    ]
    for index, (label, value) in enumerate(rows):
        y = top + index * row_height
        bar_width = 0 if max_value <= 0 else (float(value) / max_value) * chart_width
        parts.extend(
            [
                f'<text x="{left_padding}" y="{y + 18}" class="label">{html.escape(str(label))}</text>',
                f'<rect x="{chart_left}" y="{y}" width="{bar_width:.2f}" height="20" rx="4" class="bar" />',
                f'<text x="{chart_left + bar_width + 8:.2f}" y="{y + 15}" class="value">{float(value):.3f}</text>',
            ]
        )
    parts.append(f'<text x="{left_padding}" y="{height - 20}" class="source">{html.escape(source_text)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _comparison_bar_chart_svg(
    title: str,
    rows: List[tuple[str, float, float]],
    left_label: str,
    right_label: str,
    max_value: float,
) -> str:
    width = 960
    left_padding = 24
    title_y = 32
    legend_y = 58
    top = 80
    row_height = 54
    bar_height = 14
    bar_gap = 8
    source_text = "Source: ZinsserBench (github.com/simonmesmith/zinsserbench)"
    max_label_length = max((len(str(label)) for label, _, _ in rows), default=0)
    chart_left = max(280, min(420, left_padding + max_label_length * 9))
    chart_right = width - 40
    chart_width = chart_right - chart_left
    height = top + row_height * max(1, len(rows)) + 56
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text { font-family: Menlo, Consolas, monospace; fill: #1f2937; } .title { font-size: 24px; font-weight: 700; } .label { font-size: 13px; } .value { font-size: 12px; } .source { font-size: 12px; fill: #4b5563; } .overall-bar { fill: #9ca3af; } .average-bar { fill: #2f6fed; } .axis { stroke: #d1d5db; stroke-width: 1; }</style>',
        f'<text x="{left_padding}" y="{title_y}" class="title">{html.escape(title)}</text>',
        f'<rect x="{left_padding}" y="{legend_y - 11}" width="14" height="14" rx="3" class="overall-bar" />',
        f'<text x="{left_padding + 22}" y="{legend_y}" class="label">{html.escape(left_label)}</text>',
        f'<rect x="{left_padding + 180}" y="{legend_y - 11}" width="14" height="14" rx="3" class="average-bar" />',
        f'<text x="{left_padding + 202}" y="{legend_y}" class="label">{html.escape(right_label)}</text>',
        f'<line x1="{chart_left}" y1="{top - 12}" x2="{chart_right}" y2="{top - 12}" class="axis" />',
    ]
    for index, (label, overall, non_overall_average) in enumerate(rows):
        y = top + index * row_height
        overall_width = 0 if max_value <= 0 else (float(overall) / max_value) * chart_width
        average_width = 0 if max_value <= 0 else (float(non_overall_average) / max_value) * chart_width
        parts.extend(
            [
                f'<text x="{left_padding}" y="{y + 20}" class="label">{html.escape(str(label))}</text>',
                f'<rect x="{chart_left}" y="{y}" width="{overall_width:.2f}" height="{bar_height}" rx="4" class="overall-bar" />',
                f'<text x="{chart_left + overall_width + 8:.2f}" y="{y + 11}" class="value">{float(overall):.3f}</text>',
                f'<rect x="{chart_left}" y="{y + bar_height + bar_gap}" width="{average_width:.2f}" height="{bar_height}" rx="4" class="average-bar" />',
                f'<text x="{chart_left + average_width + 8:.2f}" y="{y + bar_height + bar_gap + 11}" class="value">{float(non_overall_average):.3f}</text>',
            ]
        )
    parts.append(f'<text x="{left_padding}" y="{height - 20}" class="source">{html.escape(source_text)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _delta_chart_svg(title: str, rows: List[tuple[str, float]]) -> str:
    width = 960
    left_padding = 24
    title_y = 32
    top = 72
    row_height = 34
    source_text = "Source: ZinsserBench (github.com/simonmesmith/zinsserbench)"
    max_label_length = max((len(str(label)) for label, _ in rows), default=0)
    chart_left = max(280, min(420, left_padding + max_label_length * 9))
    chart_right = width - 40
    chart_width = chart_right - chart_left
    min_value = min((value for _, value in rows), default=0.0)
    max_value = max((value for _, value in rows), default=0.0)
    span = max(abs(min_value), abs(max_value), 0.001)
    zero_x = chart_left + (0 - (-span)) / (2 * span) * chart_width
    height = top + row_height * max(1, len(rows)) + 56
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text { font-family: Menlo, Consolas, monospace; fill: #1f2937; } .title { font-size: 24px; font-weight: 700; } .label { font-size: 13px; } .value { font-size: 12px; } .source { font-size: 12px; fill: #4b5563; } .pos { fill: #059669; } .neg { fill: #dc2626; } .axis { stroke: #d1d5db; stroke-width: 1; }</style>',
        f'<text x="{left_padding}" y="{title_y}" class="title">{html.escape(title)}</text>',
        f'<line x1="{chart_left}" y1="{top - 12}" x2="{chart_right}" y2="{top - 12}" class="axis" />',
        f'<line x1="{zero_x:.2f}" y1="{top - 12}" x2="{zero_x:.2f}" y2="{height - 40}" class="axis" />',
    ]
    for index, (label, value) in enumerate(rows):
        y = top + index * row_height
        scaled = (abs(float(value)) / span) * (chart_width / 2)
        x = zero_x if value >= 0 else zero_x - scaled
        css_class = "pos" if value >= 0 else "neg"
        text_x = x + scaled + 8 if value >= 0 else x - 58
        parts.extend(
            [
                f'<text x="{left_padding}" y="{y + 16}" class="label">{html.escape(str(label))}</text>',
                f'<rect x="{x:.2f}" y="{y}" width="{scaled:.2f}" height="18" rx="4" class="{css_class}" />',
                f'<text x="{text_x:.2f}" y="{y + 14}" class="value">{float(value):+.3f}</text>',
            ]
        )
    parts.append(f'<text x="{left_padding}" y="{height - 20}" class="source">{html.escape(source_text)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _axis_heatmap_svg(title: str, rows: List[Dict[str, object]]) -> str:
    axes = [
        ("clarity", "Clarity"),
        ("simplicity", "Simplicity"),
        ("brevity_economy", "Brevity"),
        ("structure_flow", "Structure"),
        ("specificity_precision", "Specificity"),
        ("humanity_voice", "Voice"),
    ]
    width = 1040
    left_padding = 24
    top = 86
    row_height = 34
    cell_width = 100
    label_width = 320
    title_y = 32
    header_y = 64
    source_text = "Source: ZinsserBench (github.com/simonmesmith/zinsserbench)"
    height = top + row_height * max(1, len(rows)) + 56
    chart_left = left_padding + label_width
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>text { font-family: Menlo, Consolas, monospace; fill: #1f2937; } .title { font-size: 24px; font-weight: 700; } .label { font-size: 12px; } .value { font-size: 12px; font-weight: 700; } .source { font-size: 12px; fill: #4b5563; } .axis { stroke: #d1d5db; stroke-width: 1; }</style>',
        f'<text x="{left_padding}" y="{title_y}" class="title">{html.escape(title)}</text>',
    ]
    all_values = [float(row[axis_key]) for row in rows for axis_key, _ in axes]
    global_low, global_high = _global_heatmap_range(all_values)
    for index, (_, axis_label) in enumerate(axes):
        x = chart_left + index * cell_width
        parts.append(f'<text x="{x + 8}" y="{header_y}" class="label">{html.escape(axis_label)}</text>')
    for row_index, row in enumerate(rows):
        y = top + row_index * row_height
        parts.append(f'<text x="{left_padding}" y="{y + 18}" class="label">{html.escape(str(row["candidate_model_id"]))}</text>')
        for axis_index, (axis_key, _) in enumerate(axes):
            value = float(row[axis_key])
            x = chart_left + axis_index * cell_width
            fill = _relative_score_to_color(value, global_low, global_high)
            text_fill = "#111827" if value < global_low + (global_high - global_low) * 0.72 else "#f9fafb"
            parts.extend(
                [
                    f'<rect x="{x}" y="{y}" width="{cell_width - 8}" height="22" rx="4" fill="{fill}" />',
                    f'<text x="{x + 30}" y="{y + 15}" class="value" fill="{text_fill}">{value:.2f}</text>',
                ]
            )
    parts.append(f'<text x="{left_padding}" y="{height - 20}" class="source">{html.escape(source_text)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def _global_heatmap_range(values: List[float]) -> tuple[float, float]:
    if not values:
        return (1.0, 5.0)
    low = min(values)
    high = max(values)
    if abs(high - low) < 1e-9:
        return (low, low + 1.0)
    return (low, high)


def _relative_score_to_color(value: float, low: float, high: float) -> str:
    ratio = (value - low) / (high - low) if high > low else 0.5
    ratio = max(0.0, min(1.0, ratio))
    red = int(220 - ratio * 124)
    green = int(38 + ratio * 147)
    blue = int(38 + ratio * 61)
    return f"rgb({red},{green},{blue})"
