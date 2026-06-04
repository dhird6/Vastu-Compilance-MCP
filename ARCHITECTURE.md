# AI-Powered Vastu Compliance MCP Server — Architecture

## Role

Expert AEC full-stack system: Autodesk Revit/.NET plugins ↔ MCP Server ↔ OpenAI GPT-4o ↔ deterministic spatial geometry engine.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | Python 3.11+, FastAPI |
| MCP | Official `mcp` SDK (stdio) + HTTP shim for Revit plugins |
| Geometry | Shapely, NumPy (centroid-based zones, adjacency, Brahmasthan) |
| BIM/CAD | ezdxf (DXF), IfcOpenShell (IFC) — optional parsers |
| Database | PostgreSQL + pgvector (report history, Vedic RAG) |
| AI | OpenAI GPT-4o structured JSON outputs |

## Design Principles

### 1. Geometry First

All rooms are explicit polygons with:

- **Centroid-based zone** — bearing from plot center + `true_north_degrees`
- **Primary axis** — longest edge orientation (stored in metadata)
- **Brahmasthan** — inner 15% of plot radius = center zone; heavy rooms flagged
- **Adjacency** — Shapely `touches` / `intersects` for neighbor graph

### 2. Rule–AI Hybridization

```
Geometry → Deterministic Rules (YAML) → pass/fail FIXED
                    ↓
         Template explanations + Vedic refs
                    ↓
         OpenAI enrichment (optional, never changes pass/fail)
```

### 3. Stateless MCP Tools

Thin tools accept JSON with Revit **Element IDs**, **polygons**, **bounding boxes**, **room_type**, **true_north_degrees**:

- `evaluate_room` — single-room zone + rules
- `resolve_zone` — bearing → zone + Sanskrit name
- `check_brahmasthan` — center overlap check

Full-payload tools (`analyze_revit_3d_vastu_compliance`, etc.) remain for batch analysis.

## Vastu Domain

| Bearing | Zone | Sanskrit | Element | Typical use |
|---------|------|----------|---------|-------------|
| 0° / 360° | north | Kubera | Water | Living, entrance |
| 22.5–67.5° | north_east | **Ishan** | Water/Prayer | Pooja, meditation |
| 67.5–112.5° | east | Indra | Air/Sun | Living, study |
| 112.5–157.5° | south_east | **Agneya** | Fire | Kitchen |
| 157.5–202.5° | south | Yama | Fire | Storage |
| 202.5–247.5° | south_west | **Nairutya** | Earth | Master bedroom |
| 247.5–292.5° | west | Varuna | Water | Children, dining |
| 292.5–337.5° | north_west | **Vayu** | Air | Guest, storage |
| Center | center | **Brahmasthan** | Space | Open — no heavy loads |

Implementation: `app/domain/vastu_zones.py`

## Project Layout

```
app/
├── domain/vastu_zones.py      # Canonical zone catalog
├── services/
│   ├── geometry/
│   │   ├── engine.py          # Plot center, room orientations
│   │   └── shapely_ops.py     # Shapely polygon ops
│   ├── rules/engine.py        # RuleRegistry + VastuRuleEngine
│   ├── ai/openai_client.py    # GPT-4o structured outputs
│   └── direction/engine.py    # Zone resolution facade
├── mcp/
│   ├── server.py              # HTTP MCP bridge
│   ├── stdio_server.py        # Official MCP stdio (Cursor)
│   └── tools.py               # Thin stateless tools
├── bim/                       # ezdxf, ifcopenshell parsers
└── db/                        # PostgreSQL + pgvector
```

## Running

```powershell
# API + HTTP MCP
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Official MCP stdio (Cursor / Claude Desktop)
python -m app.mcp.stdio_server

# With Postgres
docker compose up -d
```

## Environment

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Enable GPT-4o chat + recommendation enrichment |
| `OPENAI_MODEL` | Default `gpt-4o` |
| `DATABASE_URL` | `postgresql+asyncpg://...` for report + vector store |
| `VASTU_MCP_URL` | Revit plugin API base (default `http://127.0.0.1:8000`) |
