from __future__ import annotations

import html
from datetime import datetime

from app.models.schemas import ComplianceReport
from app.services.report.formatter import ReportFormatter


class HtmlReportGenerator:
    def __init__(self, formatter: ReportFormatter | None = None) -> None:
        self._formatter = formatter or ReportFormatter()

    def generate(self, report: ComplianceReport) -> str:
        structured = self._formatter.build(report)
        exec_sum = structured["executive_summary"]
        score = exec_sum["compliance_score"]
        score_pct = min(100, max(0, score))

        room_rows = "".join(self._room_row(row) for row in structured["room_dashboard"])
        fix_rows = "".join(self._fix_row(fix) for fix in structured["priority_fixes"])
        zone_rows = "".join(self._zone_row(zone) for zone in structured["zone_legend"])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Vastu Compliance Report — {html.escape(exec_sum["request_id"])}</title>
  <style>
    :root {{
      --bg: #0f1419; --card: #1a2332; --text: #e8eef4; --muted: #8ba3b8;
      --accent: #00d4aa; --warn: #ff8c00; --crit: #dc143c; --ok: #2e8b57;
    }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text);
      margin: 0; padding: 24px; line-height: 1.5; }}
    h1 {{ color: var(--accent); margin-bottom: 0.25rem; }}
    .subtitle {{ color: var(--muted); margin-bottom: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
    .card {{ background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid #2a3a4d; }}
    .score-ring {{ font-size: 2.5rem; font-weight: 700; color: var(--accent); }}
    .grade {{ font-size: 1.25rem; color: var(--muted); }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 0.9rem; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #2a3a4d; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }}
    .badge-critical {{ background: var(--crit); color: #fff; }}
    .badge-warning {{ background: var(--warn); color: #000; }}
    .badge-compliant {{ background: var(--ok); color: #fff; }}
    .progress {{ height: 8px; background: #2a3a4d; border-radius: 4px; overflow: hidden; margin-top: 8px; }}
    .progress-bar {{ height: 100%; background: linear-gradient(90deg, var(--crit), var(--warn), var(--accent)); width: {score_pct}%; }}
    footer {{ margin-top: 32px; color: var(--muted); font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>Vastu Compliance Report</h1>
  <p class="subtitle">{html.escape(exec_sum["headline"])}</p>

  <div class="grid">
    <div class="card">
      <div class="score-ring">{score:.1f}%</div>
      <div class="grade">Grade {html.escape(exec_sum["grade"])}</div>
      <div class="progress"><div class="progress-bar"></div></div>
    </div>
    <div class="card">
      <strong>Rooms analyzed</strong><br/>{exec_sum["total_rooms"]}<br/><br/>
      <strong>Rules passed / failed</strong><br/>{exec_sum["passed_rules"]} / {exec_sum["failed_rules"]}
    </div>
    <div class="card">
      <strong>Remediation</strong><br/>
      {exec_sum["auto_fixes"]} auto · {exec_sum["manual_fixes"]} manual<br/><br/>
      <span style="color:var(--muted)">{html.escape(structured["remediation_summary"])}</span>
    </div>
  </div>

  <div class="card" style="margin-top:24px">
    <h2>Priority fixes</h2>
    <table>
      <thead><tr><th>#</th><th>Room</th><th>Issue</th><th>Current → Target</th><th>Action</th></tr></thead>
      <tbody>{fix_rows or "<tr><td colspan='5'>No violations</td></tr>"}</tbody>
    </table>
  </div>

  <div class="card" style="margin-top:24px">
    <h2>Room dashboard</h2>
    <table>
      <thead><tr><th>Status</th><th>Room</th><th>Type</th><th>Zone (Sanskrit)</th><th>Target</th><th>Area</th></tr></thead>
      <tbody>{room_rows}</tbody>
    </table>
  </div>

  <div class="card" style="margin-top:24px">
    <h2>Vastu zone legend</h2>
    <table>
      <thead><tr><th>Zone</th><th>Sanskrit</th><th>Element</th><th>Ideal for</th></tr></thead>
      <tbody>{zone_rows}</tbody>
    </table>
  </div>

  <footer>
    Request {html.escape(exec_sum["request_id"])} · Generated {html.escape(exec_sum["generated_at"])}<br/>
    Use <strong>Ghost Preview</strong> in Revit for proposed layout, then <strong>Apply Remediation</strong>.
  </footer>
</body>
</html>"""

    def _room_row(self, row: dict) -> str:
        badge_class = f"badge-{row['status']}" if row["status"] in {"critical", "warning", "compliant"} else "badge-warning"
        target = row.get("target_zone") or "—"
        target_s = row.get("target_sanskrit") or ""
        target_label = f"{html.escape(target)} ({html.escape(target_s)})" if target_s else html.escape(target)
        return f"""<tr>
      <td><span class="badge {badge_class}">{html.escape(row["status"])}</span></td>
      <td>{html.escape(row["room_name"])}</td>
      <td>{html.escape(row["room_type"])}</td>
      <td>{html.escape(row["zone"])} <small>({html.escape(row["zone_sanskrit"])})</small></td>
      <td>{target_label}</td>
      <td>{row["area_sqft"]:.0f}</td>
    </tr>"""

    def _fix_row(self, fix: dict) -> str:
        sev = fix["severity"]
        badge = f"badge-{sev}" if sev in {"critical", "high"} else "badge-warning"
        current = html.escape(fix["current_zone"])
        target = html.escape(fix["target_zone"])
        sanskrit = html.escape(fix.get("target_sanskrit") or "")
        return f"""<tr>
      <td>{fix["priority"]}</td>
      <td>{html.escape(fix["room_name"])} <small>({html.escape(fix["room_type"])})</small></td>
      <td><span class="badge {badge}">{html.escape(fix["rule_id"])}</span></td>
      <td>{current} → {target} <small>{sanskrit}</small></td>
      <td>{html.escape(fix["recommendation"][:120])}</td>
    </tr>"""

    def _zone_row(self, zone: dict) -> str:
        uses = ", ".join(zone.get("recommended_uses", [])[:4])
        return f"""<tr>
      <td>{html.escape(str(zone["zone"]))}</td>
      <td>{html.escape(str(zone["sanskrit"]))}</td>
      <td>{html.escape(str(zone["element"]))}</td>
      <td>{html.escape(uses)}</td>
    </tr>"""

    def save_path_hint(self, request_id: str) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = request_id.replace(":", "-")[:32]
        return f"VastuReport_{safe_id}_{stamp}.html"
