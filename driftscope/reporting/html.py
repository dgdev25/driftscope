"""Self-contained HTML report renderer — inline CSS, no CDN, no JS.

Time Complexity: O(n) where n is the number of modules.
Space Complexity: O(n) for the output string.
"""

from __future__ import annotations

import html as html_mod

from driftscope.models.report import MetricsResult

_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6; color: #24292f; background: #f6f8fa; padding: 2rem 1rem;
}
.container { max-width: 960px; margin: 0 auto; background: #fff; border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12); padding: 2rem; }
h1 { font-size: 1.75rem; margin-bottom: 0.5rem; color: #1f2328; border-bottom: 2px solid #d0d7de; padding-bottom: 0.5rem; }
h2 { font-size: 1.25rem; margin: 1.5rem 0 0.75rem; color: #1f2328; }
.date-range { color: #656d76; margin-bottom: 1.5rem; }
table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; font-size: 0.875rem; }
th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #d0d7de; }
th { background: #f6f8fa; font-weight: 600; color: #1f2328; }
tr:hover { background: #f6f8fa; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem; margin-bottom: 1.5rem; }
.summary-card { background: #f6f8fa; border-radius: 6px; padding: 1rem; text-align: center; }
.summary-card .value { font-size: 1.5rem; font-weight: 700; color: #1f2328; }
.summary-card .label { font-size: 0.75rem; color: #656d76; text-transform: uppercase; }
.breach { background: #fff8e1; }
.breach-warning { color: #9a6700; font-weight: 600; }
.danger { color: #cf222e; font-weight: 600; }
.metadata { font-size: 0.8125rem; color: #656d76; margin-top: 1.5rem; padding-top: 1rem;
  border-top: 1px solid #d0d7de; }
.metadata ul { list-style: none; }
.metadata li::before { content: "\\2022"; color: #656d76; margin-right: 0.5rem; }
.skipped-list { list-style: none; }
.skipped-list li { padding: 0.25rem 0; }
.skipped-list li::before { content: "\\2022"; color: #656d76; margin-right: 0.5rem; }
"""


def _escape(text: str) -> str:
    """HTML-escape text for safe embedding."""
    return html_mod.escape(str(text))


def render_html(result: MetricsResult) -> str:
    """Render a MetricsResult as a self-contained HTML page.

    Inline CSS only — no CDN references, no JavaScript.

    Args:
        result: The analysis result to render.

    Returns:
        A complete HTML document string.
    """
    start = result.range_start.strftime("%Y-%m-%d")
    end = result.range_end.strftime("%Y-%m-%d")

    total_modules = len(result.modules)
    total_lines = sum(m.total_lines for m in result.modules)
    ai_lines = sum(m.ai_lines for m in result.modules)
    human_lines = sum(m.human_lines for m in result.modules)
    ai_pct = (ai_lines / total_lines * 100) if total_lines > 0 else 0.0

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('<meta charset="UTF-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    parts.append(f"<title>DriftScope Report &mdash; {start} to {end}</title>")
    parts.append(f"<style>{_CSS}</style>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append('<div class="container">')

    # Header
    parts.append("<h1>DriftScope Report</h1>")
    parts.append(f'<p class="date-range">Analysis period: {_escape(start)} to {_escape(end)}</p>')

    # Executive summary
    parts.append("<h2>Executive Summary</h2>")
    parts.append('<div class="summary-grid">')
    parts.append(f'<div class="summary-card"><div class="value">{total_modules}</div><div class="label">Modules</div></div>')
    parts.append(f'<div class="summary-card"><div class="value">{total_lines:,}</div><div class="label">Total Lines</div></div>')
    parts.append(f'<div class="summary-card"><div class="value">{ai_lines:,}</div><div class="label">AI Lines</div></div>')
    parts.append(f'<div class="summary-card"><div class="value">{human_lines:,}</div><div class="label">Human Lines</div></div>')
    parts.append(f'<div class="summary-card"><div class="value">{ai_pct:.1f}%</div><div class="label">AI Attribution</div></div>')
    parts.append("</div>")

    # Survival table
    parts.append("<h2>Survival Rates</h2>")
    parts.append("<table>")
    parts.append("<thead><tr><th>Module</th><th>Window</th><th>AI Rate</th><th>Human Rate</th></tr></thead>")
    parts.append("<tbody>")
    for mod in result.modules:
        for window_key in sorted(mod.survival.keys()):
            sm = mod.survival[window_key]
            parts.append(
                f"<tr><td>{_escape(mod.module_path)}</td><td>{_escape(sm.window)}</td>"
                f"<td>{sm.ai_survival_rate:.1%}</td><td>{sm.human_survival_rate:.1%}</td></tr>"
            )
    parts.append("</tbody></table>")

    # Complexity table
    parts.append("<h2>Complexity Deltas</h2>")
    parts.append("<table>")
    parts.append(
        "<thead><tr><th>Module</th><th>AI Cyclomatic &Delta;</th>"
        "<th>Human Cyclomatic &Delta;</th><th>AI Cognitive &Delta;</th>"
        "<th>Human Cognitive &Delta;</th></tr></thead>"
    )
    parts.append("<tbody>")
    for mod in result.modules:
        c = mod.complexity
        parts.append(
            f"<tr><td>{_escape(mod.module_path)}</td>"
            f"<td>{c.cyclomatic_delta_ai:.1f}</td><td>{c.cyclomatic_delta_human:.1f}</td>"
            f"<td>{c.cognitive_delta_ai:.1f}</td><td>{c.cognitive_delta_human:.1f}</td></tr>"
        )
    parts.append("</tbody></table>")

    # Churn table
    parts.append("<h2>Churn Attribution</h2>")
    parts.append("<table>")
    parts.append("<thead><tr><th>Module</th><th>Total Churn</th><th>AI Churn</th><th>AI Attribution %</th></tr></thead>")
    parts.append("<tbody>")
    for mod in result.modules:
        ch = mod.churn
        parts.append(
            f"<tr><td>{_escape(mod.module_path)}</td>"
            f"<td>{ch.total_churn_lines}</td><td>{ch.ai_churn_lines}</td>"
            f"<td>{ch.ai_churn_attribution_pct:.1f}%</td></tr>"
        )
    parts.append("</tbody></table>")

    # Threshold breaches
    parts.append("<h2>Threshold Breaches</h2>")
    if result.threshold_breaches:
        parts.append('<table class="breach">')
        parts.append("<thead><tr><th>Metric</th><th>Module</th><th>Value</th><th>Threshold</th><th>Direction</th></tr></thead>")
        parts.append("<tbody>")
        for breach in result.threshold_breaches:
            parts.append(
                f"<tr><td>{_escape(breach.metric)}</td>"
                f"<td>{_escape(breach.module_path)}</td>"
                f'<td class="danger">{breach.value}</td>'
                f"<td>{breach.threshold}</td>"
                f"<td>{_escape(breach.direction)}</td></tr>"
            )
        parts.append("</tbody></table>")
    else:
        parts.append('<p>No threshold breaches detected.</p>')

    # Skipped files
    parts.append("<h2>Skipped Files</h2>")
    if result.skipped_files:
        parts.append('<ul class="skipped-list">')
        for sf in result.skipped_files:
            parts.append(
                f"<li><strong>{_escape(sf.get('file', 'unknown'))}</strong> "
                f"&mdash; {_escape(sf.get('reason', 'N/A'))}</li>"
            )
        parts.append("</ul>")
    else:
        parts.append("<p>No skipped files.</p>")

    # Metadata
    parts.append('<div class="metadata">')
    parts.append("<ul>")
    parts.append(f"<li>Schema Version: {_escape(result.schema_version)}</li>")
    parts.append(f"<li>Repository: <code>{_escape(str(result.repo_path))}</code></li>")
    parts.append(
        f"<li>Commit Range: <code>{_escape(result.commit_range[0])}</code> .. "
        f"<code>{_escape(result.commit_range[1])}</code></li>"
    )
    if result.data_incomplete:
        parts.append('<li class="danger">Note: Analysis data is incomplete.</li>')
    parts.append("</ul>")
    parts.append("</div>")

    parts.append("</div>")  # .container
    parts.append("</body>")
    parts.append("</html>")

    return "\n".join(parts) + "\n"
