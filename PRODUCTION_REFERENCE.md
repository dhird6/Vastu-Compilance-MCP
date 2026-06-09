# Vastu Compliance MCP — Production Reference

Complete reference for the production-ready Vastu Compliance MCP platform: architecture, MCP tools, report download, Claude chat workflow, and plugin commands.

---

## 1. System Overview

```
┌─────────────────┐     stdio/HTTP      ┌──────────────────────────────┐
│ Claude Desktop  │ ──────────────────► │  Vastu Compliance MCP Server │
│ Cursor / Chat   │                     │  (FastAPI + MCP SDK)         │
└─────────────────┘                     └──────────────┬───────────────┘
                                                       │
         ┌─────────────────────────────────────────────┼─────────────────────────┐
         │                                             │                         │
         ▼                                             ▼                         ▼
┌─────────────────┐                        ┌──────────────────┐      ┌──────────────────┐
│ AutoCAD Plugin  │                        │ Compliance       │      │ Report Export    │
│ (10 commands)   │                        │ Pipeline         │      │ HTML + ZIP       │
└─────────────────┘                        └──────────────────┘      └──────────────────┘
```

| Layer | Technology | Purpose |
|-------|------------|---------|
| MCP Transport | `app/mcp/stdio_server.py` | Claude Desktop / Cursor integration |
| HTTP API | `app/main.py` | AutoCAD/Revit plugins, scripts |
| Rules Engine | `config/vastu_rules.yaml` | Deterministic Vastu pass/fail |
| AI Layer | OpenAI GPT-4o | Explanations + VLM floor plan extraction |
| Reports | Jinja2 HTML + SVG visuals | Branded downloadable reports |

---

## 2. Production Features (What We Built)

### 2.1 Branded HTML Report

Every compliance analysis generates a professional HTML report with:

- **Company logo** (configurable SVG/PNG)
- **Executive summary** — score, grade, remediation counts
- **2D layout comparison** — original, corrected, before/after overlay
- **3D isometric comparison** — extruded room volumes for spatial comparison
- **Priority fixes table** — room, rule, zone transition, recommendation
- **Room dashboard** — status badges per room
- **Vastu zone legend** — Sanskrit names, elements, ideal uses
- **Print-ready CSS** — clean layout for PDF printing from browser

**Configuration (environment variables):**

| Variable | Default | Purpose |
|----------|---------|---------|
| `REPORT_COMPANY_NAME` | Vastu Compliance | Header company name |
| `REPORT_COMPANY_TAGLINE` | Professional Vastu Analysis Platform | Subtitle |
| `REPORT_COMPANY_WEBSITE` | https://vastu-compliance.local | Footer link |
| `REPORT_LOGO_PATH` | `config/assets/logo.svg` | Path to your company logo |

Replace `config/assets/logo.svg` with your own logo file.

### 2.2 Report Download

| Method | Endpoint / Tool | Output |
|--------|-----------------|--------|
| REST JSON | `POST /api/v1/compliance/report/download` | HTML + zip_base64 + assets |
| REST ZIP file | `POST /api/v1/compliance/report/download/zip` | ZIP attachment |
| MCP tool | `download_vastu_report` | Same bundle for Claude chat |
| AutoCAD | `VASTUANALYZE` / `VASTUEXPORTREPORT` | Saves to `Documents\VastuReports\` |
| Revit | Analyze Vastu ribbon | Saves to `Documents\VastuReports\` |

**ZIP bundle contents:**
```
VastuReport_Project_20250607.html
VastuReport_Project_20250607.json
assets/layout_original.svg
assets/layout_corrected.svg
assets/layout_comparison.svg
assets/isometric_original.svg
assets/isometric_corrected.svg
```

### 2.3 Claude Chat Workflow (Prompt-Only)

1. Connect MCP server to Claude Desktop (see Section 4)
2. Upload 2D floor plan image in chat
3. Prompt: *"Analyze this floor plan for Vastu compliance. Show score and corrected layout."*
4. Claude calls `intelligent_layout_analyze` or `analyze_floorplan`
5. Follow-up: *"Fix kitchen only, keep master bedroom fixed."*
6. Claude re-runs with `user_constraints`
7. Prompt: *"Download the Vastu report with company branding."*
8. Claude calls `download_vastu_report`

### 2.4 AutoCAD Plugin (Refactored — Autodesk Standards)

**Structure:**

```
VastuAutoCADPlugin/
├── PluginEntry.cs                    # IExtensionApplication
├── Configuration/VastuPluginSettings.cs
├── Commands/
│   ├── Base/DocumentCommandBase.cs   # Shared document helpers
│   ├── AnalyzeVastuCommand.cs
│   ├── ExportReportCommand.cs        # NEW
│   ├── ShowResultLayoutCommand.cs
│   ├── ClearResultLayoutCommand.cs
│   ├── ConfigureConstraintsCommand.cs
│   ├── GenerateLayoutCommand.cs
│   ├── ShowGeneratedLayoutCommand.cs
│   ├── ClearGeneratedLayoutCommand.cs
│   └── ExportGeneratedLayoutCommand.cs
├── Models/VastuDtos.cs
└── Services/
    ├── Abstractions/IVastuApiClient.cs
    ├── VastuApiClient.cs             # Generic Post<T>
    ├── ComplianceReportExporter.cs
    ├── ComplianceReportPresenter.cs
    └── ... (extractors, renderers)
```

**Design principles applied:**
- One command per class (Autodesk convention)
- Dependency injection via constructor (testable)
- `IVastuApiClient` abstraction for reuse
- Centralized settings in `VastuPluginSettings`
- Shared base class for document null-checks and error messages
- Full report DTO including `html_report`

| Command | Description |
|---------|-------------|
| `VASTUANALYZE` | Analyze layout + auto-export HTML report |
| `VASTUEXPORTREPORT` | Re-export or open last HTML report |
| `VASTURESULT` | Draw corrected 2D overlay |
| `VASTUCLEARRESULT` | Remove corrected overlay |
| `VASTUCONSTRAINTS` | Configure user constraints |
| `VASTUGENERATE` | Generate new Vastu layout |
| `VASTUSHOWGENERATED` | Draw generated layout |
| `VASTUCLEARGENERATED` | Remove generated layout |
| `VASTUEXPORTGENERATED` | Export generated layout DXF |

---

## 3. MCP Tools Reference

### Core Compliance

| Tool | Input | Output |
|------|-------|--------|
| `analyze_floorplan` | `payload` (FloorPlan JSON) | Full `ComplianceReport` + HTML |
| `analyze_autocad_layout_vastu_compliance` | AutoCAD entities | Full report |
| `analyze_revit_3d_vastu_compliance` | Revit 3D bounding boxes | Full report |
| `intelligent_layout_analyze` | Image or payload + constraints | Report + SVG images |
| `download_vastu_report` | `report` object | HTML + ZIP + assets |

### Utilities

| Tool | Purpose |
|------|---------|
| `vastu_score` | Score and grade from report |
| `detect_violations` | Failed rules only |
| `suggest_improvements` | Remediation plan |
| `list_rules` | YAML Vastu rules |
| `directional_zones` | 8-zone compass map |
| `compliance_chat` | Q&A on compliance |

---

## 4. Setup — Connect to Claude

```powershell
cd "C:\Plugin\Vastu Compilance MCP"
python -m pip install -r requirements.txt
```

**Claude Desktop MCP config** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vastu-compliance": {
      "command": "python",
      "args": ["-m", "app.mcp.stdio_server"],
      "cwd": "C:\\Plugin\\Vastu Compilance MCP",
      "env": {
        "OPENAI_API_KEY": "your-key",
        "OPENAI_MODEL": "gpt-4o",
        "REPORT_COMPANY_NAME": "Your Company Name",
        "REPORT_LOGO_PATH": "config/assets/logo.svg"
      }
    }
  }
}
```

Restart Claude fully after saving.

---

## 5. API Quick Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/compliance/analyze` | 2D JSON analyze |
| POST | `/api/v1/compliance/analyze/autocad` | AutoCAD layout |
| POST | `/api/v1/compliance/analyze/revit3d` | Revit 3D |
| POST | `/api/v1/compliance/report/download` | Report bundle JSON |
| POST | `/api/v1/compliance/report/download/zip` | Report ZIP file |
| POST | `/api/v1/intelligent/analyze` | Full intelligent pipeline |
| POST | `/api/v1/layout/generate-from-report` | New layout generation |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

---

## 6. Report Download Examples

### REST — ZIP download

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/compliance/report/download/zip `
  -H "Content-Type: application/json" `
  -d "@report.json" `
  --output VastuReport.zip
```

### MCP — Claude chat

> Analyze my floor plan, then download the full Vastu report with logo and 3D comparison.

Claude calls:
1. `intelligent_layout_analyze` → gets report
2. `download_vastu_report` with `{ "report": {...} }` → returns HTML + zip_base64

### AutoCAD

```
Command: VASTUANALYZE
→ Report auto-saved to Documents\VastuReports\VastuReport_*.html

Command: VASTUEXPORTREPORT
→ Re-export and open in browser
```

---

## 7. User Constraints (Chat Validator)

When user says *"keep master bedroom fixed"*, Claude passes:

```json
"user_constraints": [
  {
    "constraint_id": "keep-master",
    "kind": "fixed_room",
    "room_id": "r-master",
    "reason": "User request"
  }
]
```

| Kind | Behavior |
|------|----------|
| `fixed_room` | Room polygon must not move |
| `fixed_zone` | Room must stay in specified zone |
| `max_move` | Cap translation distance (feet) |
| `preserve_room_type` | Lock all rooms of a type |

---

## 8. Key Source Files

| File | Purpose |
|------|---------|
| `app/services/compliance_pipeline.py` | Core analysis orchestration |
| `app/services/report/html_generator.py` | Jinja2 HTML report |
| `app/services/report/templates/vastu_report.html` | Report template |
| `app/services/report/branding.py` | Logo + company config |
| `app/services/report/report_export_service.py` | ZIP bundle builder |
| `app/services/visualization/layout_image_renderer.py` | 2D SVG comparison |
| `app/services/visualization/isometric_renderer.py` | 3D isometric SVG |
| `app/mcp/stdio_server.py` | Claude MCP transport |
| `app/mcp/server.py` | MCP tool registry |
| `config/assets/logo.svg` | Default company logo |

---

## 9. Production Checklist

- [x] MCP server (stdio + HTTP)
- [x] Branded HTML reports with logo
- [x] 2D layout comparison in report
- [x] 3D isometric comparison in report
- [x] Report ZIP download (API + MCP)
- [x] AutoCAD plugin refactored (Autodesk standards)
- [x] AutoCAD report export command
- [x] Claude chat workflow (prompt-based)
- [x] User constraints validator
- [ ] Replace default logo with your company logo
- [ ] Set `APP_ENV=production` and `APP_DEBUG=false` for deployment
- [ ] Configure HTTPS reverse proxy for HTTP API

---

## 10. Related Documentation

- [MCP_SETUP.md](./MCP_SETUP.md) — MCP connection guide
- [INTELLIGENT_LAYOUT_PIPELINE.md](./INTELLIGENT_LAYOUT_PIPELINE.md) — Full 2D pipeline
- [ARCHITECTURE.md](./ARCHITECTURE.md) — System architecture
- [LAYOUT_CORRECTION.md](./LAYOUT_CORRECTION.md) — Ghost overlay and correction
- [INTEGRATION.md](./INTEGRATION.md) — Plugin integration notes
