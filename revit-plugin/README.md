# Revit Plugin — Vastu Compliance (Advanced Output)

## What you get after **Analyze Vastu**

| Output | Where |
|--------|--------|
| **Heatmap** | Rooms color-coded in the active plan (green / orange / red) |
| **HTML report** | `Documents\VastuReports\VastuReport_*.html` — open in browser |
| **JSON report** | Same folder — full data for automation |
| **Structured dialog** | Headline, score, priority fixes, links to open report |
| **Ghost Preview** | Cyan proposed layout + gold arrows + compass + labels |

## Ribbon — Vastu Compliance → Analysis

| Button | Purpose |
|--------|---------|
| **Analyze Vastu** | Full analysis + heatmap + auto-export HTML/JSON |
| **Export Report** | Re-export last report to Documents/VastuReports |
| **Ghost Preview** | Advanced ghost: outlines, shift arrows, zone compass, room labels |
| **Clear Ghost** | Remove preview graphics |
| **Apply Remediation** | Apply real fixes after you approve ghost layout |
| **Safe Fixes Only** | Metadata/highlights only — no wall moves |

## Recommended workflow

1. Floor plan view + placed rooms  
2. **Analyze Vastu** → review dialog → **Open HTML report**  
3. **Ghost Preview** → verify cyan proposed layout vs gold arrows  
4. **Apply Remediation** or **Safe Fixes Only**  
5. **Analyze Vastu** again to confirm improved score  

## Build

```powershell
dotnet build "Vastu Compilance MCP\revit-plugin\VastuRevitPlugin\VastuRevitPlugin.csproj" -c Debug
```

Close Revit before build if deploy copy fails (DLL locked).

## MCP server

```powershell
cd "Vastu Compilance MCP"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`$env:VASTU_MCP_URL = "http://127.0.0.1:8000"`
