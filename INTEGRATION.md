# Vastu Compliance — End-to-End Workflow

## Your goal

Analyze a **2D layout** or **3D Revit home model** for Vastu compliance, receive MCP suggestions via `RemediationPlan`, and **apply fixes in Revit** — including approved geometry alignment (wall moves).

---

## Setup

### 1. Start MCP server

From the **Plugin** repository root:

```powershell
cd "Vastu Compilance MCP"
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Build Vastu Revit plugin

```powershell
cd "c:\Users\varkada\OneDrive - Autodesk\Desktop\Plugin"
dotnet build "Vastu Compilance MCP\revit-plugin\VastuRevitPlugin\VastuRevitPlugin.csproj" -c Debug
```

Post-build copies `VastuRevitPlugin.dll` and `VastuRevitPlugin.addin` to:

`%APPDATA%\Autodesk\Revit\Addins\2026\`

### 3. Environment (optional)

Set before starting Revit if not using the default URL:

```powershell
$env:VASTU_MCP_URL = "http://127.0.0.1:8000"
```

---

## Ribbon tab: **Vastu Compliance** → panel **Analysis**

| # | Ribbon button | Command | What it does |
|---|---------------|---------|--------------|
| 1 | **Analyze Vastu** | `AnalyzeVastuCommand` | Extracts model → MCP analyze → score + stores `RemediationPlan` |
| 2 | **Result Layout** | `ShowResultLayoutCommand` | Draws **solid green** corrected 2D plan from `corrected_layout` (same rooms, suggestions applied) |
| 3 | **Ghost Preview** | `PreviewVastuCommand` | Draws **ghost design** (cyan shift arrows + compass) + action summary |
| 4 | **Clear Preview** | `ClearGhostDesignCommand` | Removes ghost + result layout graphics |
| 5 | **Apply Remediation** | `ApplyRemediationCommand` | **Full bridge:** safe fixes + guides, then prompts to move boundary walls |
| 6 | **Safe Fixes Only** | `ApplyVastuCommand` | Safe fixes only (highlights, comments, tags, guides) — **no** wall moves |

---

## In Revit 2026 (step by step)

1. **Restart Revit** after rebuilding the plugin (ribbon loads at startup).
2. Open your home model with **placed rooms** (names like Kitchen, Bedroom, Entrance, etc.).
3. Switch to a **floor plan view** (recommended for zone guide lines).

| Step | Button | Action |
|------|--------|--------|
| **1** | **Analyze Vastu** | Dialog shows compliance score, top recommendations, and remediation summary. |
| **2** | **Result Layout** | Solid green room outlines = corrected 2D layout from MCP (`corrected_payload`). |
| **3** | **Ghost Preview** | Cyan ghost + gold arrows = shift preview vs original; review remediation actions. |
| **4** | **Apply Remediation** | (a) Applies safe fixes and zone guides. (b) Prompts for approval. (c) Moves room boundary walls toward target Vastu zones (default 3 ft). |
| **5** | *(optional)* **Safe Fixes Only** | Visual/metadata fixes only — no wall moves. |
| **6** | *(optional)* **Clear Preview** | Remove ghost + result layout graphics before or after apply. |
| **7** | **Analyze Vastu** | Re-run to verify updated compliance after changes. |

**Undo:** Use **Ctrl+Z** if wall moves are not desired. Prefer testing on a **copy** of the project first.

---

## RemediationPlan action types (MCP → Revit)

| Action | Applied by | Revit effect |
|--------|------------|--------------|
| `highlight_room` | Safe Fixes / Apply Remediation | Orange override in active view |
| `set_parameter` | Safe Fixes / Apply Remediation | Comments field with zone + rule ID |
| `draw_zone_guide` | Safe Fixes / Apply Remediation | Blue detail/model line toward target zone |
| `annotate` | Safe Fixes / Apply Remediation | Adds `[Vastu]` to room name |
| `show_ghost_design` | Ghost Preview | Cyan shifted room outline (preview only) |
| `move_room_boundaries` | Apply Remediation only (after approval) | Moves bounding walls by `translation_feet` |

**Important:** Wall moves affect **shared walls** between adjacent rooms.

---

## MCP tools

- `analyze_floorplan` / `analyze_vastu_compliance`
- `analyze_revit_3d_vastu_compliance`
- `analyze_autocad_layout_vastu_compliance`
- `vastu_score`, `suggest_improvements`, `detect_violations`, `room_analysis`
- `compliance_chat`
- `list_rules`, `directional_zones`

Delta analyze (changed rooms only):

- `POST /api/v1/compliance/analyze/revit3d/delta`

---

## Next enhancements

- OpenAI-powered `compliance_chat` (currently template-based)
- Configurable move distance per rule / project settings
- Real-time delta re-analyze via Revit model change events
- PostgreSQL report history and audit log
