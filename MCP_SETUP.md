# Vastu Compliance MCP — Setup Guide

This project is **already an MCP server**. You can connect it to Claude Desktop, Cursor, or any MCP client in two ways.

> **Project path on this machine:**
> `C:\Users\Dhiraj Dabhade\Downloads\Vastu\Vastu Compilance MCP`

---

## Option A: stdio MCP (recommended for Claude Desktop / Cursor)

The AI client launches the server as a subprocess and talks over stdin/stdout.

### 1. Install dependencies

```powershell
cd "C:\Users\Dhiraj Dabhade\Downloads\Vastu\Vastu Compilance MCP"
python -m pip install -r requirements.txt
```

Set environment variables — copy `.env.example` to `.env`:

```powershell
Copy-Item ".env.example" ".env"
```

Then open `.env` and fill in any values you need:

| Variable | Purpose | Required? |
|----------|---------|-----------|
| `OPENAI_API_KEY` | VLM floor plan extraction + AI explanations | Optional (falls back to templates) |
| `OPENAI_MODEL` | Default `gpt-4o` | Optional |
| `RULES_PATH` | Default `config/vastu_rules.yaml` | Optional |

### 2. Register in Claude Desktop

The config file is at:

```
C:\Users\Dhiraj Dabhade\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json
```

The `mcpServers` section has already been updated with this entry:

```json
"vastu-compliance": {
  "command": "C:\\Users\\Dhiraj Dabhade\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe",
  "args": ["-m", "app.mcp.stdio_server"],
  "cwd": "C:\\Users\\Dhiraj Dabhade\\Downloads\\Vastu\\Vastu Compilance MCP",
  "env": {
    "PYTHONPATH": "C:\\Users\\Dhiraj Dabhade\\Downloads\\Vastu\\Vastu Compilance MCP",
    "RULES_PATH": "config/vastu_rules.yaml",
    "OPENAI_MODEL": "gpt-4o"
  }
}
```

> **Important:** Use the full path to `python.exe` (not just `python`) and always set `PYTHONPATH` to the project root. Without `PYTHONPATH`, Claude Desktop cannot find the `app` package even when `cwd` is set.

If you need to add `OPENAI_API_KEY`, edit the config and add it inside `"env"`:

```json
"OPENAI_API_KEY": "sk-your-key-here"
```

### 3. Register in Cursor (alternative)

Edit `%USERPROFILE%\.cursor\mcp.json` (create it if it doesn't exist):

```json
{
  "mcpServers": {
    "vastu-compliance": {
      "command": "python",
      "args": ["-m", "app.mcp.stdio_server"],
      "cwd": "C:\\Users\\Dhiraj Dabhade\\Downloads\\Vastu\\Vastu Compilance MCP",
      "env": {
        "RULES_PATH": "config/vastu_rules.yaml",
        "OPENAI_MODEL": "gpt-4o"
      }
    }
  }
}
```

### 4. Verify the server starts cleanly

Run this before restarting Claude Desktop — it should start silently with no errors:

```powershell
cd "C:\Users\Dhiraj Dabhade\Downloads\Vastu\Vastu Compilance MCP"
python -m app.mcp.stdio_server
```

Press `Ctrl+C` to stop. If you see an import error, run `pip install -r requirements.txt` again.

### 5. Restart Claude Desktop

After saving the config, **fully quit and restart Claude Desktop** so it picks up the new MCP server.

### 6. Test with this prompt

Paste this into Claude Desktop after restart:

```
Use the vastu-compliance MCP tool analyze_vastu_compliance with this layout.
true_north_degrees: 0

Rooms:
- Kitchen at polygon (0,0)→(10,0)→(10,8)→(0,8)
- Master Bedroom at (10,0)→(22,0)→(22,12)→(10,12)
- Toilet at (0,8)→(8,8)→(8,16)→(0,16)
- Living Room at (8,8)→(22,8)→(22,20)→(8,20)
- Entrance at (9,16)→(13,16)→(13,20)→(9,20)

Return compliance score, all violations with severity, and top 3 fixes.
```

---

## Option B: HTTP MCP (Revit / AutoCAD plugins)

Plugins call the FastAPI server over HTTP (not stdio).

```powershell
cd "C:\Users\Dhiraj Dabhade\Downloads\Vastu\Vastu Compilance MCP"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

| Endpoint | Purpose |
|----------|---------|
| `GET /mcp/tools` | List tools |
| `POST /mcp/tools/call` | Call a tool |
| `POST /api/v1/intelligent/analyze` | Full intelligent REST pipeline |
| `POST /api/v1/compliance/analyze` | Standard compliance |

Plugin env: `VASTU_MCP_URL=http://127.0.0.1:8000`

---

## Available MCP tools

### Core compliance

| Tool | Description |
|------|-------------|
| `analyze_floorplan` | Analyze structured 2D floor plan JSON |
| `analyze_revit_3d_vastu_compliance` | Revit 3D footprint analysis |
| `analyze_autocad_layout_vastu_compliance` | AutoCAD 2D layout |
| `vastu_score` | Score + grade from report |
| `detect_violations` | Failed rules only |
| `suggest_improvements` | Remediation plan actions |
| `list_rules` | YAML Vastu rules |
| `directional_zones` | 8-zone compass map |

### Intelligent pipeline (your full vision)

| Tool | Description |
|------|-------------|
| **`intelligent_layout_analyze`** | Extract → Vastu → report → constrained correction → SVG images |
| `extract_layout_geometry` | VLM/CAD extraction only |
| `generate_ghost_overlay` | Ghost + corrected layout JSON |
| `apply_layout_suggestions` | Same 2D layout with suggestions applied |

### Geometry helpers

| Tool | Description |
|------|-------------|
| `evaluate_room` | Single room + rules |
| `resolve_zone` | Bearing → Vastu zone |
| `check_brahmasthan` | Center zone overlap |

---

## Example: call `intelligent_layout_analyze` in Cursor

Ask Cursor (with MCP enabled):

> Use the vastu-compliance MCP tool `intelligent_layout_analyze` with this payload and keep the master bedroom fixed.

Tool arguments:

```json
{
  "payload": {
    "source": "direct_json",
    "true_north_degrees": 0,
    "elements": [
      {
        "id": "r-kitchen",
        "name": "Kitchen",
        "element_type": "room",
        "polygon": [
          {"x": 0, "y": 0},
          {"x": 10, "y": 0},
          {"x": 10, "y": 8},
          {"x": 0, "y": 8}
        ],
        "metadata": {"room_type": "kitchen"}
      },
      {
        "id": "r-master",
        "name": "Master",
        "element_type": "room",
        "polygon": [
          {"x": 12, "y": 0},
          {"x": 28, "y": 0},
          {"x": 28, "y": 12},
          {"x": 12, "y": 12}
        ],
        "metadata": {"room_type": "master_bedroom"}
      }
    ]
  },
  "user_constraints": [
    {
      "constraint_id": "keep-master",
      "kind": "fixed_room",
      "room_id": "r-master",
      "reason": "User wants master bedroom unchanged"
    }
  ],
  "generate_layout_images": true
}
```

Response includes:

- `extraction` — parsed geometry  
- `report` — Vastu compliance report  
- `corrected_layout` — same plan with fixes  
- `constraint_validation` — user rules check  
- `layout_images` — SVG original / corrected / comparison  

### VLM from image (requires OPENAI_API_KEY)

```json
{
  "image_base64": "<base64-encoded PNG of floor plan>",
  "image_media_type": "image/png",
  "user_constraints": [],
  "generate_layout_images": true
}
```

---

## Example: HTTP tool call (AutoCAD / scripts)

```powershell
curl -X POST http://127.0.0.1:8000/mcp/tools/call `
  -H "Content-Type: application/json" `
  -d '{
    "tool": "intelligent_layout_analyze",
    "arguments": {
      "payload": { "elements": [] },
      "generate_layout_images": true
    }
  }'
```

---

## Architecture

```
Cursor / Claude Desktop
        │  stdio (JSON-RPC)
        ▼
app/mcp/stdio_server.py
        │
        ▼
app/mcp/server.py  ──►  CompliancePipeline
        │                 IntelligentLayoutPipeline
        │                 VlmLayoutExtractor
        ▼
Structured JSON tools response
```

Revit / AutoCAD plugins use **HTTP** to the same `MCPServer.call_tool()` logic.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `No module named 'app'` / Server disconnected | Add `PYTHONPATH` to the MCP config `env` block pointing to the project root, and use the full `python.exe` path in `command` |
| No tools in Claude Desktop | Restart Claude Desktop fully; verify `python -m app.mcp.stdio_server` starts without errors |
| No tools in Cursor | Check `cwd` path, restart Cursor, verify `python -m app.mcp.stdio_server` runs |
| `ModuleNotFoundError` on startup | Run `pip install -r requirements.txt` from the project folder |
| VLM extraction fails | Set `OPENAI_API_KEY` in `.env` or in the MCP config `env` block, or send `payload` instead of `image_base64` |
| Revit plugin errors | Run uvicorn on port 8000, set `VASTU_MCP_URL=http://127.0.0.1:8000` |
| Large SVG in response | Set `generate_layout_images: false` and use REST `/api/v1/correction/apply-suggestions` |
| Config file location (Claude Desktop) | `C:\Users\Dhiraj Dabhade\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json` |

See also: [INTELLIGENT_LAYOUT_PIPELINE.md](./INTELLIGENT_LAYOUT_PIPELINE.md), [INTEGRATION.md](./INTEGRATION.md)
