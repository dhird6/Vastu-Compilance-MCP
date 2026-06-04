# AutoCAD Plugin - Vastu Compliance

This plugin allows you to analyze an AutoCAD layout and get Vastu suggestions directly from the MCP server.

## Command

- `VASTUANALYZE`

Run this command in AutoCAD after loading the plugin. It sends mapped layout entities to:
- `POST /api/v1/compliance/analyze/autocad`

## Entity mapping rules

The plugin classifies geometry by layer names:

- layers containing `room` -> room
- layers containing `wall` -> wall
- layers containing `door` -> door
- layers containing `window` -> window

For room typing, layer hints are used:
- `kitchen` -> kitchen
- `master` or `bed` -> master_bedroom
- `pooja` -> pooja
- `toilet` -> toilet
- `living` -> living_room

## Build

1. Open `autocad-plugin/VastuAutoCADPlugin/VastuAutoCADPlugin.csproj` in Visual Studio.
2. Ensure `AUTOCAD_API_DIR` matches your installed AutoCAD path.
3. Build in `Release` mode.

## Load in AutoCAD (quick)

1. Start AutoCAD.
2. Run command: `NETLOAD`
3. Select built `VastuAutoCADPlugin.dll`.
4. Run command: `VASTUANALYZE`.

## Install as AutoLoader package (optional)

1. Create a `.bundle` folder, e.g. `VastuAutoCADPlugin.bundle`.
2. Copy `deploy/PackageContents.xml` to bundle root.
3. Place DLL at `./Contents/Windows/VastuAutoCADPlugin.dll`.
4. Copy bundle under:
   - `%AppData%\Autodesk\ApplicationPlugins\`

## MCP server URL

Default:
- `http://127.0.0.1:8000`

Override with env var:
- `VASTU_MCP_URL=http://your-server:8000`

## Note

Recommendations and scriptural references are produced by the backend rule + knowledge engines, so update your Vastu rules and Vedic knowledge there for project-specific behavior.
