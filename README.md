# Vastu Compliance MCP Server

Production-oriented MCP server built with FastAPI for Autodesk workflows (Forma/Revit/APS), deterministic Vastu compliance checks, explainable recommendations, and structured JSON reporting.

## Highlights

- FastAPI + OpenAPI-ready service
- MCP endpoints for tool initialization and execution
- Autodesk Platform Services integration layer (OAuth + metadata fetch)
- Geometry extraction and room/wall/door/window classification pipeline
- Directional zoning engine (8-zone compass mapping)
- Deterministic YAML/JSON Vastu rules engine
- Revit 3D footprint projection pipeline for compliance checks
- AutoCAD layout (DWG) entity projection pipeline for compliance checks
- Vedic/Puran knowledge ingestion and recommendation references
- Explainable recommendation layer (AI explanations only, no rule mutation)
- Compliance scoring + severity + confidence outputs
- Geometry validation and visualization overlays/heatmap payloads
- Plugin architecture for pre/post evaluation hooks
- Structured logging + request IDs + Prometheus metrics
- Async-by-default service and test-friendly module boundaries
- Docker and docker-compose support

## Project Structure

```text
app/
  api/
    deps.py
    routes/
      autodesk.py
      compliance.py
      mcp.py
  core/
    config.py
    logging.py
  mcp/
    server.py
  models/
    schemas.py
  plugins/
    audit_plugin.py
    base.py
    manager.py
  services/
    ai/explainer.py
    autodesk/client.py
    context/context_manager.py
    direction/engine.py
    geometry/engine.py
    knowledge/vedic_knowledge.py
    rules/engine.py
    scoring/compliance.py
    validation/geometry_validator.py
    visualization/overlay.py
    compliance_pipeline.py
  main.py
config/
  vastu_rules.yaml
  vedic_knowledge.yaml
tests/
  test_vastu_pipeline.py
revit-plugin/
  VastuRevitPlugin/
    App.cs
    Commands/AnalyzeVastuCommand.cs
    Services/RevitModelExtractor.cs
    Services/VastuApiClient.cs
    deploy/VastuRevitPlugin.addin
autocad-plugin/
  VastuAutoCADPlugin/
    Commands/VastuCommands.cs
    Services/AutocadLayoutExtractor.cs
    Services/VastuApiClient.cs
    deploy/PackageContents.xml
Dockerfile
docker-compose.yml
requirements.txt
```

## Run Locally

1. Create `.env` from `.env.example`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Run:
   - `uvicorn app.main:app --reload`

Open docs:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- Metrics: [http://localhost:8000/metrics](http://localhost:8000/metrics)

## Run in Visual Studio Code

1. Open folder `Vastu Compilance MCP` in VS Code.
2. Create/select Python interpreter:
   - `Ctrl + Shift + P` -> `Python: Select Interpreter`
3. Create `.env` from `.env.example`.
4. Install dependencies in VS Code terminal:
   - `python -m pip install -r requirements.txt`
5. Run backend:
   - `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
6. Open Swagger:
   - [http://localhost:8000/docs](http://localhost:8000/docs)

Optional VS Code debug config (`.vscode/launch.json`):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI (uvicorn)",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
      "jinja": true
    }
  ]
}
```

## MCP Endpoints

- `POST /mcp/initialize`
- `GET /mcp/tools`
- `POST /mcp/tools/call`
- `POST /api/v1/compliance/analyze/revit3d`
- `POST /api/v1/compliance/analyze/autocad`
- `POST /api/v1/compliance/knowledge/ingest`

### Example MCP Tool Call

`POST /mcp/tools/call`

```json
{
  "tool": "analyze_vastu_compliance",
  "arguments": {
    "payload": {
      "source": "direct_json",
      "true_north_degrees": 0,
      "elements": [
        {
          "id": "room-1",
          "name": "Kitchen",
          "element_type": "room",
          "polygon": [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 10},
            {"x": 0, "y": 10}
          ],
          "metadata": {"room_type": "kitchen"}
        }
      ]
    },
    "context": {
      "client": "autodesk-forma",
      "project_id": "proj-01"
    }
  }
}
```

### Example Revit 3D Compliance Request

`POST /api/v1/compliance/analyze/revit3d`

```json
{
  "payload": {
    "source": "revit_3d",
    "true_north_degrees": 12,
    "elements": [
      {
        "id": "room-3d-1",
        "name": "Kitchen",
        "element_type": "room",
        "bounding_box": {
          "min": {"x": 0, "y": 0, "z": 0},
          "max": {"x": 12, "y": 8, "z": 3}
        },
        "metadata": {"room_type": "kitchen"}
      }
    ]
  },
  "context": {"client": "revit-plugin"}
}
```

### Example AutoCAD Layout Compliance Request

`POST /api/v1/compliance/analyze/autocad`

```json
{
  "payload": {
    "source": "autocad_layout_2d",
    "true_north_degrees": 0,
    "layout_name": "Ground Floor",
    "entities": [
      {
        "id": "room-1",
        "name": "Kitchen",
        "entity_type": "room",
        "points": [
          {"x": 0, "y": 0},
          {"x": 8, "y": 0},
          {"x": 8, "y": 6},
          {"x": 0, "y": 6}
        ],
        "metadata": {"room_type": "kitchen", "layer": "ROOM_KITCHEN"}
      }
    ]
  },
  "context": {"client": "autocad-plugin"}
}
```

### Example Vedic Knowledge Ingestion

`POST /api/v1/compliance/knowledge/ingest`

```json
{
  "entries": [
    {
      "source": "Skanda Purana",
      "principle": "Kitchen placement",
      "room_types": ["kitchen"],
      "preferred_zones": ["south_east"],
      "avoid_zones": ["north_east"],
      "guidance": "Cooking spaces are traditionally aligned with south-east."
    }
  ]
}
```

## Docker

- Build and run: `docker compose up --build`

## Revit Plugin

A Revit add-in scaffold is available in `revit-plugin/` to call this server directly from Revit.
See `revit-plugin/README.md` for build and install steps.

### Revit add-in quick steps

1. Open `revit-plugin/VastuRevitPlugin/VastuRevitPlugin.csproj` in Visual Studio.
2. Confirm `REVIT_API_DIR` path in `.csproj`.
3. Build `Release`.
4. Copy `VastuRevitPlugin.dll` to a permanent path.
5. Copy `revit-plugin/VastuRevitPlugin/deploy/VastuRevitPlugin.addin` to:
   - `%AppData%\Autodesk\Revit\Addins\2025\`
6. Edit `.addin` `<Assembly>` path to built DLL.
7. Start Revit and click:
   - `Vastu Compliance` -> `Analyze Vastu`

## AutoCAD Plugin

An AutoCAD .NET plugin scaffold is available in `autocad-plugin/` with `VASTUANALYZE` command support.
See `autocad-plugin/README.md` for build and install steps.

### AutoCAD add-in quick steps

1. Open `autocad-plugin/VastuAutoCADPlugin/VastuAutoCADPlugin.csproj` in Visual Studio.
2. Confirm `AUTOCAD_API_DIR` path in `.csproj`.
3. Build `Release`.
4. In AutoCAD run command:
   - `NETLOAD`
5. Select `VastuAutoCADPlugin.dll`.
6. Run command:
   - `VASTUANALYZE`

### Autodesk coding standard alignment

Current plugin/backend code follows these practical Autodesk extension conventions:

- .NET add-ins use explicit command entry points (`IExternalCommand` / `CommandMethod`).
- API interaction is isolated in dedicated client service classes.
- Model extraction and transport DTOs are separated for testability.
- Read-only operations are used for model extraction in Revit and AutoCAD.
- Failures are surfaced to host UI (`TaskDialog` / command line) with non-crashing behavior.

## Security Notes

- APS credentials are loaded from environment variables only.
- Rule evaluation is deterministic and side-effect free.
- AI layer only generates explanations/recommendations for deterministic outcomes.
