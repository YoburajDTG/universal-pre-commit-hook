import json
from pathlib import Path
from typing import Dict, List, Optional

from common import BaseChecker
from utils import CommandResult, logger


def generate_json_report(
    checkers: List[BaseChecker],
    results: Dict[str, Dict[str, CommandResult]],
    overall_duration: float,
    success: bool,
) -> str:
    """Generates a JSON-formatted report of the validation results."""
    report_data = {
        "success": success,
        "overall_duration_seconds": overall_duration,
        "projects": [],
    }

    for checker in checkers:
        checker_results = results.get(checker.name, {})
        project_entry = {
            "name": checker.name,
            "project_root": str(checker.context.project_root),
            "stages": {},
        }
        for stage_name, res in checker_results.items():
            project_entry["stages"][stage_name] = {
                "command": res.command,
                "exit_code": res.exit_code,
                "duration_seconds": res.duration,
                "success": res.success,
                "skipped": "skipped" in res.command or "unimplemented" in res.command,
                "stdout": res.stdout,
                "stderr": res.stderr,
            }
        report_data["projects"].append(project_entry)

    return json.dumps(report_data, indent=2)


def generate_markdown_report(
    checkers: List[BaseChecker],
    results: Dict[str, Dict[str, CommandResult]],
    overall_duration: float,
    success: bool,
) -> str:
    """Generates a Markdown-formatted report, perfect for CI step summaries."""
    status_icon = "✅" if success else "❌"
    status_text = "PASSED" if success else "FAILED"

    lines = [
        "# Universal Pre-Commit Validation Summary",
        "",
        f"**Status:** {status_icon} **{status_text}**",
        f"**Overall Duration:** {overall_duration:.2f}s",
        "",
        "## Project Breakdown",
        "",
    ]

    for checker in checkers:
        lines.append(f"### {checker.name} Project")
        lines.append(f"**Root Directory:** `{checker.context.project_root.name}`")
        lines.append("")
        lines.append("| Stage | Status | Duration | Command |")
        lines.append("| :--- | :--- | :--- | :--- |")

        checker_results = results.get(checker.name, {})
        for stage_name, res in checker_results.items():
            if "skipped" in res.command or "unimplemented" in res.command:
                stage_status = "⚠️ Skipped"
                duration_str = "N/A"
            elif res.success:
                stage_status = "✅ Passed"
                duration_str = f"{res.duration:.2f}s"
            else:
                stage_status = "❌ Failed"
                duration_str = f"{res.duration:.2f}s"

            lines.append(
                f"| **{stage_name}** | {stage_status} | {duration_str} | `{res.command}` |"
            )
        lines.append("")

    return "\n".join(lines)


def generate_html_report(
    checkers: List[BaseChecker],
    results: Dict[str, Dict[str, CommandResult]],
    overall_duration: float,
    success: bool,
) -> str:
    """Generates a self-contained, beautifully styled HTML dashboard report."""
    status_class = "passed" if success else "failed"
    status_text = "PASSED" if success else "FAILED"
    status_icon = "✓" if success else "✗"

    project_cards = []
    for checker in checkers:
        checker_results = results.get(checker.name, {})
        stage_rows = []

        for stage_name, res in checker_results.items():
            is_skipped = "skipped" in res.command or "unimplemented" in res.command
            if is_skipped:
                row_class = "stage-skipped"
                badge = '<span class="badge badge-warning">SKIPPED</span>'
                dur = "N/A"
            elif res.success:
                row_class = "stage-passed"
                badge = '<span class="badge badge-success">PASSED</span>'
                dur = f"{res.duration:.2f}s"
            else:
                row_class = "stage-failed"
                badge = '<span class="badge badge-error">FAILED</span>'
                dur = f"{res.duration:.2f}s"

            # Create log accordion if output exists
            log_output = ""
            if res.stdout or res.stderr:
                combined_logs = ""
                if res.stdout:
                    combined_logs += f"--- STDOUT ---\n{res.stdout}\n"
                if res.stderr:
                    combined_logs += f"--- STDERR ---\n{res.stderr}\n"
                log_output = f"""
                <div class="log-accordion">
                    <button class="accordion-header" onclick="toggleAccordion(this)">View Execution Logs</button>
                    <div class="accordion-content">
                        <pre><code>{combined_logs}</code></pre>
                    </div>
                </div>
                """

            stage_rows.append(f"""
            <tr class="{row_class}">
                <td><strong>{stage_name}</strong></td>
                <td>{badge}</td>
                <td>{dur}</td>
                <td><code>{res.command}</code></td>
            </tr>
            <tr>
                <td colspan="4" style="padding: 0; border: none;">{log_output}</td>
            </tr>
            """)

        stage_rows_html = "\n".join(stage_rows)
        project_cards.append(f"""
        <div class="card">
            <div class="card-header">
                <h2>Project: {checker.name}</h2>
                <span class="root-path">Path: <code>{checker.context.project_root.name}</code></span>
            </div>
            <div class="card-body">
                <table>
                    <thead>
                        <tr>
                            <th>Stage</th>
                            <th>Status</th>
                            <th>Duration</th>
                            <th>Invoked Command</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stage_rows_html}
                    </tbody>
                </table>
            </div>
        </div>
        """)

    project_cards_html = "\n".join(project_cards)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation execution dashboard</title>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --primary: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1rem;
        }}
        h1 {{
            margin: 0;
            font-size: 2rem;
            font-weight: 700;
        }}
        .summary-badge {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-weight: bold;
            font-size: 1rem;
        }}
        .summary-badge.passed {{
            background-color: rgba(16, 185, 129, 0.2);
            color: var(--success);
            border: 1px solid var(--success);
        }}
        .summary-badge.failed {{
            background-color: rgba(239, 68, 68, 0.2);
            color: var(--error);
            border: 1px solid var(--error);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 1rem;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card .value {{
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--primary);
        }}
        .stat-card .label {{
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        .card {{
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin-bottom: 2rem;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
        }}
        .card-header {{
            background-color: rgba(51, 65, 85, 0.3);
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .card-header h2 {{
            margin: 0;
            font-size: 1.25rem;
        }}
        .root-path {{
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        .card-body {{
            padding: 1.5rem;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        th {{
            border-bottom: 2px solid var(--border-color);
            padding: 0.75rem;
            color: var(--text-muted);
            font-size: 0.875rem;
            text-transform: uppercase;
        }}
        td {{
            padding: 0.75rem;
            border-bottom: 1px solid var(--border-color);
        }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
        }}
        .badge-success {{
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }}
        .badge-warning {{
            background-color: rgba(245, 158, 11, 0.15);
            color: var(--warning);
        }}
        .badge-error {{
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--error);
        }}
        .log-accordion {{
            margin: 0.5rem 1rem 1rem 1rem;
            border: 1px solid var(--border-color);
            border-radius: 4px;
        }}
        .accordion-header {{
            background-color: #1a202c;
            color: var(--text-muted);
            width: 100%;
            border: none;
            padding: 0.5rem 1rem;
            text-align: left;
            font-size: 0.875rem;
            cursor: pointer;
            outline: none;
        }}
        .accordion-header:hover {{
            background-color: #2d3748;
        }}
        .accordion-content {{
            display: none;
            padding: 1rem;
            background-color: #0b0f19;
            border-top: 1px solid var(--border-color);
            overflow-x: auto;
        }}
        pre {{
            margin: 0;
        }}
        code {{
            font-family: Consolas, Monaco, monospace;
            font-size: 0.875rem;
        }}
    </style>
    <script>
        function toggleAccordion(header) {{
            const content = header.nextElementSibling;
            if (content.style.display === "block") {{
                content.style.display = "none";
            }} else {{
                content.style.display = "block";
            }}
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Universal Validation Report</h1>
            <div class="summary-badge {status_class}">
                <span class="icon">{status_icon}</span>
                <span>{status_text}</span>
            </div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="value">{overall_duration:.2f}s</div>
                <div class="label">Total Duration</div>
            </div>
            <div class="stat-card">
                <div class="value">{len(checkers)}</div>
                <div class="label">Projects Discovered</div>
            </div>
        </div>

        {project_cards_html}
    </div>
</body>
</html>
"""
    return html_content


def write_reports(
    checkers: List[BaseChecker],
    results: Dict[str, Dict[str, CommandResult]],
    overall_duration: float,
    success: bool,
    report_paths: Dict[str, Optional[str]],
) -> None:
    """Helper function to compile and write reports to requested formats."""
    json_path = report_paths.get("json")
    md_path = report_paths.get("md")
    html_path = report_paths.get("html")

    if json_path:
        try:
            content = generate_json_report(checkers, results, overall_duration, success)
            dest = Path(json_path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            logger.info(f"Exported JSON report to: {dest}")
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}")

    if md_path:
        try:
            content = generate_markdown_report(
                checkers, results, overall_duration, success
            )
            dest = Path(md_path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            logger.info(f"Exported Markdown report to: {dest}")
        except Exception as e:
            logger.error(f"Failed to generate Markdown report: {e}")

    if html_path:
        try:
            content = generate_html_report(checkers, results, overall_duration, success)
            dest = Path(html_path).resolve()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            logger.info(f"Exported HTML report to: {dest}")
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
